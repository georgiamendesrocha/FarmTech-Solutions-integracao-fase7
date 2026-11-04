"""Demo animada do Recomendador Inteligente de Cultura.

Gera dois artefactos para o README:

  - assets/readme/painel_ia_recomendador_demo.gif   (animação 6 cenas)
  - assets/readme/painel_ia_recomendador_hero.png   (frame final estático)

A animação simula o fluxo da página `painel_solucoes_ia.py` (aba Culturas):
entrada do solo + clima → 5 modelos treinados → ranking top-5 →
radar (perfil ideal vs. solo) → cultura recomendada com confiança.

Uso (raiz do repositório, venv activo):
  python scripts/export_readme_recomendador_demo.py
"""

from __future__ import annotations

import io
import warnings
from pathlib import Path

import matplotlib.patches as patches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "assets" / "readme"
AGRI = ROOT / "src" / "dados" / "Atividade_Cap10_produtos_agricolas.csv"

FEATURES = ["N", "P", "K", "temp_c", "umidade", "ph_corr", "chuva"]
FEATURES_LABELS = {
    "N": "N",
    "P": "P",
    "K": "K",
    "temp_c": "Temperatura",
    "umidade": "Umidade",
    "ph_corr": "pH",
    "chuva": "Chuva",
}
FEATURES_UNIT = {
    "N": "",
    "P": "",
    "K": "",
    "temp_c": "°C",
    "umidade": "%",
    "ph_corr": "",
    "chuva": "mm",
}
FEATURES_ICON = {
    "N": "🧪",
    "P": "🧪",
    "K": "🧪",
    "temp_c": "🌡",
    "umidade": "💧",
    "ph_corr": "⚗",
    "chuva": "🌧",
}

# Paleta visual (estilo painel "AI", fundo escuro, acento esmeralda + amarelo)
BG = "#0b1220"
PANEL = "#111827"
ACCENT = "#22c55e"
ACCENT_DARK = "#16a34a"
GOLD = "#facc15"
TEXT = "#f8fafc"
MUTED = "#94a3b8"
GRID = "#1f2937"

FIG_W, FIG_H = 12.0, 6.6  # polegadas
DPI = 100


# ---------------------------------------------------------------------------
# Pipeline de dados / modelo (espelho de painel_solucoes_ia._produtos_pkg)
# ---------------------------------------------------------------------------


def _carregar_e_treinar() -> tuple[pd.DataFrame, RandomForestClassifier, StandardScaler]:
    df = pd.read_csv(AGRI)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    rename = {
        "temperature": "temp_c",
        "humidity": "umidade",
        "ph": "ph_corr",
        "rainfall": "chuva",
        "n": "N",
        "p": "P",
        "k": "K",
        "nitrogen": "N",
        "phosphorous": "P",
        "potassium": "K",
        "crop": "label",
    }
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns and v not in df.columns})
    for c in FEATURES:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["label"] = df["label"].astype(str).str.strip()
    df = df.dropna(subset=FEATURES + ["label"]).reset_index(drop=True)

    X = df[FEATURES].to_numpy(float)
    y = df["label"].astype(str).to_numpy()
    scaler = StandardScaler().fit(X)
    Xs = scaler.transform(X)
    clf = RandomForestClassifier(n_estimators=200, random_state=42, max_depth=10)
    clf.fit(Xs, y)
    return df, clf, scaler


def _amostra_demo(df: pd.DataFrame) -> pd.Series:
    """Devolve um exemplo realista para a demo (linha real do dataset)."""
    if (df["label"] == "rice").any():
        return df[df["label"] == "rice"].iloc[3][FEATURES].astype(float)
    return df.iloc[0][FEATURES].astype(float)


# ---------------------------------------------------------------------------
# Renderização das frames
# ---------------------------------------------------------------------------


def _start_fig() -> tuple[plt.Figure, plt.Axes]:
    fig = plt.figure(figsize=(FIG_W, FIG_H), facecolor=BG)
    ax = fig.add_axes([0, 0, 1, 1], facecolor=BG)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_axis_off()
    # Header
    ax.text(0.04, 0.945, "FarmTech · Painel IA · soluções", fontsize=10, color=MUTED, alpha=0.9)
    ax.text(0.96, 0.945, "Recomendador Inteligente de Cultura", fontsize=10,
            color=GOLD, ha="right", weight="bold")
    ax.plot([0.04, 0.96], [0.92, 0.92], color=GRID, linewidth=0.8)
    return fig, ax


def _fig_to_image(fig: plt.Figure) -> Image.Image:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=DPI, facecolor=fig.get_facecolor())
    buf.seek(0)
    img = Image.open(buf).convert("RGB")
    plt.close(fig)
    return img


