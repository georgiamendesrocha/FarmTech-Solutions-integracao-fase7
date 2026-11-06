# app.r
# Menu interativo para carregar dados e executar análises em R.

temporal_helper <- file.path("r", "temporal_utils.R")
if (!file.exists(temporal_helper)) {
  script_file <- tryCatch(sys.frame(1)$ofile, error = function(e) NULL)
  if (is.null(script_file)) script_file <- sub("^--file=", "", grep("^--file=", commandArgs(), value = TRUE)[1])
  temporal_helper <- file.path(dirname(normalizePath(script_file)), "r", "temporal_utils.R")
}
source(temporal_helper, local = TRUE, encoding = "UTF-8")

mode_value <- function(x) {
  x <- x[!is.na(x)]
  if (length(x) == 0) {
    return(NA)
  }
  ux <- unique(x)
  if (length(ux) == 0) {
    return(NA)
  }
  tab <- tabulate(match(x, ux))
  modes <- ux[tab == max(tab)]
  if (length(modes) == 1) {
    return(modes)
  }
  return(modes)
}

ensure_plot_dir <- function(subdir = NULL) {
  out_dir <- file.path("dados", "plots")
  if (!is.null(subdir) && nzchar(subdir)) {
    out_dir <- file.path(out_dir, subdir)
  }
  if (!dir.exists(out_dir)) {
    dir.create(out_dir, recursive = TRUE)
  }
  out_dir
}

save_plot <- function(filename, plot_expr, subdir = NULL) {
  out_dir <- ensure_plot_dir(subdir)
  path <- file.path(out_dir, filename)
  png(path, width = 900, height = 600)
  on.exit(dev.off(), add = TRUE)
  plot_expr()
  cat("Salvo plot:", path, "\n")
}

normalize_plot_base <- function(name) {
  base <- tolower(name)
  base <- gsub("[^a-z0-9]+", "_", base)
  base <- switch(base,
    "humidity" = "umidade",
    "forecast_humidity" = "umidade_prevista",
    "forecast_umidade" = "umidade_prevista",
    "temp_c" = "temperatura_c",
    "forecast_temp_c" = "temperatura_prevista_c",
    "rain_mm" = "chuva_mm",
    "forecast_rain_mm" = "chuva_prevista_mm",
    "wind_ms" = "vento_ms",
    "forecast_wind_ms" = "vento_previsto_ms",
    "weathercode" = "codigo_tempo",
    "forecast_weathercode" = "codigo_tempo_previsto",
    "bomba_fw" = "bomba_agua",
    "ph_corr" = "ph_corrigido",
    "t_rel_ms" = "tempo_relativo_ms",
    "ph_base" = "ph_base",
    base
  )
  base
}

translate_name <- function(name) {
  labels <- list(
    "humidity" = "umidade (%)",
    "forecast_humidity" = "umidade prevista (%)",
    "forecast_umidade" = "umidade prevista (%)",
    "temp_c" = "temperatura (°C)",
    "forecast_temp_c" = "temperatura prevista (°C)",
    "rain_mm" = "chuva (mm)",
    "forecast_rain_mm" = "chuva prevista (mm)",
    "wind_ms" = "vento (m/s)",
    "forecast_wind_ms" = "vento previsto (m/s)",
    "weathercode" = "código do tempo",
    "forecast_weathercode" = "código do tempo previsto",
    "bomba_fw" = "bomba de água",
    "ph_corr" = "pH corrigido",
    "ph_base" = "pH base",
    "t_rel_ms" = "tempo desde reset (ms)",
    "N" = "N",
    "P" = "P",
    "K" = "K"
  )
  if (!is.null(labels[[name]])) {
    return(labels[[name]])
  }
  name
}

