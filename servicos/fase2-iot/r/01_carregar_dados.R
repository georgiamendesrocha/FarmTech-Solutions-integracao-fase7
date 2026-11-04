# Carrega CSV de irrigacao para analise em R (historico, captura antiga ou exemplo).

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

paths <- c(
  file.path("dados", "historico_irrigacao.csv"),
  file.path("dados", "captura_serial.csv")
)

ok <- file.exists(paths)
if (!any(ok)) {
  stop(
    paste0(
      "Nenhum CSV em dados/. Gere historico com Monitor PlatformIO + RFC2217 ou COM ",
      "e verifique o README para instruções."
    )
  )
}

arquivo <- paths[which(ok)[1]]
message("A usar: ", arquivo)

dados <- read.csv(arquivo, stringsAsFactors = FALSE)

if ("ts_iso" %in% names(dados)) {
  ts <- dados$ts_iso
  if (any(grepl("Z$", ts))) {
    ts <- gsub("Z$", "", ts)
    dados$ts_iso <- as.POSIXct(ts, format = "%Y-%m-%dT%H:%M:%S", tz = "UTC")
  } else {
    local_tz <- Sys.timezone()
    if (is.na(local_tz) || local_tz == "") {
      local_tz <- ""
    }
    dados$ts_iso <- as.POSIXct(ts, format = "%Y-%m-%dT%H:%M:%S", tz = local_tz)
  }
}

dados$t_rel_ms <- as.integer(dados$t_rel_ms)
dados$N <- as.integer(dados$N)
dados$P <- as.integer(dados$P)
dados$K <- as.integer(dados$K)
dados$bomba_fw <- as.integer(dados$bomba_fw)

str(dados)
cat("\n=== Resumo geral ===\n")
print(summary(dados))

numeric_cols <- c("t_rel_ms", "umidade", "temp_c", "ph_base", "ph_corr")
for (col in numeric_cols) {
  if (col %in% names(dados)) {
    x <- dados[[col]]
    x <- x[!is.na(x)]
    if (length(x) > 0) {
      cat("\n---", col, "---\n")
      cat("mean:", mean(x), "\n")
      cat("median:", median(x), "\n")
      cat("mode:", paste(mode_value(x), collapse = ", "), "\n")
      cat("sd:", sd(x), "\n")
      cat("var:", var(x), "\n")
      cat("range:", paste(range(x), collapse = " a "), "\n")
      cat("quantile(0,0.25,0.5,0.75,1):\n")
      print(quantile(x, probs = c(0, 0.25, 0.5, 0.75, 1), na.rm = TRUE))
    }
  }
}
