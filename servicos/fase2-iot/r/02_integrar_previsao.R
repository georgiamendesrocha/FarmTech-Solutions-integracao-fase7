# r/02_integrar_previsao.R
# Integra dados de IoT (historico de irrigacao) com previsao do tempo.

temporal_helper <- file.path("r", "temporal_utils.R")
if (!file.exists(temporal_helper)) {
  script_file <- tryCatch(sys.frame(1)$ofile, error = function(e) NULL)
  if (is.null(script_file)) script_file <- sub("^--file=", "", grep("^--file=", commandArgs(), value = TRUE)[1])
  temporal_helper <- file.path(dirname(normalizePath(script_file)), "temporal_utils.R")
}
source(temporal_helper, local = TRUE, encoding = "UTF-8")

mode_value <- function(x) {
  x <- x[!is.na(x)]
  if (length(x) == 0) {
    return(NA)
  }
  ux <- unique(x)
  tab <- tabulate(match(x, ux))
  modes <- ux[tab == max(tab)]
  if (length(modes) == 1) {
    return(modes)
  }
  return(modes)
}

load_iot_data <- function() {
  paths <- c(
    file.path("dados", "historico_irrigacao.csv"),
    file.path("dados", "captura_serial.csv")
  )
  ok <- file.exists(paths)
  if (!any(ok)) {
    stop("Nenhum CSV de IoT encontrado em dados/. Gere historico com scripts/serial_grava_csv.py")
  }

  arquivo <- paths[which(ok)[1]]
  message("A usar IoT: ", arquivo)

  dados <- read.csv(arquivo, stringsAsFactors = FALSE)
  if ("ts_iso" %in% names(dados)) {
    dados$ts_iso <- parse_timestamps(dados$ts_iso)
  }

  dados$t_rel_ms <- as.numeric(dados$t_rel_ms)
  dados$N <- as.integer(dados$N)
  dados$P <- as.integer(dados$P)
  dados$K <- as.integer(dados$K)
  dados$bomba_fw <- as.integer(dados$bomba_fw)

  dados
}

load_weather_data <- function() {
  arquivo <- file.path("dados", "previsao_tempo", "previsao_tempo.csv")
  if (!file.exists(arquivo)) {
    stop("Arquivo de previsao do tempo nao encontrado em dados/previsao_tempo/previsao_tempo.csv. Execute scripts/weather_forecast.py primeiro.")
  }

  dados <- read.csv(arquivo, stringsAsFactors = FALSE)
  if ("ts_iso" %in% names(dados)) {
    dados$ts_iso <- parse_timestamps(dados$ts_iso, default_tz = "UTC")
  }

  dados$temp_c <- as.numeric(dados$temp_c)
  dados$umidade <- as.numeric(dados$umidade)
  dados$rain_mm <- as.numeric(dados$rain_mm)
  dados$wind_ms <- as.numeric(dados$wind_ms)
  dados$weathercode <- as.integer(dados$weathercode)

  dados
}

