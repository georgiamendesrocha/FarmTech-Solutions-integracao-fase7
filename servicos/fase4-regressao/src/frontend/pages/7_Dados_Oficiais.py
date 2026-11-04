"""Dados reais oficiais de sensores de solo e estatísticas agrícolas."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

import pandas as pd
import plotly.express as px
import streamlit as st
from src.frontend.feedback import erro_publico
from src.ml.artifact_security import carregar_json
from farmtech_integracao.ui import info_card

from src.data_sources import (
    NOAA_CSV,
    NOAA_METADATA,
    SIDRA_METADATA,
    SIDRA_MUNICIPAL_CSV,
    INMET_CSV,
    INMET_METADATA,
    carregar_inmet,
    carregar_noaa,
    carregar_sidra,
    preparar_historico_sidra,
    preparar_serie_inmet_diaria,
    preparar_serie_noaa_diaria,
    carregar_conjunto_meteorologico,
    carregar_conjunto_sidra,
)
from src.ml.productivity import (
    METRICS_FILENAME as PRODUCTIVITY_METRICS_FILENAME,
    MODELS_DIR,
    carregar_previsoes_produtividade,
)

st.set_page_config(page_title="Dados Oficiais — FarmTech", layout="wide")

st.title("Observações reais e estatísticas oficiais")
st.caption(
    "Fontes oficiais carregadas de cópias locais. Esta página não combina dados "
    "de estações externas, sensores simulados ou estimativas de ML."
)

tab_soil, tab_productivity = st.tabs(
    ["Sensores de solo e meteorologia observada", "Produtividade — IBGE/SIDRA"]
)

with tab_soil:
    st.markdown("### Medições reais in situ")
    try:
        soil, noaa_metadata = carregar_conjunto_meteorologico("NOAA")
    except (OSError, ValueError, json.JSONDecodeError) as error:
        erro_publico("Cópia NOAA indisponível ou inválida. Confira os arquivos e metadados; preserve a cópia atual antes de atualizar pela fonte oficial.", error, aviso=True)
    else:
        st.success(
            "Observações instrumentais reais da rede USCRN; não são dados do "
            "protótipo FarmTech nem previsões de Machine Learning."
        )
        source_col1, source_col2, source_col3, source_col4 = st.columns(4)
        source_col1.metric("Estação", noaa_metadata["estacao"])
        source_col2.metric("Observações válidas", f"{noaa_metadata['observacoes']:,}")
        source_col3.metric("Latitude", f"{noaa_metadata['latitude']:.3f}°")
        source_col4.metric("Longitude", f"{noaa_metadata['longitude']:.3f}°")
        st.caption(
            f"Fonte: NOAA/NCEI USCRN — [arquivo oficial]({noaa_metadata['url']}) | "
            f"Período UTC: {noaa_metadata['inicio_utc']} a {noaa_metadata['fim_utc']} | "
            "frequência horária; dados armazenados localmente."
        )

        depth_labels = {
            "5 cm": "soil_moisture_5cm_m3_m3",
            "10 cm": "soil_moisture_10cm_m3_m3",
            "20 cm": "soil_moisture_20cm_m3_m3",
            "50 cm": "soil_moisture_50cm_m3_m3",
            "100 cm": "soil_moisture_100cm_m3_m3",
        }
        selected_depth = st.selectbox("Profundidade do sensor de solo", list(depth_labels))
        daily_soil = preparar_serie_noaa_diaria(
            soil, depth_labels[selected_depth]
        )
        fig_soil = px.line(
            daily_soil,
            x="dia_utc",
            y="umidade_media_m3_m3",
            title=f"Umidade volumétrica média diária — profundidade {selected_depth}",
            labels={
                "dia_utc": "Dia (UTC)",
                "umidade_media_m3_m3": "Umidade volumétrica (m³/m³)",
            },
        )
        st.plotly_chart(fig_soil, use_container_width=True)
        st.caption(
            "Cada ponto é a média das observações horárias válidas daquele dia; "
            "dias sem dados não são imputados."
        )

        weather_variables = {
            "Temperatura média do ar (°C)": "air_temperature_c",
            "Umidade relativa do ar (%)": "relative_humidity_pct",
            "Precipitação (mm/h)": "precipitation_mm",
        }
        selected_weather_label = st.selectbox(
            "Variável meteorológica observada na mesma estação",
            list(weather_variables),
        )
        weather_variable = weather_variables[selected_weather_label]
        weather = soil[["timestamp_utc", weather_variable]].dropna().copy()
        weather["dia_utc"] = weather["timestamp_utc"].dt.floor("D")
        aggregation = "sum" if weather_variable == "precipitation_mm" else "mean"
        weather_daily = (
            weather.groupby("dia_utc", as_index=False)
            .agg(valor=(weather_variable, aggregation))
            .sort_values("dia_utc")
        )
        weather_title = (
            "Precipitação acumulada por dia"
            if aggregation == "sum"
            else f"{weather_variable.replace('_', ' ').title()} — média diária"
        )
        fig_weather = px.line(
            weather_daily,
            x="dia_utc",
            y="valor",
            title=weather_title,
            labels={"dia_utc": "Dia (UTC)", "valor": weather_variable},
        )
        st.plotly_chart(fig_weather, use_container_width=True)

        with st.expander("Amostra de observações e proveniência"):
            st.dataframe(
                soil.tail(50).sort_values("timestamp_utc", ascending=False),
                use_container_width=True,
                hide_index=True,
            )
            st.json(
                {
                    "hash_sha256_arquivo_fonte": noaa_metadata["arquivo_fonte_sha256"],
                    "hash_sha256_copia_local": noaa_metadata[
                        "arquivo_normalizado_sha256"
                    ],
                    "unidades": noaa_metadata["unidades"],
                    "tratamento": noaa_metadata["tratamento"],
                    "limitações": noaa_metadata["limitacoes"],
                }
            )
        info_card(
            "A estação fica nos Estados Unidos. As observações são mostradas "
            "separadamente das leituras ESP32/Wokwi simuladas: umidade do solo "
            "volumétrica (m³/m³) e umidade do protótipo (%) têm escala e contexto "
            "diferentes, portanto não são comparadas diretamente."
        )

    st.markdown("---")
    st.markdown("### Complemento meteorológico observado — INMET")
    try:
        inmet, inmet_metadata = carregar_conjunto_meteorologico("INMET")
    except (OSError, ValueError, json.JSONDecodeError) as error:
        erro_publico("Cópia INMET indisponível ou inválida. Confira os arquivos e metadados; preserve a cópia atual antes de atualizar pela fonte oficial.", error, aviso=True)
    else:
        st.success(
            "Observações meteorológicas reais do INMET. Não são medições de "
            "umidade do solo nem substituem sensores de campo."
        )
        inmet_col1, inmet_col2, inmet_col3 = st.columns(3)
        inmet_col1.metric("Estação", inmet_metadata["station"])
        inmet_col2.metric("Observações", f"{inmet_metadata['observacoes']:,}")
        inmet_col3.metric(
            "Localização",
            f"{inmet_metadata['latitude']:.3f}°, {inmet_metadata['longitude']:.3f}°",
        )
        st.caption(
            f"Fonte: INMET — [arquivo oficial]({inmet_metadata['url']}) | "
            f"Estação {inmet_metadata['station_code']} ({inmet_metadata['uf']}) | "
            f"{inmet_metadata['inicio_utc']} a {inmet_metadata['fim_utc']} UTC."
        )
        inmet_variables = {
            "Temperatura do ar (°C)": "air_temperature_c",
            "Precipitação acumulada (mm/dia)": "precipitation_mm",
            "Umidade relativa do ar (%)": "relative_humidity_pct",
        }
        selected_inmet_variable = st.selectbox(
            "Variável histórica INMET", inmet_variables
        )
        inmet_daily = preparar_serie_inmet_diaria(
            inmet, inmet_variables[selected_inmet_variable]
        )
        fig_inmet = px.line(
            inmet_daily,
            x="dia_utc",
            y="valor",
            title=f"{selected_inmet_variable} — agregado diário observado",
            labels={"dia_utc": "Dia (UTC)", "valor": selected_inmet_variable},
        )
        st.plotly_chart(fig_inmet, use_container_width=True)
        with st.expander("Amostra e tratamento INMET"):
            st.dataframe(
                inmet.tail(50).sort_values("timestamp_utc", ascending=False),
                use_container_width=True,
                hide_index=True,
            )
            st.json(
                {
                    "hash_sha256_arquivo_fonte": inmet_metadata["arquivo_estacao_sha256"],
                    "hash_sha256_copia_local": inmet_metadata[
                        "arquivo_normalizado_sha256"
                    ],
                    "unidades": inmet_metadata["unidades"],
                    "tratamento": inmet_metadata["tratamento"],
                    "limitações": inmet_metadata["limitacoes"],
                }
            )
        info_card(
            "As séries NOAA, INMET e IoT são de locais e contextos diferentes; "
            "o dashboard as mantém separadas e não calcula correlações entre elas."
        )

with tab_productivity:
    st.markdown("### Séries oficiais de rendimento médio")
    try:
        national, municipal, sidra_metadata = carregar_conjunto_sidra()
    except (OSError, ValueError, json.JSONDecodeError) as error:
        erro_publico("Cópia SIDRA indisponível ou inválida. Confira CSVs e metadados; preserve os arquivos atuais antes de atualizar pela fonte oficial.", error, aviso=True)
    else:
        st.success(
            "Estatísticas agrícolas oficiais do IBGE; não são leituras de sensores "
            "nem medições da propriedade FarmTech."
        )
        st.caption(
            f"IBGE/SIDRA, tabela 1612, variável 112 (rendimento médio da produção), "
            f"unidade kg/ha. Série nacional: {sidra_metadata['periodo_nacional']}; "
            f"recorte municipal: {sidra_metadata['periodo_municipal']}."
        )

        crops = (
            national[["codigo_cultura", "cultura"]]
            .drop_duplicates()
            .sort_values("cultura")
        )
        selected_crop = st.selectbox(
            "Cultura",
            crops["codigo_cultura"].tolist(),
            format_func=lambda code: crops.loc[
                crops["codigo_cultura"] == code, "cultura"
            ].iloc[0],
        )
        crop_history = preparar_historico_sidra(national, selected_crop)
        fig_history = px.line(
            crop_history,
            x="ano",
            y="rendimento_kg_ha",
            markers=True,
            title="Rendimento médio nacional observado — série histórica",
            labels={"ano": "Ano", "rendimento_kg_ha": "Rendimento médio (kg/ha)"},
        )
        st.plotly_chart(fig_history, use_container_width=True)

        crop_municipal = municipal.loc[
            (municipal["codigo_cultura"].astype(str) == str(selected_crop))
            & municipal["rendimento_kg_ha"].notna()
        ].copy()
        crop_municipal["rendimento_kg_ha"] = pd.to_numeric(
            crop_municipal["rendimento_kg_ha"], errors="coerce"
        )
        if not crop_municipal.empty:
            top_municipal = crop_municipal.nlargest(20, "rendimento_kg_ha")
            fig_municipal = px.bar(
                top_municipal.sort_values("rendimento_kg_ha"),
                x="rendimento_kg_ha",
                y="geografia",
                orientation="h",
                title=(
                    "20 maiores rendimentos municipais publicados no recorte "
                    f"{sidra_metadata['periodo_municipal']}"
                ),
                labels={
                    "rendimento_kg_ha": "Rendimento médio (kg/ha)",
                    "geografia": "Município/UF",
                },
            )
            st.plotly_chart(fig_municipal, use_container_width=True)
            st.dataframe(
                crop_municipal[
                    ["codigo_geografico", "municipio", "uf", "cultura", "ano", "rendimento_kg_ha", "unidade"]
                ].sort_values("municipio"),
                use_container_width=True,
                hide_index=True,
            )

        try:
            productivity_metrics_path = MODELS_DIR / PRODUCTIVITY_METRICS_FILENAME
            if productivity_metrics_path.is_file():
                productivity_metrics = carregar_json(productivity_metrics_path)
                st.markdown("#### Avaliação temporal e baseline")
                st.caption(productivity_metrics["validacao"])
                st.write(productivity_metrics["status"])
                report_rows = []
                for crop_code, crop_result in productivity_metrics["culturas"].items():
                    test = crop_result["teste_temporal"]["metodo_selecionado"]
                    baseline = crop_result["teste_temporal"]["persistencia_ultimo_ano"]
                    report_rows.append(
                        {
                            "Cultura": crop_result["cultura"],
                            "Método (seleção na validação)": crop_result["metodo_selecionado"],
                            "MAE teste (kg/ha)": test["mae"],
                            "RMSE teste (kg/ha)": test["rmse"],
                            "R² teste": test["r2"],
                            "MAE baseline (kg/ha)": baseline["mae"],
                            "R² baseline": baseline["r2"],
                            "Previsão disponibilizada": crop_result["previsao_disponivel"],
                        }
                    )
                st.dataframe(
                    pd.DataFrame(report_rows).round(3),
                    use_container_width=True,
                    hide_index=True,
                )
                forecasts = carregar_previsoes_produtividade()
                if forecasts is None or forecasts.empty:
                    st.warning(
                        "Previsão de rendimento não disponibilizada: o teste temporal "
                        "reservado não demonstrou habilidade positiva suficiente. "
                        "Somente a análise histórica oficial é exibida."
                    )
                else:
                    st.markdown("#### Estimativas experimentais de rendimento")
                    st.dataframe(forecasts, use_container_width=True, hide_index=True)

        except Exception as error:
            erro_publico("Diagnóstico de produtividade indisponível ou inválido. Somente o histórico oficial pode ser consultado; nenhuma previsão confiável foi publicada.", error, aviso=True)

        st.info(
            "Os rendimentos municipais são agregados oficiais por município e cultura; "
            "não representam rendimento de uma fazenda específica. Nenhuma linha é "
            "mesclada com as observações NOAA ou com a simulação IoT."
        )