def _draw_card(ax, x, y, w, h, label, value, *, accent=ACCENT, big=False):
    rect = patches.FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.012,rounding_size=0.018",
        linewidth=1.2,
        edgecolor=accent,
        facecolor=PANEL,
        transform=ax.transAxes,
        alpha=0.95,
    )
    ax.add_patch(rect)
    ax.text(x + w / 2, y + h * 0.74, label, ha="center", va="center",
            fontsize=10, color=MUTED, transform=ax.transAxes)
    ax.text(x + w / 2, y + h * 0.36, value, ha="center", va="center",
            fontsize=22 if big else 18, color=TEXT, weight="bold", transform=ax.transAxes)


def frame_intro() -> Image.Image:
    fig, ax = _start_fig()
    ax.text(0.5, 0.62, "Recomendador Inteligente", ha="center", va="center",
            fontsize=34, color=TEXT, weight="bold", transform=ax.transAxes)
    ax.text(0.5, 0.52, "de Cultura", ha="center", va="center",
            fontsize=34, color=ACCENT, weight="bold", transform=ax.transAxes)
    ax.text(0.5, 0.40,
            "IoT (umidade · temperatura · pH)  +  Previsão (chuva 5 d)  +  Solo (N · P · K)",
            ha="center", va="center", fontsize=13, color=MUTED, transform=ax.transAxes)
    ax.text(0.5, 0.32,
            "→  5 modelos ML  →  Cultura ideal · radar · ajustes acionáveis",
            ha="center", va="center", fontsize=13, color=MUTED, transform=ax.transAxes)
    ax.text(0.5, 0.18, "FarmTech Solutions  ·  FIAP — Fase 3  ·  ML no agronegócio",
            ha="center", va="center", fontsize=10, color=MUTED, alpha=0.8, transform=ax.transAxes)
    return _fig_to_image(fig)


def frame_inputs(values: dict[str, float]) -> Image.Image:
    fig, ax = _start_fig()
    ax.text(0.04, 0.86, "1 · Entrada — perfil do solo + clima local",
            fontsize=16, color=TEXT, weight="bold", transform=ax.transAxes)
    ax.text(0.04, 0.815,
            "N, P, K vêm de análise do solo · temperatura/umidade/pH dos sensores IoT · chuva da previsão (5 d)",
            fontsize=10, color=MUTED, transform=ax.transAxes)

    # 7 cards, 4 colunas x 2 linhas (último vazio à direita)
    cols = 4
    pad_x = 0.04
    w = (1 - 2 * pad_x - 0.02 * (cols - 1)) / cols
    h = 0.20
    for i, k in enumerate(FEATURES):
        col = i % cols
        row = i // cols
        x = pad_x + col * (w + 0.02)
        y = 0.50 - row * 0.30
        v = values[k]
        unit = FEATURES_UNIT[k]
        text = f"{v:.1f}{unit}" if k != "ph_corr" else f"{v:.2f}"
        label = f"{FEATURES_ICON[k]}  {FEATURES_LABELS[k]}"
        _draw_card(ax, x, y, w, h, label, text, accent=ACCENT, big=True)

    # Banner inferior
    ax.text(0.5, 0.07, "→  enviando 7 features para os modelos…",
            ha="center", va="center", fontsize=12, color=GOLD,
            transform=ax.transAxes, alpha=0.95)
    return _fig_to_image(fig)


def frame_treino(progress: float, modelos_marcados: int) -> Image.Image:
    fig, ax = _start_fig()
    ax.text(0.04, 0.86, "2 · Treino & validação — 5 modelos ML",
            fontsize=16, color=TEXT, weight="bold", transform=ax.transAxes)
    ax.text(0.04, 0.815,
            "Pipeline: StandardScaler → train/test (75/25) → cross-val · seleção pelo melhor F1 ponderado",
            fontsize=10, color=MUTED, transform=ax.transAxes)

    nomes = ["Reg. Logística", "Random Forest", "Gradient Boosting", "k-NN", "Naive Bayes"]
    for i, nome in enumerate(nomes):
        y = 0.62 - i * 0.07
        ok = i < modelos_marcados
        bullet = "✓" if ok else "•"
        color = ACCENT if ok else MUTED
        ax.text(0.10, y, bullet, fontsize=18, color=color, transform=ax.transAxes,
                weight="bold", va="center")
        ax.text(0.14, y, nome, fontsize=14, color=TEXT if ok else MUTED,
                transform=ax.transAxes, va="center")
        if i == 1 and ok:
            ax.text(0.45, y, "← melhor modelo", fontsize=11, color=GOLD,
                    transform=ax.transAxes, weight="bold", va="center")

    # Barra de progresso
    bar_x, bar_y, bar_w, bar_h = 0.10, 0.18, 0.80, 0.04
    bg = patches.FancyBboxPatch((bar_x, bar_y), bar_w, bar_h,
                                boxstyle="round,pad=0,rounding_size=0.015",
                                linewidth=0, facecolor=GRID, transform=ax.transAxes)
    ax.add_patch(bg)
    fg = patches.FancyBboxPatch((bar_x, bar_y), bar_w * progress, bar_h,
                                boxstyle="round,pad=0,rounding_size=0.015",
                                linewidth=0, facecolor=ACCENT, transform=ax.transAxes)
    ax.add_patch(fg)
    ax.text(0.5, 0.10, f"{int(progress * 100)} %",
            ha="center", va="center", fontsize=14, color=GOLD,
            transform=ax.transAxes, weight="bold")
    return _fig_to_image(fig)


