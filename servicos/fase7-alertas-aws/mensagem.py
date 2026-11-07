"""Texto do e-mail enviado aos funcionários."""


def assunto(alerta):
    if alerta.get("fonte") == "iot_fase2":
        origem = alerta["origem"]
        selo = {"wokwi": "SIMULAÇÃO WOKWI", "esp32": "ESP32 DECLARADO",
                "exemplo": "EXEMPLO SINTÉTICO", "desconhecida": "ORIGEM NÃO COMPROVADA"}[origem]
        if alerta["historico"]:
            selo = "HISTÓRICO / " + selo
        texto = f"FarmTech [{selo}]: {alerta['alerta']}"
    else:
        texto = f"FarmTech: {alerta['alerta']}"
    return texto[:100]


def corpo(alerta, local):
    if alerta.get("fonte") == "iot_fase2":
        return _corpo_iot(alerta, local)
    nome = local.get("name") or "local não informado"
    admin = local.get("admin1") or ""
    pais = local.get("country") or ""
    lugar = ", ".join(parte for parte in (nome, admin, pais) if parte)
    linhas = [
        "FarmTech Solutions — aviso aos funcionários",
        "",
        f"Local: {lugar}",
        f"Horário UTC do evento: {alerta['instante']}",
        "",
        f"Alerta: {alerta['alerta']}",
    ]
    if alerta.get("umidade") is not None:
        linhas.append(f"Umidade relativa do ar prevista: {alerta['umidade']:.1f}%")
    if alerta.get("chuva_mm") is not None:
        linhas.append(f"Chuva prevista na hora do evento: {alerta['chuva_mm']:.1f} mm")
    linhas.extend([
        "",
        f"Ação corretiva: {alerta['acao']}",
        "",
        "Fonte: previsão da Fase 2 (Open-Meteo), regra do tomate da FarmTech.",
        "",
        "Regra acadêmica: a previsão não mede a umidade do solo.",
        "Confirme as condições do solo e do cultivo antes de acionar a irrigação.",
    ])
    return "\n".join(linhas)


def _corpo_iot(alerta, local):
    leitura = alerta["leitura"]
    fontes = {
        "wokwi": "Simulação de sensores no Wokwi, declarada pelo operador; não é medição física.",
        "esp32": "Captura ESP32 declarada pelo operador; origem física não verificada por este serviço.",
        "exemplo": "Exemplo sintético gerado para teste; não é captura Wokwi nem medição física.",
        "desconhecida": "Origem não comprovada; não classificar como medição física real.",
    }
    modo = ("REPRODUÇÃO HISTÓRICA; este registro não representa uma medição atual."
            if alerta["historico"] else
            "Registro recebido recentemente no PC (até cinco minutos); não comprova nova aquisição válida no DHT22.")
    linhas = [
        "FarmTech Solutions — alerta didático dos sensores da Fase 2",
        "",
        f"Local declarado: {local.get('name') or 'não informado'}",
        f"Dispositivo declarado: {local.get('iot_dispositivo') or 'não informado'}",
        "",
        f"Fonte: CSV do contrato IoT Fase 2. {fontes[alerta['origem']]}",
        f"Modo: {modo}",
        "",
        f"Horário original de recepção no PC: {leitura['_ts_original']}",
        f"Horário UTC de recepção no PC: {alerta['instante']}",
        f"Idade do registro: {alerta['idade_segundos']:.0f} segundos.",
        f"Tempo relativo do firmware: {leitura['t_rel_ms']} ms; reinicia com o dispositivo.",
        "",
        f"Alerta: {alerta['alerta']}",
        "",
        f"Umidade do DHT22/protótipo: {leitura['umidade']:.1f}% (umidade do ar; proxy didático de solo).",
        f"Temperatura ambiente registrada: {leitura['temp_c']:.1f} °C; sem regra de alerta neste serviço.",
        f"LDR: {leitura['ldr']}; pH base simulado: {leitura['ph_base']:.3f}; pH corrigido simulado: {leitura['ph_corr']:.3f}.",
        f"Indicadores N/P/K dos botões: {leitura['N']}/{leitura['P']}/{leitura['K']} (0=ausente, 1=presente; não são concentrações).",
        f"Estado registrado da bomba no firmware: {leitura['bomba_fw']} (0=desligada, 1=ligada).",
        f"Estado esperado pela regra didática do firmware: {'ligada' if alerta['bomba_esperada'] else 'desligada'}.",
        "",
        f"Ação recomendada: {alerta['acao']}",
        "",
        "Critérios didáticos: umidade <45% ou >80%; pH corrigido fora de 6,0–6,8; ausência de N/P/K.",
        "",
        "Sem calibração ou validação agronômica. LDR e botões não medem pH ou nutrientes reais.",
        "O serviço apenas informa o funcionário; não envia comandos nem aciona uma bomba física.",
    ]
    return "\n".join(linhas)
