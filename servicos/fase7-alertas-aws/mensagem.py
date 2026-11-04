"""Texto do e-mail enviado aos funcionários."""


def assunto(alerta):
    texto = f"FarmTech: {alerta['alerta']}"
    return texto[:100]


def corpo(alerta, local):
    nome = local.get("name") or "local não informado"
    admin = local.get("admin1") or ""
    pais = local.get("country") or ""
    lugar = ", ".join(parte for parte in (nome, admin, pais) if parte)
    linhas = [
        "FarmTech Solutions — aviso aos funcionários",
        "",
        f"Local: {lugar}",
        f"Horário UTC do evento: {alerta['instante']}",
        f"Alerta: {alerta['alerta']}",
    ]
    if alerta.get("umidade") is not None:
        linhas.append(f"Umidade prevista: {alerta['umidade']:.1f}%")
    if alerta.get("chuva_mm") is not None:
        linhas.append(f"Chuva prevista: {alerta['chuva_mm']:.1f} mm")
    linhas.extend([
        f"Ação corretiva: {alerta['acao']}",
        "",
        "Fonte: previsão da Fase 2 (Open-Meteo), regra do tomate da FarmTech.",
    ])
    return "\n".join(linhas)