describe_numeric <- function(name, x) {
  x <- x[is.finite(x)]
  if (length(x) == 0) {
    cat("\n", name, ": todos os valores são NA.\n", sep = "")
    return()
  }
  cat("\n---", name, "---\n")
  cat(sprintf("%-15s: %.2f\n", "Média", mean(x)))
  cat(sprintf("%-15s: %.2f\n", "Mediana", median(x)))
  cat(sprintf("%-15s: %s\n", "Moda", paste(mode_value(x), collapse = ", ")))
  cat(sprintf("%-15s: %.2f\n", "Desvio padrão", sd(x)))
  cat(sprintf("%-15s: %.2f\n", "Variância", var(x)))
  cat(sprintf("%-15s: %.2f a %.2f\n", "Intervalo", range(x)[1], range(x)[2]))
  cat("Quartis / Percentis:\n")
  q <- quantile(x, probs = c(0, 0.25, 0.5, 0.75, 1), na.rm = TRUE)
  cat(sprintf("  %-5s: %.2f\n", "0%", q[1]))
  cat(sprintf("  %-5s: %.2f\n", "25%", q[2]))
  cat(sprintf("  %-5s: %.2f\n", "50%", q[3]))
  cat(sprintf("  %-5s: %.2f\n", "75%", q[4]))
  cat(sprintf("  %-5s: %.2f\n", "100%", q[5]))
  cat("Percentis 90/95/99:\n")
  p <- quantile(x, probs = c(0.9, 0.95, 0.99), na.rm = TRUE)
  cat(sprintf("  %-5s: %.2f\n", "90%", p[1]))
  cat(sprintf("  %-5s: %.2f\n", "95%", p[2]))
  cat(sprintf("  %-5s: %.2f\n", "99%", p[3]))
}
main <- function() {
  iot <- load_iot_data()
  weather <- load_weather_data()

  if (!"ts_iso" %in% names(iot) || !"ts_iso" %in% names(weather)) {
    stop("Ambos os datasets precisam ter a coluna ts_iso como timestamp UTC.")
  }

  valid_count <- sum(is.finite(as.numeric(weather$ts_iso)))
  selected <- ordered_forecast_indices(weather$ts_iso)
  message("Previsão: ", nrow(weather) - valid_count, " timestamps inválidos ignorados; ",
    valid_count - length(selected), " duplicatas removidas (primeira linha original preservada).")
  weather <- weather[selected, , drop = FALSE]
  outside <- as.numeric(iot$ts_iso) < min(as.numeric(weather$ts_iso)) | as.numeric(iot$ts_iso) > max(as.numeric(weather$ts_iso))
  cat("Método: interpolação linear das variáveis contínuas; código/metadados por vizinho mais próximo.\n")
  cat("Previsão ordenada por instante; empate do vizinho favorece o horário anterior.\n")
  cat("Sem tolerância máxima; fora da cobertura repete o valor extremo. Registros fora:", sum(outside, na.rm = TRUE), "\n")
  cat("Registros IoT com timestamp inválido (sem associação):", sum(!is.finite(as.numeric(iot$ts_iso))), "\n")

  message("Comparando ", nrow(iot), " registros de IoT com ", nrow(weather), " registros de previsao.")
  indices <- find_nearest_index(iot$ts_iso, weather$ts_iso)

  # Interpolação é uma escolha de associação, sem promessa de melhora estatística.
  forecast_temp_c <- interpolate_forecast(iot$ts_iso, weather$ts_iso, weather$temp_c)
  forecast_umidade <- interpolate_forecast(iot$ts_iso, weather$ts_iso, weather$umidade)
  forecast_rain_mm <- interpolate_forecast(iot$ts_iso, weather$ts_iso, weather$rain_mm)
  forecast_wind_ms <- interpolate_forecast(iot$ts_iso, weather$ts_iso, weather$wind_ms)
  forecast_weathercode <- weather$weathercode[indices]  # use nearest for categorical

  merged <- data.frame(
    iot,
    forecast_ts_iso = weather$ts_iso[indices],
    forecast_temp_c = forecast_temp_c,
    forecast_umidade = forecast_umidade,
    forecast_rain_mm = forecast_rain_mm,
    forecast_wind_ms = forecast_wind_ms,
    forecast_weathercode = forecast_weathercode,
    forecast_city = weather$city[indices],
    forecast_country = weather$country[indices],
    forecast_latitude = weather$latitude[indices],
    forecast_longitude = weather$longitude[indices],
    stringsAsFactors = FALSE
  )

  merged <- format_timestamp_columns(merged)
  cat("Horários exportados em", IOT_TIMEZONE, "com offset explícito; IoT sem fuso usa", capture_timezone(), "; previsão sem sufixo é UTC.\n")

  out_path <- file.path("dados", "analises", "integrada", "dados_integrados_iot_previsao.csv")
  dir.create(dirname(out_path), recursive = TRUE, showWarnings = FALSE)
  message("Salvando dataset integrado em: ", out_path)
  write.csv(merged, out_path, row.names = FALSE)

  cat("\n=== Resumo do dataset integrado ===\n")
  print(summary(merged))
  cat("\nPrimeiras linhas do dataset integrado:\n")
  print(head(merged))

  cat("\n=== Medidas descritivas adicionais ===\n")
for (col in c("umidade", "temp_c", "ph_corr", "forecast_temp_c", "forecast_umidade", "forecast_rain_mm")) {
    if (col %in% names(merged)) {
      describe_numeric(col, merged[[col]])
    }
  }

  invisible(merged)
}

main()