describe_numeric <- function(name, x) {
  display_name <- translate_name(name)
  if (!is.numeric(x)) {
    cat("\n", display_name, ": não é numérico.\n", sep = "")
    return()
  }

  excluded <- sum(!is.finite(x))
  x <- x[is.finite(x)]
  if (excluded > 0) {
    cat("Valores ausentes ou não finitos ignorados em", display_name, ":", excluded, "\n")
  }
  if (length(x) == 0) {
    cat("\n", display_name, ": nenhum valor finito disponível.\n", sep = "")
    return()
  }

  cat("\n---", display_name, "---\n")
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

summary_finite <- function(dados) {
  # Limpa apenas a cópia usada no resumo; preserva os dados de origem/exportação.
  for (col in names(dados)) {
    if (is.numeric(dados[[col]])) {
      dados[[col]][!is.finite(dados[[col]])] <- NA
    }
  }
  summary(dados)
}

plot_numeric <- function(name, x, subdir = NULL) {
  if (!is.numeric(x)) {
    return()
  }
  x <- x[is.finite(x)]
  if (length(x) == 0) {
    return()
  }

  display_name <- translate_name(name)
  filename <- paste0("grafico_", normalize_plot_base(name), ".png")
  save_plot(filename, function() {
    par(mfrow = c(2, 2), mar = c(4, 4, 3, 1))
    hist(x, main = paste("Histograma de", display_name), xlab = display_name, col = "skyblue", border = "white")
    boxplot(x, main = paste("Boxplot de", display_name), ylab = display_name, col = "lightgreen")
    plot(x, type = "l", main = paste("Série de", display_name), xlab = "Índice", ylab = display_name, col = "blue")
    if (length(unique(x)) >= 2) {
      plot(density(x), main = paste("Densidade de", display_name), xlab = display_name)
    } else {
      plot.new()
      title(main = paste("Densidade de", display_name))
      text(0.5, 0.5, "Densidade não estimada: dados insuficientes ou constantes.")
    }
  }, subdir = subdir)
}

plot_bar <- function(name, x, subdir = NULL) {
  if (length(x) == 0) {
    return()
  }
  counts <- table(x)
  if (length(counts) == 0) {
    return()
  }
  display_name <- translate_name(name)
  filename <- paste0("barra_", normalize_plot_base(name), ".png")
  save_plot(filename, function() {
    barplot(counts, main = paste("Frequência de", display_name), col = "orange", las = 1)
  }, subdir = subdir)
}

plot_regression <- function(x_name, y_name, x, y, subdir = NULL) {
  if (!is.numeric(x) || !is.numeric(y)) {
    return()
  }
  if (length(x) != length(y) || length(x) == 0) {
    cat("Regressão ignorada: pares ausentes ou vetores de tamanhos diferentes.\n")
    return()
  }
  complete <- is.finite(x) & is.finite(y)
  if (sum(complete) < 3) {
    cat("Regressão ignorada:", x_name, "e", y_name, "com menos de 3 pares finitos.\n")
    return()
  }

  x <- x[complete]
  y <- y[complete]
  if (length(unique(x)) < 2 || length(unique(y)) < 2) {
    cat("Regressão ignorada:", x_name, "ou", y_name, "sem variação nos dados.\n")
    return()
  }
  model <- tryCatch(lm(y ~ x), error = function(e) NULL)
  if (is.null(model) || model$rank < 2 || any(!is.finite(coef(model)))) {
    cat("Regressão ignorada: ajuste numericamente inviável.\n")
    return()
  }
  r_squared <- 1 - sum(residuals(model)^2) / sum((y - mean(y))^2)
  if (!is.finite(r_squared)) {
    cat("Regressão ignorada: R² não definido para estes dados.\n")
    return()
  }
  filename <- paste0("regressao_", normalize_plot_base(x_name), "_vs_", normalize_plot_base(y_name), ".png")
  display_x <- translate_name(x_name)
  display_y <- translate_name(y_name)
  save_plot(filename, function() {
    plot(x, y,
      main = paste("Regressão:", display_y, "vs", display_x),
      xlab = display_x,
      ylab = display_y,
      pch = 19,
      col = "blue"
    )
    abline(model, col = "red", lwd = 2)
    legend_text <- sprintf("y = %.2f x + %.2f\nR² = %.3f",
      coef(model)[2], coef(model)[1], r_squared)
    legend("topright", legend = legend_text, bty = "n", text.col = "black")
  }, subdir = subdir)
}

load_data <- function() {
  paths <- c(
    file.path("dados", "historico_irrigacao.csv"),
    file.path("dados", "captura_serial.csv")
  )

  ok <- file.exists(paths)
  if (!any(ok)) {
    stop("Nenhum CSV encontrado em dados/. Gere historico com scripts/serial_grava_csv.py")
  }

  arquivo <- paths[which(ok)[1]]
  message("A usar IoT: ", arquivo)

  dados <- read.csv(arquivo, stringsAsFactors = FALSE)
  if ("ts_iso" %in% names(dados)) {
    dados$ts_iso <- parse_timestamps(dados$ts_iso)
  }

  convert_to_int <- function(col) {
    if (col %in% names(dados)) {
      dados[[col]] <<- as.integer(dados[[col]])
    }
  }

  # millis() do ESP32 é uint32; R integer estoura após 2^31 - 1 ms.
  if ("t_rel_ms" %in% names(dados)) {
    dados$t_rel_ms <- as.numeric(dados$t_rel_ms)
  }
  convert_to_int("N")
  convert_to_int("P")
  convert_to_int("K")
  convert_to_int("bomba_fw")

  list(dados = dados, arquivo = arquivo)
}

load_weather_data <- function() {
  arquivo_integrado <- file.path("..", "..", ".runtime", "exports", "fase2", "previsao_tempo.csv")
  arquivo_original <- file.path("dados", "previsao_tempo", "previsao_tempo.csv")
  arquivo <- if (file.exists(arquivo_integrado)) arquivo_integrado else arquivo_original
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

  list(dados = dados, arquivo = arquivo)
}

with_report <- function(report_path, expr) {
  previous_sinks <- sink.number()
  sink(report_path, split = TRUE)
  on.exit({
    while (sink.number() > previous_sinks) {
      sink()
    }
  }, add = TRUE)
  force(expr)
}

ensure_output_dir <- function(subdir = NULL) {
  out_dir <- file.path("dados", "analises")
  if (!is.null(subdir) && nzchar(subdir)) {
    out_dir <- file.path(out_dir, subdir)
  }
  if (!dir.exists(out_dir)) {
    dir.create(out_dir, recursive = TRUE)
  }
  out_dir
}

run_analysis_and_save <- function() {
  loaded <- load_data()
  dados <- loaded$dados
  display_data <- format_timestamp_columns(dados)
  out_dir <- ensure_output_dir("iot")
  out_report <- file.path(out_dir, "analise_historico.txt")
  out_data <- file.path(out_dir, "analise_historico.csv")

  cat("\nExecutando análise de IoT e salvando relatório...\n")
  with_report(out_report, {
    cat("Arquivo CSV usado:", loaded$arquivo, "\n")
    cat("Horários apresentados em", IOT_TIMEZONE, "com offset UTC explícito; IoT sem fuso usa", capture_timezone(), "(UTC se o fuso local estiver indisponível).\n")
    cat("\n=== Análise dos dados de IoT ===\n")
    cat("Número de linhas:", nrow(dados), "\n")
    cat("Número de colunas:", ncol(dados), "\n\n")
    cat("Primeiras 6 linhas:\n")
    print(head(display_data))
    cat("\nEstrutura dos dados:\n")
    str(display_data)
    cat("\nResumo estatístico (valores não finitos tratados como ausentes):\n")
    print(summary_finite(display_data))
    cat("\n=== Medidas de tendência central e dispersão ===\n")
    for (col in c("t_rel_ms", "umidade", "temp_c", "ph_base", "ph_corr")) {
      if (col %in% names(dados)) {
        describe_numeric(col, dados[[col]])
      }
    }
    cat("\n=== Medidas separatrizes ===\n")
    for (col in c("t_rel_ms", "umidade", "temp_c", "ph_base", "ph_corr")) {
      if (col %in% names(dados)) {
        cat("\n", translate_name(col), "\n", sep = "")
        print(quantile(dados[[col]][is.finite(dados[[col]])], probs = c(0, 0.25, 0.5, 0.75, 1), na.rm = TRUE))
      }
    }
    cat("\n=== Gráficos salvos em dados/plots/iot/ ===\n")
    plot_numeric("umidade", dados$umidade, subdir = "iot")
    plot_numeric("temp_c", dados$temp_c, subdir = "iot")
    plot_numeric("ph_corr", dados$ph_corr, subdir = "iot")
    plot_numeric("t_rel_ms", dados$t_rel_ms, subdir = "iot")
    plot_bar("N", dados$N, subdir = "iot")
    plot_bar("P", dados$P, subdir = "iot")
    plot_bar("K", dados$K, subdir = "iot")
    plot_bar("bomba_fw", dados$bomba_fw, subdir = "iot")
    cat("\n=== Gráficos de regressão salvos em dados/plots/regressao/ ===\n")
    plot_regression("temp_c", "umidade", dados$temp_c, dados$umidade, subdir = "regressao")
    plot_regression("temp_c", "ph_corr", dados$temp_c, dados$ph_corr, subdir = "regressao")
    plot_regression("t_rel_ms", "umidade", dados$t_rel_ms, dados$umidade, subdir = "regressao")
  })

  write.csv(display_data, out_data, row.names = FALSE)
  cat("\nAnálise de IoT concluída.\n")
  cat("Relatório gravado em:", out_report, "\n")
  cat("Dados processados gravados em:", out_data, "\n")
}

run_weather_analysis_and_save <- function() {
  loaded <- load_weather_data()
  dados <- loaded$dados
  display_data <- format_timestamp_columns(dados, tz = "UTC")
  out_dir <- ensure_output_dir("previsao")
  out_report <- file.path(out_dir, "analise_previsao.txt")
  out_data <- file.path(out_dir, "analise_previsao.csv")

  cat("\nExecutando análise de previsão do tempo e salvando relatório...\n")
  with_report(out_report, {
    cat("Arquivo CSV usado:", loaded$arquivo, "\n")
    cat("Horários meteorológicos apresentados em UTC com offset explícito.\n")
    cat("\n=== Análise de previsão do tempo ===\n")
    cat("Número de linhas:", nrow(dados), "\n")
    cat("Número de colunas:", ncol(dados), "\n\n")
    cat("Primeiras 6 linhas:\n")
    print(head(display_data))
    cat("\nEstrutura dos dados:\n")
    str(display_data)
    cat("\nResumo estatístico (valores não finitos tratados como ausentes):\n")
    print(summary_finite(display_data))
    cat("\n=== Medidas de tendência central e dispersão ===\n")
    for (col in c("temp_c", "umidade", "rain_mm", "wind_ms")) {
      if (col %in% names(dados)) {
        describe_numeric(col, dados[[col]])
      }
    }
    cat("\n=== Medidas separatrizes ===\n")
    for (col in c("temp_c", "umidade", "rain_mm", "wind_ms")) {
      if (col %in% names(dados)) {
        cat("\n", translate_name(col), "\n", sep = "")
        print(quantile(dados[[col]][is.finite(dados[[col]])], probs = c(0, 0.25, 0.5, 0.75, 1), na.rm = TRUE))
      }
    }
    cat("\n=== Gráficos salvos em dados/plots/previsao/ ===\n")
    plot_numeric("temp_c", dados$temp_c, subdir = "previsao")
    plot_numeric("umidade", dados$umidade, subdir = "previsao")
    plot_numeric("rain_mm", dados$rain_mm, subdir = "previsao")
    plot_numeric("wind_ms", dados$wind_ms, subdir = "previsao")
    cat("\n=== Gráficos de regressão salvos em dados/plots/regressao/ ===\n")
    plot_regression("temp_c", "umidade", dados$temp_c, dados$umidade, subdir = "regressao")
    plot_regression("temp_c", "rain_mm", dados$temp_c, dados$rain_mm, subdir = "regressao")
    plot_regression("temp_c", "wind_ms", dados$temp_c, dados$wind_ms, subdir = "regressao")
  })

  write.csv(display_data, out_data, row.names = FALSE)
  cat("\nAnálise de previsão concluída.\n")
  cat("Relatório gravado em:", out_report, "\n")
  cat("Dados processados gravados em:", out_data, "\n")
}

run_integration_and_save <- function() {
  iot_loaded <- load_data()
  weather_loaded <- load_weather_data()

  iot <- iot_loaded$dados
  weather <- weather_loaded$dados

  if (!"ts_iso" %in% names(iot) || !"ts_iso" %in% names(weather)) {
    stop("Ambos os datasets precisam ter a coluna ts_iso como timestamp UTC.")
  }

  # Impede associação de registros IoT e previsões de períodos sem sobreposição.
  valid_iot <- as.numeric(iot$ts_iso)
  valid_weather <- as.numeric(weather$ts_iso)
  valid_iot <- valid_iot[is.finite(valid_iot)]
  valid_weather <- valid_weather[is.finite(valid_weather)]
  if (length(valid_iot) == 0 || length(valid_weather) == 0 ||
      max(valid_iot) < min(valid_weather) || min(valid_iot) > max(valid_weather)) {
    stop(paste0("IoT e previsao meteorologica nao possuem datas sobrepostas. ",
                "Nao e correto integrar registros de periodos diferentes."))
  }

  indices <- find_nearest_index(iot$ts_iso, weather$ts_iso)
  gaps <- abs(as.numeric(difftime(weather$ts_iso[indices], iot$ts_iso, units = "secs")))
  forecast_range <- range(as.numeric(weather$ts_iso)[is.finite(as.numeric(weather$ts_iso))])
  outside_range <- as.numeric(iot$ts_iso) < forecast_range[1] | as.numeric(iot$ts_iso) > forecast_range[2]
  merged <- data.frame(
    iot,
    forecast_ts_iso = weather$ts_iso[indices],
    forecast_temp_c = weather$temp_c[indices],
    forecast_umidade = weather$umidade[indices],
    forecast_rain_mm = weather$rain_mm[indices],
    forecast_wind_ms = weather$wind_ms[indices],
    forecast_weathercode = weather$weathercode[indices],
    forecast_city = weather$city[indices],
    forecast_country = weather$country[indices],
    forecast_latitude = weather$latitude[indices],
    forecast_longitude = weather$longitude[indices],
    stringsAsFactors = FALSE
  )

  merged <- format_timestamp_columns(merged)

  out_dir <- ensure_output_dir("integrada")
  out_path <- file.path(out_dir, "dados_integrados_iot_previsao.csv")
  out_report <- file.path(out_dir, "analise_integrada.txt")

  write.csv(merged, out_path, row.names = FALSE)
  cat("\nExecutando integração e salvando relatório...\n")
  with_report(out_report, {
    cat("Arquivo IoT usado:", iot_loaded$arquivo, "\n")
    cat("Arquivo de previsao usado:", weather_loaded$arquivo, "\n")
    cat("Associação temporal: previsão com menor distância absoluta em segundos; empate pela primeira linha do CSV.\n")
    cat("Sem interpolação ou tolerância máxima; fora da cobertura, usa o horário válido mais próximo.\n")
    cat("Timestamps IoT inválidos (sem associação):", sum(is.na(indices)), "\n")
    cat("Timestamps de previsão inválidos (ignorados):", sum(!is.finite(as.numeric(weather$ts_iso))), "\n")
    cat("Registros IoT fora da cobertura da previsão:", sum(outside_range, na.rm = TRUE), "\n")
    if (any(is.finite(gaps))) {
      cat("Maior distância temporal da associação (segundos):", max(gaps[is.finite(gaps)]), "\n")
    }
    cat("Horários exportados em", IOT_TIMEZONE, "com offset explícito; IoT sem fuso usa", capture_timezone(), "; previsão sem fuso é UTC.\n")
    cat("\n=== Resumo do dataset integrado (valores não finitos tratados como ausentes) ===\n")
    print(summary_finite(merged))
    cat("\n=== Medidas de tendência central e dispersão (integração) ===\n")
    for (col in c("umidade", "temp_c", "ph_corr", "forecast_temp_c", "forecast_umidade", "forecast_rain_mm", "forecast_wind_ms")) {
      if (col %in% names(merged)) {
        describe_numeric(col, merged[[col]])
      }
    }
    cat("\n=== Medidas separatrizes ===\n")
    for (col in c("umidade", "ph_corr", "forecast_temp_c", "forecast_rain_mm")) {
      if (col %in% names(merged)) {
        cat("\n", translate_name(col), "\n", sep = "")
        print(quantile(merged[[col]][is.finite(merged[[col]])], probs = c(0, 0.25, 0.5, 0.75, 1), na.rm = TRUE))
      }
    }
    cat("\n=== Gráficos de regressão entre IoT e previsão salvos em dados/plots/regressao/ ===\n")
    if (all(c("temp_c", "forecast_temp_c") %in% names(merged))) {
      plot_regression("temp_c", "forecast_temp_c", merged$temp_c, merged$forecast_temp_c, subdir = "regressao")
    }
    if (all(c("umidade", "forecast_umidade") %in% names(merged))) {
      plot_regression("umidade", "forecast_umidade", merged$umidade, merged$forecast_umidade, subdir = "regressao")
    }
  })

  cat("\nDataset integrado gravado em:", out_path, "\n")
  cat("Relatório integrado gravado em:", out_report, "\n")
}

read_input <- function(prompt_text = "") {
  cat(prompt_text)
  flush.console()
  resposta <- readLines("stdin", n = 1)
  if (length(resposta) == 0) {
    return(NA_character_)
  }
  trimws(resposta)
}

show_menu <- function() {
  cat("\n===== APP de Análise R =====\n")
  cat("1 - Análise de IoT e salvar relatório\n")
  cat("2 - Análise de previsão do tempo e salvar relatório\n")
  cat("3 - Integrar IoT e previsão do tempo\n")
  cat("4 - Voltar ao menu principal\n")
}

main <- function() {
  repeat {
    show_menu()
    escolha <- read_input("Escolha uma opção: ")
    if (is.na(escolha)) {
      cat("\nEntrada encerrada. Retornando ao menu principal...\n")
      break
    }

    if (escolha == "1") {
      tryCatch(run_analysis_and_save(), error = function(e) cat("Erro:", e$message, "\n"))
    } else if (escolha == "2") {
      tryCatch(run_weather_analysis_and_save(), error = function(e) cat("Erro:", e$message, "\n"))
    } else if (escolha == "3") {
      tryCatch(run_integration_and_save(), error = function(e) cat("Erro:", e$message, "\n"))
    } else if (escolha == "4") {
      cat("Retornando ao menu principal...\n")
      break
    } else {
      cat("Opção inválida. Digite 1, 2, 3 ou 4.\n")
    }
  }
}

args <- commandArgs(trailingOnly = TRUE)
if (length(args) == 0) {
  main()
} else if (args[1] == "iot") {
  run_analysis_and_save()
} else if (args[1] == "weather" || args[1] == "previsao") {
  run_weather_analysis_and_save()
} else if (args[1] == "integrate" || args[1] == "integrar") {
  run_integration_and_save()
} else {
  stop("Usage: Rscript app.r [iot|previsao|integrar]")
}