def _draw_top5_bars(ax, top5: pd.DataFrame, reveal: int):
    """Desenha barras horizontais reveladas progressivamente."""
    cols = ["#22c55e", "#16a34a", "#15803d", "#166534", "#14532d"]
    bar_h = 0.10
    gap = 0.02
    label_x = 0.04   # rótulo alinhado à esquerda
    bar_x = 0.18
    bar_w_max = 0.30
    base_y = 0.68    # bottom da 1.ª barra (a do topo)
    for i, (_, row) in enumerate(top5.iterrows()):
        y = base_y - i * (bar_h + gap)
        ax.text(label_x, y + bar_h / 2, row["Cultura"], fontsize=14,
                color=TEXT if i < reveal else MUTED, weight="bold",
                ha="left", va="center", transform=ax.transAxes)
        bg = patches.FancyBboxPatch((bar_x, y), bar_w_max, bar_h,
                                    boxstyle="round,pad=0,rounding_size=0.012",
                                    linewidth=0, facecolor=GRID, transform=ax.transAxes)
        ax.add_patch(bg)
        if i < reveal:
            w = bar_w_max * float(row["Probabilidade"])
            fg = patches.FancyBboxPatch((bar_x, y), max(w, 0.005), bar_h,
                                        boxstyle="round,pad=0,rounding_size=0.012",
                                        linewidth=0, facecolor=cols[i % len(cols)],
                                        transform=ax.transAxes)
            ax.add_patch(fg)
            ax.text(bar_x + bar_w_max + 0.012, y + bar_h / 2,
                    f"{row['Probabilidade']:.1%}", fontsize=12, color=GOLD,
                    weight="bold", ha="left", va="center", transform=ax.transAxes)


def _draw_radar(fig, top5: pd.DataFrame, perfil_ideal, perfil_atual, ax_pos):
    ax_r = fig.add_axes(ax_pos, projection="polar", facecolor=BG)
    norm = perfil_ideal.abs().clip(lower=1e-6) + perfil_atual.abs().clip(lower=1e-6)
    ideal = (perfil_ideal / norm).fillna(0).tolist()
    atual = (perfil_atual / norm).fillna(0).tolist()
    theta = np.linspace(0, 2 * np.pi, len(FEATURES), endpoint=False).tolist()
    theta_c = theta + [theta[0]]
    ideal += [ideal[0]]
    atual += [atual[0]]

    ax_r.plot(theta_c, ideal, color=ACCENT, linewidth=2.0, label="Ideal")
    ax_r.fill(theta_c, ideal, color=ACCENT, alpha=0.25)
    ax_r.plot(theta_c, atual, color=GOLD, linewidth=2.0, label="Solo agora")
    ax_r.fill(theta_c, atual, color=GOLD, alpha=0.20)
    ax_r.set_xticks(theta)
    ax_r.set_xticklabels([FEATURES_LABELS[f] for f in FEATURES], color=MUTED, fontsize=8)
    ax_r.set_yticks([])
    ax_r.tick_params(pad=0)
    ax_r.spines["polar"].set_color(GRID)
    ax_r.grid(color=GRID, alpha=0.5)
    ax_r.legend(loc="upper right", bbox_to_anchor=(1.18, 1.10), fontsize=8,
                facecolor=PANEL, edgecolor=GRID, labelcolor=TEXT, framealpha=0.95)


