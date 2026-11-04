# Testes locais com R base. Execute da raiz: Rscript tests/test_app_r.R
# Fixtures e saídas ficam em tests/.tmp_r_audit/, sem tocar em dados/.

run_tests <- function() {
# As fixtures sem offset representam captura em Bahia, inclusive nos subprocessos.
# Restaura TZ ao terminar ou falhar; o teste específico de UTC continua isolado.
previous_test_tz <- Sys.getenv("TZ", unset = NA_character_)
on.exit({
  if (is.na(previous_test_tz)) Sys.unsetenv("TZ") else Sys.setenv(TZ = previous_test_tz)
}, add = TRUE)
Sys.setenv(TZ = "America/Bahia")

project_root <- normalizePath(getwd(), winslash = "/", mustWork = TRUE)
stopifnot(file.exists(file.path(project_root, "app.r")))
expressions <- parse(file.path(project_root, "app.r"), encoding = "UTF-8")
app <- new.env(parent = globalenv())
# A última expressão despacha o menu/CLI; carregamos apenas as definições.
for (expression in expressions[-length(expressions)]) eval(expression, envir = app)
legacy_expressions <- parse(file.path(project_root, "r/02_integrar_previsao.R"), encoding = "UTF-8")
legacy <- new.env(parent = globalenv())
for (expression in legacy_expressions[-length(legacy_expressions)]) eval(expression, envir = legacy)

scratch <- file.path(project_root, "tests", ".tmp_r_audit", paste0("run-", Sys.getpid(), "-", format(Sys.time(), "%Y%m%d%H%M%S")))
dir.create(scratch, recursive = TRUE, showWarnings = FALSE)
setwd(scratch)
passed <- 0L
check <- function(name, code) {
  force(code)
  passed <<- passed + 1L
  cat("PASS:", name, "\n")
}

check("sintaxe dos scripts R auxiliares", {
  for (path in c("r/01_carregar_dados.R", "r/02_integrar_previsao.R", "r/temporal_utils.R")) {
    parse(file.path(project_root, path), encoding = "UTF-8")
  }
})

check("estatisticas ignoram NA, NaN e infinitos", {
  output <- capture.output(app$describe_numeric("temp_c", c(1, 2, 3, NA, NaN, Inf, -Inf)))
  stopifnot(any(grepl("ignorados", output)), any(grepl(": 2.00", output, fixed = TRUE)))
  stopifnot(!any(grepl("Inf|NaN", output)))
  empty <- capture.output(app$describe_numeric("temp_c", c(NA_real_, Inf)))
  stopifnot(any(grepl("nenhum valor finito", empty)))
})

check("regressoes inviaveis nao criam graficos", {
  constant_x <- capture.output(app$plot_regression("temp_c", "umidade", rep(24, 5), 1:5))
  constant_y <- capture.output(app$plot_regression("temp_c", "umidade", 1:5, rep(40, 5)))
  few_pairs <- capture.output(app$plot_regression("temp_c", "umidade", c(1, 2, Inf), 1:3))
  mismatch <- capture.output(app$plot_regression("temp_c", "umidade", 1:3, 1:4))
  singular <- capture.output(app$plot_regression("temp_c", "umidade", 1e15 + 1:5, 1:5))
  stopifnot(all(vapply(list(constant_x, constant_y, few_pairs, mismatch, singular), function(x) any(grepl("ignorada", x)), logical(1))))
  stopifnot(!dir.exists("dados/plots"))
})

check("regressao valida usa apenas pares finitos", {
  app$plot_regression("temp_c", "umidade", c(1, 2, 3, 4, Inf, NA), c(2, 5, 5, 9, 99, 0))
  output <- "dados/plots/regressao_temperatura_c_vs_umidade.png"
  stopifnot(file.exists(output), file.info(output)$size > 0)
})

check("graficos aceitam uma leitura, constantes e nao finitos", {
  app$plot_numeric("temp_c", c(24, NA, Inf), subdir = "single")
  app$plot_numeric("temp_c", rep(24, 5), subdir = "constant")
  app$plot_numeric("temp_c", c(NA_real_, Inf), subdir = "empty")
  stopifnot(file.exists("dados/plots/single/grafico_temperatura_c.png"))
  stopifnot(file.exists("dados/plots/constant/grafico_temperatura_c.png"))
  stopifnot(!dir.exists("dados/plots/empty"))
})

check("timestamps mistos respeitam fuso local, Z e offsets", {
  times <- app$parse_timestamps(c("2026-10-31T21:00:00", "2026-11-01T00:00:00Z", "2026-10-31T21:00:00-03:00", "2026-11-01T01:00:00+0100"), default_tz = "Etc/GMT+3")
  stopifnot(length(unique(as.numeric(times))) == 1L)
  hourly <- app$parse_timestamps(c("2026-11-01T00:00", "2026-11-01T00:00Z"), default_tz = "UTC")
  stopifnot(all(as.numeric(hourly) == as.numeric(times[1])))
  invalid <- app$parse_timestamps(c("invalid", NA, "2026-11-01T00:00:99", "2026-11-01T00:00junk"))
  stopifnot(all(is.na(invalid)))
})

check("vizinho temporal cobre empates, pontas e timestamps invalidos", {
  refs <- as.POSIXct(c(3600, 0, NA), origin = "1970-01-01", tz = "UTC")
  times <- as.POSIXct(c(1800, -100, 7200, NA), origin = "1970-01-01", tz = "UTC")
  stopifnot(identical(app$find_nearest_index(times, refs), c(1L, 2L, 1L, NA_integer_)))
  no_refs <- tryCatch(app$find_nearest_index(times, refs[3]), error = function(e) e)
  stopifnot(inherits(no_refs, "error"), grepl("timestamps", conditionMessage(no_refs)))
})

check("horario Bahia conserva instante e associacao ao formatar", {
  input <- c("2026-10-31T21:33:50", "2026-11-01T00:33:50Z", "2026-10-31T21:33:50-03:00")
  parsed <- app$parse_timestamps(input, default_tz = "America/Bahia")
  original <- as.POSIXct("2026-10-31 21:33:50", tz = "America/Bahia")
  stopifnot(all(as.numeric(parsed) == as.numeric(original)))
  stopifnot(identical(attr(parsed, "tzone"), "America/Bahia"))
  formatted <- app$format_timestamps(parsed)
  stopifnot(all(formatted == "2026-10-31T21:33:50-03:00"))
  after <- app$parse_timestamps(formatted)
  forecast <- app$parse_timestamps(c("2026-11-01T00:00", "2026-11-01T01:00"), default_tz = "UTC")
  stopifnot(identical(as.numeric(parsed), as.numeric(after)))
  stopifnot(identical(app$find_nearest_index(parsed, forecast), app$find_nearest_index(after, forecast)))
})

check("apresentacao Bahia nao muda interpretacao de captura em outro fuso", {
  previous_tz <- Sys.getenv("TZ", unset = NA_character_)
  Sys.setenv(TZ = "UTC")
  parsed <- app$parse_timestamps(c("2026-10-31T21:33:50", "2026-10-31T21:33:50-03:00"))
  formatted <- app$format_timestamps(parsed)
  if (is.na(previous_tz)) Sys.unsetenv("TZ") else Sys.setenv(TZ = previous_tz)
  stopifnot(formatted[1] == "2026-10-31T18:33:50-03:00")
  stopifnot(formatted[2] == "2026-10-31T21:33:50-03:00")
  stopifnot(as.numeric(parsed[2]) - as.numeric(parsed[1]) == 10800)
  stopifnot(identical(as.numeric(app$parse_timestamps(formatted)), as.numeric(parsed)))
})

check("interpolacao ordena previsao e resolve invalidos e duplicatas", {
  times <- legacy$parse_timestamps(c("2026-11-01T02:00", "invalid", "2026-11-01T00:00", "2026-11-01T01:00", "2026-11-01T00:00"), default_tz = "UTC")
  values <- c(20, 99, 0, 10, 900)
  stopifnot(identical(legacy$ordered_forecast_indices(times), c(3L, 4L, 1L)))
  iot <- legacy$parse_timestamps(c("2026-11-01T00:30Z", "2026-11-01T01:30Z", "2026-10-30T00:00Z", "2026-11-02T00:00Z", "invalid"))
  interpolated <- legacy$interpolate_forecast(iot, times, values)
  stopifnot(identical(interpolated, c(5, 15, 0, 20, NA_real_)))
  ordered <- legacy$ordered_forecast_indices(times)
  nearest <- legacy$find_nearest_index(iot, times[ordered])
  stopifnot(identical(nearest, c(1L, 2L, 1L, 3L, NA_integer_)))
})

check("interpolacao nao preenche valores ausentes e aceita previsao unica", {
  reference <- legacy$parse_timestamps(c("2026-11-01T00:00", "2026-11-01T01:00", "2026-11-01T02:00"), default_tz = "UTC")
  queries <- legacy$parse_timestamps(c("2026-11-01T00:30Z", "2026-11-01T02:00Z", "invalid"))
  stopifnot(identical(legacy$interpolate_forecast(queries, reference, c(0, Inf, 20)), c(NA_real_, 20, NA_real_)))
  stopifnot(identical(legacy$interpolate_forecast(queries, reference[1], 7), c(7, 7, NA_real_)))
  invalid <- tryCatch(legacy$interpolate_forecast(queries, reference[NA_integer_], NA_real_), error = function(e) e)
  stopifnot(inherits(invalid, "error"))
})

check("relatorio preserva redirecionamentos preexistentes", {
  sink("outer.txt")
  depth <- sink.number()
  app$with_report("inner.txt", cat("inner report\n"))
  preserved <- sink.number() == depth
  app_error <- tryCatch(app$with_report("error.txt", stop("expected")), error = function(e) e)
  preserved <- preserved && sink.number() == depth
  sink()
  stopifnot(preserved, inherits(app_error, "error"))
})

check("menu encerra quando stdin termina", {
  app$read_input <- function(prompt_text = "") NA_character_
  output <- capture.output(app$main())
  stopifnot(any(grepl("Entrada encerrada", output)))
})

check("integracao salva fixture sem confundir timestamps invalidos", {
  dir.create("dados/previsao_tempo", recursive = TRUE, showWarnings = FALSE)
  iot <- data.frame(ts_iso = c("2026-11-01T00:30:00Z", "2026-10-30T00:00:00Z", "invalid"), t_rel_ms = c(4294967295, 2, 3),
    umidade = c(40, 50, NA), temp_c = c(24, Inf, 25), ph_corr = rep(6.4, 3), N = rep(1, 3), P = rep(1, 3), K = rep(1, 3), bomba_fw = c(1, 1, 0))
  weather <- data.frame(city = "Fixture", country = "BR", latitude = 0, longitude = 0,
    ts_iso = c("2026-11-01T00:00", "invalid", "2026-11-01T01:00"), temp_c = c(24, NA, 25), umidade = c(60, NA, 70),
    rain_mm = c(0, NA, 1), wind_ms = c(2, NA, 3), weathercode = c(0, NA, 1))
  write.csv(iot, "dados/historico_irrigacao.csv", row.names = FALSE)
  write.csv(weather, "dados/previsao_tempo/previsao_tempo.csv", row.names = FALSE)
  capture.output(app$run_integration_and_save())
  merged <- read.csv("dados/analises/integrada/dados_integrados_iot_previsao.csv")
  report <- readLines("dados/analises/integrada/analise_integrada.txt", encoding = "UTF-8", warn = FALSE)
  stopifnot(nrow(merged) == 3L, identical(merged$forecast_temp_c, c(24L, 24L, NA_integer_)))
  stopifnot(any(grepl("Timestamps IoT.*: 1", report)), any(grepl("fora da cobertura.*: 1", report)))
  stopifnot(!any(grepl("Mean.*Inf", report)))
  stopifnot(is.infinite(merged$temp_c[2]))
  stopifnot(merged$t_rel_ms[1] == 4294967295)
  stopifnot(merged$ts_iso[1] == "2026-10-31T21:30:00-03:00")
  capture.output(app$run_analysis_and_save())
  capture.output(app$run_weather_analysis_and_save())
  stopifnot(file.exists("dados/analises/iot/analise_historico.txt"))
  stopifnot(file.exists("dados/analises/previsao/analise_previsao.txt"))
  processed_iot <- read.csv("dados/analises/iot/analise_historico.csv")
  processed_weather <- read.csv("dados/analises/previsao/analise_previsao.csv")
  stopifnot(processed_iot$ts_iso[1] == "2026-10-31T21:30:00-03:00")
  stopifnot(processed_weather$ts_iso[1] == "2026-11-01T00:00:00+00:00")
})

check("integracao independente usa UTC e interpola fixture desordenada", {
  iot <- data.frame(ts_iso = c("2026-10-31T21:30:00", "2026-10-30T00:00:00Z", "invalid"), t_rel_ms = 1:3,
    umidade = c(40, 50, NA), temp_c = c(24, 25, 26), ph_corr = rep(6.4, 3), N = 1, P = 1, K = 1, bomba_fw = c(1, 1, 0))
  weather <- data.frame(city = c("Later", "Invalid", "First", "Duplicate"), country = "BR", latitude = 0, longitude = 0,
    ts_iso = c("2026-11-01T01:00", "invalid", "2026-11-01T00:00", "2026-11-01T00:00"), temp_c = c(30, NA, 20, 999),
    umidade = c(70, NA, 60, 999), rain_mm = c(2, NA, 0, 999), wind_ms = c(4, NA, 2, 999), weathercode = c(1, NA, 0, 99))
  write.csv(iot, "dados/historico_irrigacao.csv", row.names = FALSE)
  write.csv(weather, "dados/previsao_tempo/previsao_tempo.csv", row.names = FALSE)
  output <- capture.output(merged <- legacy$main())
  stopifnot(identical(merged$forecast_temp_c, c(25, 20, NA_real_)))
  stopifnot(identical(merged$forecast_weathercode, c(0L, 0L, NA_integer_)))
  stopifnot(merged$forecast_city[1] == "First", merged$ts_iso[1] == "2026-10-31T21:30:00-03:00")
  stopifnot(any(grepl("fora: 1", output)), any(grepl("America/Bahia", output)))
  legacy_forecast <- legacy$load_weather_data()
  stopifnot(as.numeric(legacy_forecast$ts_iso[1]) == as.numeric(as.POSIXct("2026-11-01 01:00:00", tz = "UTC")))
})

check("helper localizado por CLI e source fora da raiz do modulo", {
  rscript <- file.path(R.home("bin"), if (.Platform$OS.type == "windows") "Rscript.exe" else "Rscript")
  scripts <- c("app.r", "r/02_integrar_previsao.R")
  for (script in scripts) {
    absolute <- file.path(project_root, script)
    args <- if (script == "app.r") "integrar" else character()
    output <- system2(rscript, c(shQuote(absolute), args), stdout = TRUE, stderr = TRUE)
    stopifnot(is.null(attr(output, "status")))
    runner <- paste0("source_", basename(script))
    writeLines(paste0("source(", encodeString(absolute, quote = "\""), ", encoding = \"UTF-8\")"), runner)
    sourced <- system2(rscript, c(shQuote(runner), args), stdout = TRUE, stderr = TRUE)
    stopifnot(is.null(attr(sourced, "status")))
  }
})

cat("\n", passed, "grupos de testes R aprovados. Fixtures:", scratch, "\n")
setwd(project_root)
}

run_tests()
