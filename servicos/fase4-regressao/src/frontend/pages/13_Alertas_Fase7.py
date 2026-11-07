"""Avaliação local dos alertas preservados; esta página não publica mensagens."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[5]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

from farmtech_integracao import fase2, fase7
from farmtech_integracao.contracts import Result
from farmtech_integracao.ui import apply_theme, info_card, navigation_link

st.set_page_config(page_title="Alertas — Fase 7 | FarmTech", page_icon="🔔", layout="wide")
apply_theme()
st.caption("FARMTECH SOLUTIONS · FASE 7")
st.title("Alertas — Fase 7")
info_card("Consulte os dados dos sensores e as condições meteorológicas, identifique possíveis alertas e visualize as ações corretivas recomendadas. As análises são demonstrativas e não enviam notificações reais.")

try:
    available = fase7.availability()
except Exception:
    available = Result("unavailable", "Não foi possível verificar o serviço local de alertas.")
if not available.ok:
    st.warning(available.message)
    st.stop()

mode = st.radio("Fonte da avaliação", ["Demonstração local", "CSV IoT da Fase 2", "Previsão Open-Meteo"],
                key="fase7_mode", horizontal=True)
new_result = None


def fingerprint(*values):
    return hashlib.sha256(json.dumps(values, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def evaluate(action, *args, **kwargs):
    try:
        with st.spinner("Avaliando os dados e preparando a prévia local..."):
            return action(*args, **kwargs)
    except Exception:
        # Uma falha de serviço opcional não interrompe as demais páginas.
        return Result("error", "Avaliação indisponível. Confira o arquivo e a disponibilidade do serviço local.")


if mode == "Demonstração local":
    st.caption("Cenários sintéticos gerados para demonstração; não representam captura Wokwi nem medições físicas.")
    source = st.selectbox("Tipo de demonstração", ["Sensores IoT", "Previsão meteorológica"], key="fase7_demo_source")
    cases = ({"umidade_baixa": "Umidade baixa (<45%)", "umidade_alta": "Umidade alta (>80%)",
              "ph_fora_faixa": "pH simulado fora da faixa", "npk_ausente": "Indicador N/P/K ausente",
              "normal": "Sem limiar cruzado"} if source == "Sensores IoT" else
             {"chuva": "Chuva horária ≥1 mm", "umidade_baixa": "Umidade do ar baixa (<45%)",
              "umidade_alta": "Umidade do ar alta (>80%)", "normal": "Sem limiar cruzado"})
    if st.session_state.get("fase7_demo_case") not in cases:
        st.session_state.pop("fase7_demo_case", None)
    case = st.selectbox("Cenário", list(cases), format_func=cases.get, key="fase7_demo_case")
    submitted = st.button("Avaliar demonstração", type="primary")
    signature = fingerprint(mode, source, case)
    if submitted:
        new_result = evaluate(fase7.demo_iot if source == "Sensores IoT" else fase7.demo_weather, case)

elif mode == "CSV IoT da Fase 2":
    st.caption("O CSV registra a recepção no PC. DHT22 representa umidade do ar; pH e N/P/K são indicadores didáticos do protótipo.")
    source = st.radio("Entrada CSV", ["Histórico local da Fase 2", "Enviar CSV"], key="fase7_csv_source")
    content = None
    upload_ready = True
    if source == "Histórico local da Fase 2":
        st.caption("Leitura somente do histórico da Fase 2, sem alterar o arquivo original. Sua origem física ou simulada não é comprovada pelo CSV.")
    else:
        upload = st.file_uploader("Selecionar CSV IoT (até 1 MiB)", type=["csv"],
                                  max_upload_size=1, key="fase7_csv_upload")
        upload_ready = upload is not None
        if upload is not None:
            if getattr(upload, "size", 0) > 1024 * 1024:
                st.warning("O CSV deve ter no máximo 1 MiB.")
                upload_ready = False
            else:
                content = upload.getvalue()
                upload_ready = isinstance(content, bytes) and 0 < len(content) <= 1024 * 1024
                if not upload_ready:
                    st.warning("Envie um CSV não vazio de até 1 MiB.")
    origins = {"desconhecida": "Origem não comprovada", "wokwi": "Simulação Wokwi declarada",
               "esp32": "Captura ESP32 declarada, não verificada"}
    origin = st.selectbox("Origem declarada", list(origins), format_func=origins.get, key="fase7_origin")
    offset = st.selectbox("Fuso do PC de captura", ["Não informado", "-03:00", "UTC", "+00:00"], key="fase7_timezone")
    st.caption("Se o timestamp não tiver offset, informe o fuso usado na captura. O serviço não presume UTC.")
    historical = st.checkbox("Reprodução histórica (não representa uma medição atual)", value=True, key="fase7_history")
    st.caption("Sem reprodução histórica, a recepção deve ter no máximo cinco minutos. Isso não comprova uma nova aquisição válida do sensor.")
    left, right = st.columns(2)
    local = left.text_input("Local declarado (opcional)", key="fase7_local", max_chars=160)
    device = right.text_input("Dispositivo declarado (opcional)", key="fase7_device", max_chars=160)
    submitted = st.button("Avaliar CSV IoT", type="primary", disabled=not upload_ready)
    signature = fingerprint(mode, source, hashlib.sha256(content).hexdigest() if content is not None else None,
                            origin, offset, historical, local, device)
    if submitted and upload_ready:
        new_result = evaluate(fase7.evaluate_iot_csv, content, origem=origin,
                              fuso=None if offset == "Não informado" else offset,
                              historico=historical, local=local, dispositivo=device)

else:
    st.caption("Fonte externa complementar: previsão de umidade do ar e chuva, sem substituir os dados dos sensores da Fase 2.")
    navigation_link("pages/10_IoT_Meteorologia.py", label="Abrir IoT e meteorologia", icon="🌦️")
    city = st.text_input("Cidade para a previsão", value="Irecê", key="fase7_city", max_chars=120)
    submitted = st.button("Solicitar previsão e avaliar", type="primary")
    if submitted:
        forecast = evaluate(fase2.forecast, city)
        if not forecast.ok:
            forecast = Result(forecast.status, "Previsão indisponível. Confira a consulta meteorológica.")
        st.session_state["fase2_integration_result"] = forecast.as_dict()
        new_result = evaluate(fase7.evaluate_weather, forecast.as_dict()) if forecast.ok else forecast
    cached_value = st.session_state.get("fase2_integration_result")
    cached = cached_value if isinstance(cached_value, dict) else None
    if cached and cached.get("status") == "ok":
        cached_data = cached.get("data")
        location = cached_data.get("location") if isinstance(cached_data, dict) else None
        location = location if isinstance(location, dict) else {}
        st.caption(f"Previsão já consultada: {location.get('name', 'local não informado')}. Horários originais em UTC.")
    if st.button("Avaliar previsão já consultada", disabled=not cached or cached.get("status") != "ok"):
        new_result = evaluate(fase7.evaluate_weather, cached)
    signature = fingerprint(mode, city, cached)

# Seletores fora de formulários notificam o Streamlit imediatamente. Uma
# seleção antiga não recupera sua prévia ao ser escolhida novamente.
previous_signature = st.session_state.get("fase7_selection_signature")
if previous_signature is not None and previous_signature != signature:
    st.session_state.pop("fase7_preview_result", None)
    st.session_state["fase7_selection_changed"] = True
st.session_state["fase7_selection_signature"] = signature
if new_result is not None:
    st.session_state["fase7_preview_result"] = {"signature": signature, "result": new_result.as_dict()}
    st.session_state["fase7_selection_changed"] = False

stored = st.session_state.get("fase7_preview_result")
if stored is None:
    if st.session_state.get("fase7_selection_changed"):
        st.info("A seleção foi alterada. Avalie novamente para visualizar um resultado correspondente aos dados selecionados.")
    else:
        info_card("Selecione uma fonte e solicite a avaliação para visualizar a condição e a prévia da mensagem.")
    st.stop()
if stored["signature"] != signature:
    st.info("A seleção foi alterada. Avalie novamente para visualizar um resultado correspondente aos dados selecionados.")
    st.stop()

result = stored["result"]
if result.get("status") != "ok":
    st.warning(result.get("message", "Avaliação indisponível."))
    st.stop()
data, source = result.get("data", {}), result.get("source", {})
if data.get("preview_only") is not True or data.get("sns_enabled") is not False:
    st.error("A resposta não corresponde a uma avaliação exclusivamente local.")
    st.stop()

reading = data.get("reading", {})
if data.get("mode") == "recepcao_recente" and reading.get("ts_iso"):
    try:
        received = datetime.fromisoformat(reading["ts_iso"].replace("Z", "+00:00"))
        if (datetime.now(timezone.utc) - received).total_seconds() > 300:
            st.warning("O registro desta avaliação já ultrapassou cinco minutos. Avalie novamente com uma captura recente ou em reprodução histórica.")
            st.stop()
    except (ValueError, TypeError):
        st.warning("O horário da leitura não pôde ser confirmado. Avalie novamente.")
        st.stop()

st.divider()
st.subheader("Resultado da avaliação local")
st.caption(f"Avaliação local: {data.get('evaluated_at') or 'não informada'} · a avaliação não é atualizada automaticamente.")
if not reading:
    st.caption(f"Consulta à fonte: {data.get('forecast_retrieved_at') or 'indisponível (metadado não fornecido)'}")
    st.caption(f"Evento meteorológico previsto: {data.get('forecast_event_at') or 'não identificado (sem evento de alerta)'}")
origin_names = {"desconhecida": "Origem não comprovada", "wokwi": "Simulação Wokwi declarada",
                "esp32": "Captura ESP32 declarada, não verificada", "exemplo": "Exemplo sintético"}
origin_label = origin_names.get(source.get("origin"), source.get("provider", "não informada"))
st.write(f"Origem: {origin_label}")
if source.get("historical"):
    st.warning("Reprodução histórica: os registros mantêm suas datas originais e não representam medições atuais.")
if source.get("synthetic") or data.get("mode") == "demonstracao":
    st.info("Demonstração sintética: estes resultados não são medições físicas nem captura Wokwi.")

if reading:
    st.write(f"Recepção original no PC: {reading.get('_ts_original', reading.get('ts_iso', 'não informada'))}")
    st.write(f"Recepção em UTC: {reading.get('ts_iso', 'não informada')}")
    st.caption("O timestamp é de recebimento no computador; não certifica o instante ou a qualidade da medição.")
    columns = st.columns(4)
    columns[0].metric("Umidade DHT22 (%)", f"{reading['umidade']:.1f}")
    columns[1].metric("Temperatura (°C)", f"{reading['temp_c']:.1f}")
    columns[2].metric("pH simulado", f"{reading['ph_corr']:.3f}")
    columns[3].metric("Indicadores N/P/K", f"{reading['N']}/{reading['P']}/{reading['K']}")

alert = data.get("alert")
if alert is None:
    info_card("Nenhum limiar das regras foi cruzado nos dados avaliados. Não foi gerada uma mensagem de alerta.")
else:
    st.subheader("Alerta principal")
    st.warning(alert["alerta"])
    st.write("**Ação corretiva sugerida**")
    st.write(alert["acao"])
    conditions = data.get("conditions", [])
    secondary = [condition for condition in conditions if not condition.get("primary")]
    if secondary:
        st.subheader("Demais condições detectadas")
        st.table([{"Condição": condition["condicao"], "Valor": str(condition["valor"]),
                   "Critério didático": condition["limiar"]} for condition in secondary])
        st.caption("A prioridade das regras define um único alerta principal; as demais condições não geram mensagens adicionais.")
    st.subheader("Prévia da mensagem")
    with st.container(border=True):
        st.write("**Assunto**")
        st.text(data.get("subject", ""), width="stretch")
        st.write("**Conteúdo gerado na avaliação**")
        # Texto literal em parágrafos: preserva cada linha da mensagem sem
        # interpretar Markdown, HTML ou JavaScript vindos dos dados.
        for paragraph in data.get("body", "").split("\n\n"):
            st.text(paragraph, width="stretch")

st.caption("Prévia local. Nenhuma mensagem foi publicada e o estado de publicação do serviço permanece inalterado.")
