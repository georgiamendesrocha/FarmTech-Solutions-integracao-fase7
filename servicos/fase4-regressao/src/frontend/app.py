"""Entrada da dashboard FarmTech Solutions — integração FIAP Fase 7.

A navegação e a identidade institucional são compartilhadas entre todas as páginas.
As rotinas da dashboard original são preservadas na página inicial.
"""

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parents[1]))

from farmtech_integracao.demo import configure_dashboard
configure_dashboard()

import streamlit as st
from src.frontend.assets import carregar_logo
from farmtech_integracao.ui import apply_theme, info_card

try:
    logo = carregar_logo()
except (OSError, ValueError):
    logo = None

st.set_page_config(
    page_title="FarmTech Solutions",
    page_icon=logo if logo is not None else "🌱",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_theme()

# A marca institucional fica acessível durante toda a navegação.
if logo is not None:
    st.logo(logo, size="large")

with st.sidebar:
    st.markdown("# FarmTech Solutions")
    st.caption("Assistente Agrícola Inteligente · FIAP")
    st.divider()

# Cabeçalho compartilhado: não depende de qual página está sendo executada.
st.markdown(
    '<div style="background:#40534E;border-left:4px solid #71BE9C;'
    'padding:0.8rem 1rem;border-radius:10px;margin-bottom:1.1rem">'
    '<div style="font-weight:800;font-size:2.4rem;color:#E3E9E7">'
    'FarmTech Solutions</div>'
    '<div style="color:#CBD5D3;font-size:0.84rem">'
    'Plataforma Integrada de Inteligência Agrícola </div>'
    '</div>',
    unsafe_allow_html=True,
)


def render_home():
    # A sessão referencia o produtor único do processo.
    if "scheduler_holder" not in st.session_state:
        st.session_state["scheduler_holder"] = {}

    estado_atual_simulacao = "indisponivel"
    try:
        from src.frontend.scheduler import estado_simulacao, iniciar_scheduler
        from src.db.database import validar_banco
        if estado_simulacao(st.session_state["scheduler_holder"]) != "desativada":
            validar_banco()
        iniciar_scheduler(st.session_state["scheduler_holder"])
        estado_atual_simulacao = estado_simulacao(st.session_state["scheduler_holder"])
    except Exception as e:
        st.session_state["scheduler_holder"]["erro"] = "Simulação indisponível. Confira o banco e a configuração."

    # ── Página inicial ────────────────────────────────────────────────────────────────────
    st.title("Visão geral")
    st.subheader("Assistente Agrícola Inteligente")
    st.caption("GESTÃO · IoT · DADOS · VISÃO COMPUTACIONAL")
    with st.container(border=True):
        st.markdown("### Explore os serviços da FarmTech")
        st.write("Acesse as Fases 1, 2, 3 e 6 pela navegação. As sete páginas analíticas da Fase 4 continuam disponíveis.")
        st.page_link("pages/8_Servicos_Integrados.py", label="Abrir visão geral dos serviços", icon="🌱")
    if os.getenv("FARMTECH_INTEGRACAO") == "1":
        info_card("Modo integrado local · simulação desativada · ações dos serviços executadas somente quando solicitadas.")
        from farmtech_integracao.demo import demo_path
        if Path(os.getenv("DB_PATH", "")).resolve() == demo_path().resolve():
            st.caption("Base reconstruída de demonstração a partir dos CSVs acadêmicos/registrados/simulados; não é histórico real recuperado.")
            if not demo_path().is_file():
                st.warning("A base de demonstração ainda não foi preparada. Execute explicitamente: python iniciar.py --preparar-demo")

    if estado_atual_simulacao == "ativa":
        st.success("Simulação ativa — scheduler em execução, registrando leituras simuladas.")
    elif estado_atual_simulacao == "pausada":
        info_card("Simulação pausada — novos ciclos de leituras simuladas estão suspensos.")
    elif estado_atual_simulacao == "desativada":
        info_card("Simulação desativada por configuração.")
    elif estado_atual_simulacao == "indisponivel":
        st.warning("Simulação indisponível. Confira o banco e a configuração.")
    else:
        info_card("Simulação parada — scheduler não está em execução.")

    st.markdown(
        """
        Plataforma de monitoramento e análise para o agronegócio, integrando leituras
        registradas/simuladas do protótipo ESP32/Wokwi, armazenadas em SQLite, com
        Machine Learning supervisionado para previsões agrícolas e apoio a decisão
        no manejo de culturas.
        """
    )

    col1, col2 = st.columns([3, 2])


    with col1:
        st.markdown("#### Arquitetura integrada")
        st.caption("FarmTech Solutions — serviços das fases anteriores integrados à dashboard da Fase 4.")

        with st.container(border=True):
            st.markdown("**Fase 4 — Núcleo da plataforma**")
            st.write("Dashboard Streamlit, banco SQLite, modelos de Machine Learning e dados oficiais.")

        esquerda, direita = st.columns(2)

        with esquerda:
            with st.container(border=True):
                st.markdown("**Fase 1 — Gestão agrícola**")
                st.caption("Talhões, áreas, insumos e custos.")

            with st.container(border=True):
                st.markdown("**Fase 3 — Dados**")
                st.caption("Consultas Oracle e arquivos CSV.")

        with direita:
            with st.container(border=True):
                st.markdown("**Fase 2 — IoT**")
                st.caption("Sensores, meteorologia e simulações.")

            with st.container(border=True):
                st.markdown("**Fase 6 — Visão computacional**")
                st.caption("Modelo YOLO para banana e milho.")

        st.page_link(
            "pages/8_Servicos_Integrados.py",
            label="Acessar serviços integrados",
        )



    with col2:
        st.markdown("#### Status do Banco de Dados")
        try:
            from src.db.database import status_banco

            status = status_banco()
            for inicio in range(0, len(status), 2):
                itens = list(status.items())[inicio:inicio + 2]
                colunas = st.columns(len(itens))
                for coluna, (tabela, total) in zip(colunas, itens):
                    with coluna:
                        st.metric(
                            f"{tabela.replace('_', ' ').capitalize()} (registros)",
                            f"{total:,}".replace(",", "."),
                        )

        except Exception as e:
            from src.frontend.feedback import erro_publico
            erro_publico("Banco indisponível ou inválido. Confira a configuração e execute a ingestão dos CSVs após preservar os dados existentes.", e, aviso=True)

    st.markdown("---")
    st.markdown("#### Páginas disponíveis")

    cols = st.columns(3)
    paginas = [
        ("Sensores IoT", "Leituras registradas/simuladas do prototipo ESP32/Wokwi e estado da simulação."),
        ("Analise Exploratoria", "Heatmaps, distribuicoes por cultura, boxplots e scatter entre variaveis."),
        ("Pipeline ML", "Comparacao de modelos, metricas, residuos e feature importance."),
        ("Previsao Agricola", "Previsoes originais de chuva e umidade e estimativa experimental de pH."),
        ("Recomendacoes de Manejo", "Indicativos de manejo cruzando previsao ML com leituras registradas/simuladas do prototipo ESP32/Wokwi."),
        ("Historico de Previsoes", "Consulta ao historico de todas as previsoes realizadas."),
        ("Dados Oficiais", "Observacoes de solo NOAA/USCRN, meteorologia INMET e historico de produtividade IBGE/SIDRA."),
    ]
    for i, (titulo, descricao) in enumerate(paginas):
        with cols[i % 3]:
            info_card(descricao, title=titulo)

    st.markdown("---")
    st.caption(
        "FIAP — Fase 7 | Equipe atual: Marina Soares, Carlos Amaral, Georgia Rocha, Edemir Sufiatti | "
        "Tutor: Nicolly Candida | Coordenador: Andre Godoi Chiovato"
    )


PAGES_DIR = Path(__file__).resolve().parent / "pages"
F4_LABELS = {
    1: "Sensores IoT",
    2: "Análise Exploratória",
    3: "Pipeline ML",
    4: "Previsão Agrícola",
    5: "Recomendações de Manejo",
    6: "Histórico de Previsões",
    7: "Dados Oficiais",
}
F4_ICONS = {1: "sensors", 2: "monitoring", 3: "model_training", 4: "query_stats", 5: "eco", 6: "history", 7: "public"}
F7_ICONS = {
    "servico": "hub", "gest": "agriculture", "iot": "device_hub",
    "oracle": "database", "visao": "image_search",
}


def numbered_page(file_path: Path):
    """Cria item de menu para arquivo da pasta pages, sem alterar seu conteúdo."""
    match = re.match(r"^(\d+)_", file_path.stem)
    number = int(match.group(1)) if match else 0
    default_title = re.sub(r"^\d+_", "", file_path.stem).replace("_", " ")
    if 1 <= number <= 7:
        title = F4_LABELS.get(number, default_title)
        icon = F4_ICONS.get(number, "dashboard")
    else:
        name = file_path.stem.lower()
        if "servic" in name:
            title, icon = "Visão Geral dos Serviços", F7_ICONS["servico"]
        elif "gest" in name:
            title, icon = "Gestão Agrícola", F7_ICONS["gest"]
        elif "oracle" in name:
            title, icon = "Consultas e Oracle", F7_ICONS["oracle"]
        elif "visao" in name or "yolo" in name:
            title, icon = "Visão Computacional", F7_ICONS["visao"]
        elif "iot" in name:
            title, icon = "IoT e Meteorologia", F7_ICONS["iot"]
        else:
            title, icon = default_title, "extension"
    return number, st.Page(file_path, title=title, icon=f":material/{icon}:")


pages = sorted((p for p in PAGES_DIR.glob("*.py") if not p.name.startswith("_")), key=lambda p: p.name)
registered = [numbered_page(p) for p in pages]
analysis_pages = [page for number, page in registered if 1 <= number <= 7]
integration_pages = [page for number, page in registered if number > 7 or number == 0]

navigation = {"Plataforma": [st.Page(render_home, title="Visão Geral", icon=":material/dashboard:", default=True)]}
if analysis_pages:
    navigation["Análises e dados · Fase 4"] = analysis_pages
if integration_pages:
    navigation["Serviços integrados"] = integration_pages

selected_page = st.navigation(navigation, position="sidebar", expanded=True)
selected_page.run()