def frame_top5(top5: pd.DataFrame, reveal: int, *, with_radar: bool,
               perfil_ideal=None, perfil_atual=None, banner: bool = False) -> Image.Image:
    fig, ax = _start_fig()
    ax.text(0.04, 0.86, "3 · Top-5 culturas mais prováveis",
            fontsize=16, color=TEXT, weight="bold", transform=ax.transAxes)
    ax.text(0.04, 0.815,
            "Saída do melhor modelo (Random Forest) · probabilidade calibrada por validação cruzada",
            fontsize=10, color=MUTED, transform=ax.transAxes)

    _draw_top5_bars(ax, top5, reveal)

    if with_radar and perfil_ideal is not None:
        ax.text(0.75, 0.78, "Perfil ideal vs. solo agora",
                fontsize=12, color=TEXT, weight="bold",
                ha="center", transform=ax.transAxes)
        _draw_radar(fig, top5, perfil_ideal, perfil_atual, ax_pos=[0.58, 0.22, 0.36, 0.52])

    if banner:
        cult = top5.iloc[0]["Cultura"]
        prob = top5.iloc[0]["Probabilidade"]
        rect = patches.FancyBboxPatch(
            (0.06, 0.04), 0.88, 0.10,
            boxstyle="round,pad=0.014,rounding_size=0.025",
            linewidth=2, edgecolor=ACCENT, facecolor=PANEL,
            transform=ax.transAxes,
        )
        ax.add_patch(rect)
        ax.text(0.10, 0.09, "✨", fontsize=20, transform=ax.transAxes, va="center")
        ax.text(0.16, 0.105, "Cultura recomendada", fontsize=10, color=MUTED,
                transform=ax.transAxes, va="center")
        ax.text(0.16, 0.075, cult.upper(), fontsize=20, color=ACCENT, weight="bold",
                transform=ax.transAxes, va="center")
        ax.text(0.92, 0.105, "Confiança", fontsize=10, color=MUTED,
                ha="right", transform=ax.transAxes, va="center")
        ax.text(0.92, 0.075, f"{prob:.1%}", fontsize=20, color=GOLD, weight="bold",
                ha="right", transform=ax.transAxes, va="center")

    return _fig_to_image(fig)


# ---------------------------------------------------------------------------
# Pipeline principal
# ---------------------------------------------------------------------------


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[INFO] CSV: {AGRI}")
    df, clf, scaler = _carregar_e_treinar()
    print(f"[INFO] Linhas: {len(df)} · classes: {df['label'].nunique()}")

    sample = _amostra_demo(df)
    Xs = scaler.transform(sample.values.reshape(1, -1))
    probs = clf.predict_proba(Xs)[0]
    classes = list(clf.classes_)
    rank = (
        pd.DataFrame({"Cultura": classes, "Probabilidade": probs})
        .sort_values("Probabilidade", ascending=False)
        .reset_index(drop=True)
    )
    top5 = rank.head(5).reset_index(drop=True)
    cult_top = top5.iloc[0]["Cultura"]
    perfil_ideal = df[df["label"] == cult_top][FEATURES].mean()
    perfil_atual = sample.copy()

    inputs = {f: float(sample[f]) for f in FEATURES}

    # ---------------- Construção de frames ----------------
    frames: list[Image.Image] = []

    # Cena 1 — intro (1.4 s)
    intro = frame_intro()
    for _ in range(7):
        frames.append(intro)

    # Cena 2 — entradas (1.6 s)
    inp = frame_inputs(inputs)
    for _ in range(8):
        frames.append(inp)

    # Cena 3 — treino progressivo (1.5 s)
    progress_steps = [
        (0.20, 1),
        (0.40, 2),
        (0.60, 3),
        (0.80, 4),
        (1.00, 5),
    ]
    for p, m in progress_steps:
        for _ in range(2):
            frames.append(frame_treino(p, m))

    # Cena 4 — top5 revelado (5 etapas, 0.3 s cada)
    for n in range(1, 6):
        frames.append(frame_top5(top5, n, with_radar=False))
        frames.append(frame_top5(top5, n, with_radar=False))

    # Cena 5 — top5 + radar aparece (1.4 s)
    radar_view = frame_top5(top5, 5, with_radar=True,
                            perfil_ideal=perfil_ideal, perfil_atual=perfil_atual)
    for _ in range(7):
        frames.append(radar_view)

    # Cena 6 — banner final (2 s)
    final_view = frame_top5(top5, 5, with_radar=True,
                            perfil_ideal=perfil_ideal, perfil_atual=perfil_atual,
                            banner=True)
    for _ in range(10):
        frames.append(final_view)

    # ---------------- GIF ----------------
    gif_path = OUT_DIR / "painel_ia_recomendador_demo.gif"
    pal_frames = [f.convert("P", palette=Image.ADAPTIVE, colors=128) for f in frames]
    pal_frames[0].save(
        gif_path,
        save_all=True,
        append_images=pal_frames[1:],
        duration=200,
        loop=0,
        optimize=True,
        disposal=2,
    )
    print(f"[OK] {gif_path}  ({gif_path.stat().st_size / 1024:.1f} KB · {len(frames)} frames)")

    # ---------------- Hero PNG ----------------
    hero_path = OUT_DIR / "painel_ia_recomendador_hero.png"
    final_view.save(hero_path, "PNG", optimize=True)
    print(f"[OK] {hero_path}  ({hero_path.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
