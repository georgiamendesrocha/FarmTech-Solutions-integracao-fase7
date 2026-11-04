from pathlib import Path
import sqlite3

import pandas as pd
import streamlit as st

from api import get_db_path, init_db


st.set_page_config(
    page_title="FarmTech Solutions - Ir Além",
    layout="wide",
)


def load_data() -> pd.DataFrame:
    init_db()
    db_path = get_db_path()
    if not db_path.exists():
        return pd.DataFrame(
            columns=["id", "timestamp", "device_id", "temperature", "humidity", "light"]
        )

    with sqlite3.connect(db_path) as conn:
        return pd.read_sql_query(
            """
            SELECT id, timestamp, device_id, temperature, humidity, light
            FROM leituras
            ORDER BY id ASC
            """,
            conn,
        )


def format_number(value, suffix: str) -> str:
    if pd.isna(value):
        return "sem dado"
    return f"{float(value):.1f}{suffix}"


def format_timestamp(value) -> str:
    timestamp = pd.to_datetime(value, errors="coerce")
    if pd.isna(timestamp):
        return "sem dado" if pd.isna(value) else str(value)
    return timestamp.strftime("%d/%m/%Y %H:%M:%S")


st.title("FarmTech Solutions - Ir Além")
st.subheader("Dashboard IoT com dados recebidos via API e armazenados em SQLite")

col_button, col_db = st.columns([1, 3])
with col_button:
    if st.button("Atualizar dados"):
        st.rerun()
with col_db:
    st.caption(f"Banco consultado: `{Path(get_db_path()).name}`")

df = load_data()

if df.empty:
    st.info("Nenhuma leitura registrada no SQLite. Inicie `python api.py` e envie dados para `POST /telemetria`.")
    st.stop()

latest = df.iloc[-1]
device_id = latest["device_id"] if pd.notna(latest["device_id"]) and latest["device_id"] else "não informado"

metric_cols = st.columns(5)
metric_cols[0].metric("Temperatura", format_number(latest["temperature"], " °C"))
metric_cols[1].metric("Umidade", format_number(latest["humidity"], " %"))
metric_cols[2].metric("Luminosidade", format_number(latest["light"], " %"))
metric_cols[3].metric("Dispositivo", str(device_id))
metric_cols[4].metric("Última leitura", format_timestamp(latest["timestamp"]))

if pd.to_numeric(df["light"], errors="coerce").gt(100).any():
    st.warning(
        "Existem registros históricos com luminosidade acima de 100. "
        "Eles não foram convertidos; novas leituras usam escala normalizada de 0 a 100%."
    )

st.markdown("---")
st.subheader("Histórico")

chart_df = df.copy()
chart_df["timestamp_plot"] = pd.to_datetime(chart_df["timestamp"], errors="coerce")
chart_df = chart_df.dropna(subset=["timestamp_plot"]).sort_values("timestamp_plot")
chart_df["timestamp_label"] = chart_df["timestamp_plot"].dt.strftime("%d/%m %H:%M:%S")
chart_df = chart_df.set_index("timestamp_label")

col_left, col_right = st.columns(2)
with col_left:
    st.line_chart(chart_df[["temperature", "humidity"]])
with col_right:
    light_chart_df = chart_df.copy()
    light_chart_df["light"] = pd.to_numeric(light_chart_df["light"], errors="coerce")
    light_chart_df = light_chart_df[light_chart_df["light"].between(0, 100)]
    st.caption("Somente leituras na escala normalizada de 0 a 100% são exibidas neste gráfico.")
    st.line_chart(light_chart_df[["light"]])

st.subheader("Tabela de dados")
st.dataframe(df.sort_values("id", ascending=False), use_container_width=True)
