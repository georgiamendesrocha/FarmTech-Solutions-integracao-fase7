# Contratos de tempo compartilhados pelo menu e pela integração independente.
IOT_TIMEZONE <- "America/Bahia"

capture_timezone <- function() {
  tz <- Sys.timezone()
  if (length(tz) != 1 || is.na(tz) || !nzchar(tz)) "UTC" else tz
}

parse_timestamps <- function(values, default_tz = capture_timezone()) {
  values <- as.character(values)
  valid <- !is.na(values) & grepl("^[0-9]{4}-[0-9]{2}-[0-9]{2}T([01][0-9]|2[0-3]):[0-5][0-9](:[0-5][0-9](\\.[0-9]+)?)?(Z|[+-]([01][0-9]|2[0-3]):?[0-5][0-9])?$", values)
  has_offset <- valid & grepl("(Z|[+-][0-9]{2}:?[0-9]{2})$", values)
  normalized <- sub("Z$", "+0000", values)
  normalized <- sub("([+-][0-9]{2}):([0-9]{2})$", "\\1\\2", normalized)
  parsed <- as.POSIXct(rep(NA_real_, length(values)), origin = "1970-01-01", tz = default_tz)
  for (offset in c(FALSE, TRUE)) {
    selected <- which(valid & has_offset == offset)
    if (length(selected) == 0) next
    tz <- if (offset) "UTC" else default_tz
    suffix <- if (offset) "%z" else ""
    has_seconds <- grepl("T[0-9]{2}:[0-9]{2}:", normalized[selected])
    for (seconds in c(FALSE, TRUE)) {
      pending <- selected[has_seconds == seconds]
      if (length(pending) == 0) next
      base_format <- if (seconds) "%Y-%m-%dT%H:%M:%OS" else "%Y-%m-%dT%H:%M"
      parsed[pending] <- as.POSIXct(normalized[pending], format = paste0(base_format, suffix), tz = tz)
    }
  }
  parsed
}

format_timestamps <- function(values, tz = IOT_TIMEZONE) {
  # Muda somente a apresentação, sem modificar os segundos desde a época UTC.
  formatted <- format(values, "%Y-%m-%dT%H:%M:%S%z", tz = tz)
  sub("([+-][0-9]{2})([0-9]{2})$", "\\1:\\2", formatted)
}

format_timestamp_columns <- function(dados, tz = IOT_TIMEZONE) {
  for (col in names(dados)) {
    if (inherits(dados[[col]], "POSIXt")) {
      dados[[col]] <- format_timestamps(dados[[col]], tz)
    }
  }
  dados
}

find_nearest_index <- function(times, ref_times) {
  reference <- as.numeric(ref_times)
  valid_reference <- which(is.finite(reference))
  if (length(valid_reference) == 0) {
    stop("A previsão não contém timestamps válidos para associação temporal.")
  }
  # Menor distância absoluta; em empate, mantém a primeira linha recebida.
  vapply(as.numeric(times), function(x) {
    if (!is.finite(x)) return(NA_integer_)
    valid_reference[which.min(abs(reference[valid_reference] - x))]
  }, integer(1))
}

ordered_forecast_indices <- function(times) {
  numeric_times <- as.numeric(times)
  selected <- which(is.finite(numeric_times))
  if (length(selected) == 0) {
    stop("A previsão não contém timestamps válidos para associação temporal.")
  }
  selected <- selected[order(numeric_times[selected], selected)]
  # Em timestamp duplicado prevalece a primeira linha do arquivo original.
  selected[!duplicated(numeric_times[selected])]
}

interpolate_forecast <- function(iot_times, weather_times, weather_values) {
  if (length(weather_times) != length(weather_values)) {
    stop("Previsão com quantidades incompatíveis de horários e valores.")
  }
  selected <- ordered_forecast_indices(weather_times)
  reference <- as.numeric(weather_times[selected])
  values <- as.numeric(weather_values[selected])
  values[!is.finite(values)] <- NA_real_
  vapply(as.numeric(iot_times), function(t) {
    if (!is.finite(t)) return(NA_real_)
    exact <- match(t, reference)
    if (!is.na(exact)) return(values[exact])
    if (t < reference[1]) return(values[1])
    if (t > reference[length(reference)]) return(values[length(values)])
    left <- findInterval(t, reference)
    # Não atravessa silenciosamente limites com valores ausentes/não finitos.
    if (anyNA(values[c(left, left + 1)])) return(NA_real_)
    fraction <- (t - reference[left]) / (reference[left + 1] - reference[left])
    values[left] + fraction * (values[left + 1] - values[left])
  }, numeric(1))
}
