"""
Gera bytes de PDF a partir de `src/docs/relatorio.md`.

Formatação alinhada às exigências usuais da **ABNT NBR 14724** para trabalhos
académicos em suporte digital (margens, corpo 12 pt, entrelinhas 1,5, parágrafo
justificado com recuo de 1º linha 1,25 cm, fonte Times New Roman ou Arial).

Inclui o **logo FIAP** (`assets/logo-fiap.png`) no topo da primeira página, quando
o ficheiro existir.
"""

from __future__ import annotations

import os
import re
import sys
from io import BytesIO
from pathlib import Path
from urllib.parse import unquote

from fpdf import FPDF

# --- ABNT NBR 14724 (texto — práticas correntes em suporte digital) ---
MARGIN_LEFT_MM = 30.0   # 3 cm (lombada)
MARGIN_TOP_MM = 20.0
MARGIN_RIGHT_MM = 20.0
MARGIN_BOTTOM_MM = 20.0
BODY_FONT_PT = 12
LINE_SPACING = 1.5
# Altura de linha em mm: corpo 12 pt × 1,5 (1 pt ≈ 0,3528 mm)
LINE_HEIGHT_MM = BODY_FONT_PT * (25.4 / 72.0) * LINE_SPACING
FIRST_LINE_INDENT_MM = 12.5  # 1,25 cm — recuo da primeira linha do parágrafo
LOGO_MAX_WIDTH_MM = 52.0

_RE_IMG = re.compile(r"^\s*!\[([^\]]*)\]\(([^)]+)\)\s*$")
_RE_OL = re.compile(r"^\s*(\d+)\.\s+(.*)$")


def _font_files() -> tuple[Path, Path | None]:
    """
    Preferência ABNT: **Times New Roman**; senão Arial; senão DejaVu em fpdf2.
    """
    import fpdf

    if sys.platform == "win32":
        fdir = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
        # Times New Roman (comum em normas ABNT)
        for reg, bd in (
            (fdir / "times.ttf", fdir / "timesbd.ttf"),
            (fdir / "arial.ttf", fdir / "arialbd.ttf"),
        ):
            if reg.is_file():
                return reg, bd if bd.is_file() else None

    tnr = Path("/usr/share/fonts/truetype/msttcorefonts/Times_New_Roman.ttf")
    tnrb = Path("/usr/share/fonts/truetype/msttcorefonts/Times_New_Roman_Bold.ttf")
    if tnr.is_file():
        return tnr, tnrb if tnrb.is_file() else None

    dj = Path("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf")
    djb = Path("/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf")
    if dj.is_file():
        return dj, djb if djb.is_file() else None

    mac_t = Path("/Library/Fonts/Times New Roman.ttf")
    mac_tb = Path("/Library/Fonts/Times New Roman Bold.ttf")
    if mac_t.is_file():
        return mac_t, mac_tb if mac_tb.is_file() else None

    root = Path(fpdf.__file__).resolve().parent
    for name in ("DejaVuSans.ttf",):
        found = next(root.rglob(name), None)
        if found is not None:
            bold = next(root.rglob("DejaVuSans-Bold.ttf"), None)
            return found, bold

    raise FileNotFoundError(
        "Não encontrei fonte TTF (Times/Arial/DejaVu). Instale fontes no sistema."
    )


def _take_words_line(pdf: FPDF, words: list[str], max_w: float) -> tuple[str, list[str]]:
    """Monta uma linha que cabe em `max_w` (largura útil), medida com a fonte atual."""
    if not words:
        return "", []
    first = words[0]
    if pdf.get_string_width(first) > max_w:
        # palavra longa (ex.: URL): corta para não estourar
        lo, hi = 1, len(first)
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if pdf.get_string_width(first[:mid]) <= max_w:
                lo = mid
            else:
                hi = mid - 1
        return first[:lo], ([first[lo:]] + words[1:] if lo < len(first) else words[1:])
    line = first
    rest = words[1:]
    while rest:
        trial = line + " " + rest[0]
        if pdf.get_string_width(trial) <= max_w - 0.6:
            line = trial
            rest = rest[1:]
        else:
            break
    return line, rest


def _paragraph_abnt(pdf: FPDF, text: str) -> None:
    """Parágrafo: justificado, recuo só na primeira linha, entrelinhas 1,5."""
    text = " ".join(text.replace("\n", " ").split())
    if not text:
        return

    pdf.set_font("Doc", "", BODY_FONT_PT)
    l = pdf.l_margin
    w_total = pdf.w - pdf.l_margin - pdf.r_margin
    words = text.split()
    first_line = True

    while words:
        x0 = l + FIRST_LINE_INDENT_MM if first_line else l
        w_line = w_total - (FIRST_LINE_INDENT_MM if first_line else 0)
        line, words = _take_words_line(pdf, words, w_line)
        if not line:
            break
        pdf.set_x(x0)
        last_line = len(words) == 0
        pdf.multi_cell(w_line, LINE_HEIGHT_MM, line, align="L" if last_line else "J")
        first_line = False

    pdf.ln(LINE_HEIGHT_MM * 0.35)


def _logo_path(repo_root: Path) -> Path:
    return (repo_root / "assets" / "logo-fiap.png").resolve()


class _RelatorioPDF(FPDF):
    def footer(self) -> None:
        self.set_y(-12)
        self.set_font("Doc", "", 10)
        self.set_text_color(80, 80, 80)
        self.cell(0, 8, text=f"Página {self.page_no()} de {{nb}}", align="C")


def relatorio_md_to_pdf_bytes(repo_root: Path | None = None) -> tuple[bytes, str]:
    """
    Devolve (pdf_bytes, nome_ficheiro_sugerido).
    Levanta FileNotFoundError se `src/docs/relatorio.md` não existir.
    """
    root = (repo_root or Path(__file__).resolve().parents[2]).resolve()
    md_path = root / "src" / "docs" / "relatorio.md"
    if not md_path.is_file():
        raise FileNotFoundError(str(md_path))

    md_text = md_path.read_text(encoding="utf-8")
    buf = BytesIO()
    pdf = _RelatorioPDF(
        unit="mm",
        format="A4",
    )
    pdf.alias_nb_pages()
    pdf.set_margins(MARGIN_LEFT_MM, MARGIN_TOP_MM, MARGIN_RIGHT_MM)
    pdf.set_auto_page_break(auto=True, margin=MARGIN_BOTTOM_MM)

    reg, bold = _font_files()
    pdf.add_font("Doc", "", str(reg))
    has_bold = False
    if bold is not None and bold.is_file():
        pdf.add_font("Doc", "B", str(bold))
        has_bold = True

    pdf.add_page()

    # --- Capa visual: logo FIAP (1.ª página) ---
    logo = _logo_path(root)
    if logo.is_file():
        try:
            x_center = (pdf.w - LOGO_MAX_WIDTH_MM) / 2
            pdf.image(str(logo), x=x_center, y=pdf.get_y(), w=LOGO_MAX_WIDTH_MM)
            pdf.ln(22)
        except Exception:
            pdf.set_font("Doc", "", 9)
            pdf.multi_cell(0, 4, "[Logo FIAP não incluído — verifique assets/logo-fiap.png]")
            pdf.ln(3)
    else:
        pdf.ln(2)

    lines = md_text.splitlines()
    i, n = 0, len(lines)

    while i < n:
        raw_line = lines[i]
        stripped = raw_line.strip()
        if not stripped:
            i += 1
            continue

        if stripped.startswith("# "):
            pdf.set_font("Doc", "B" if has_bold else "", 14)
            pdf.multi_cell(0, LINE_HEIGHT_MM, stripped[2:].strip().upper(), align="C")
            pdf.ln(5)
            i += 1
            continue

        if stripped.startswith("## "):
            pdf.ln(2)
            pdf.set_font("Doc", "B" if has_bold else "", BODY_FONT_PT)
            pdf.multi_cell(0, LINE_HEIGHT_MM, stripped[3:].strip(), align="L")
            pdf.ln(2)
            i += 1
            continue

        if stripped.startswith("### "):
            pdf.ln(1)
            pdf.set_font("Doc", "B" if has_bold else "", BODY_FONT_PT)
            pdf.set_text_color(25, 25, 25)
            pdf.multi_cell(0, LINE_HEIGHT_MM, stripped[4:].strip(), align="L")
            pdf.set_text_color(0, 0, 0)
            pdf.ln(1.5)
            i += 1
            continue

        if stripped == "---" or (stripped.startswith("---") and set(stripped) <= {"-", " "}):
            pdf.ln(2)
            pdf.set_draw_color(180, 180, 180)
            y = pdf.get_y()
            pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)
            pdf.ln(4)
            i += 1
            continue

        if stripped.startswith("```"):
            i += 1
            chunk: list[str] = []
            while i < n and not lines[i].strip().startswith("```"):
                chunk.append(lines[i])
                i += 1
            if i < n:
                i += 1
            pdf.set_font("Doc", "", 10)
            pdf.set_fill_color(248, 248, 248)
            lh_code = 10 * (25.4 / 72.0) * 1.2
            txt = "\n".join(chunk) if chunk else ""
            pdf.set_x(pdf.l_margin + 5)
            pdf.multi_cell(pdf.epw - 5, lh_code, txt, fill=True, align="L")
            pdf.ln(3)
            pdf.set_font("Doc", "", BODY_FONT_PT)
            continue

        img_m = _RE_IMG.match(raw_line)
        if img_m:
            rel = unquote(img_m.group(2)).strip().lstrip("/")
            img_path = (root / rel).resolve()
            if img_path.is_file():
                try:
                    fig_w = min(160.0, pdf.epw)
                    x_fig = (pdf.w - fig_w) / 2
                    pdf.image(str(img_path), x=x_fig, w=fig_w)
                except Exception:
                    pdf.set_font("Doc", "", BODY_FONT_PT)
                    _paragraph_abnt(pdf, f"[Imagem omitida na exportação: {rel}]")
            else:
                pdf.set_font("Doc", "", BODY_FONT_PT)
                _paragraph_abnt(pdf, f"[Ficheiro de imagem inexistente: {rel}]")
            pdf.ln(3)
            i += 1
            continue

        if stripped.startswith("- "):
            pdf.set_font("Doc", "", BODY_FONT_PT)
            hang = 8.0
            while i < n:
                s = lines[i].strip()
                if not s:
                    break
                if not s.startswith("- "):
                    break
                txt = s[2:].strip()
                pdf.set_x(pdf.l_margin + hang)
                pdf.multi_cell(pdf.epw - hang, LINE_HEIGHT_MM, "\u2022  " + txt, align="L")
                i += 1
            pdf.ln(2)
            continue

        om = _RE_OL.match(raw_line)
        if om:
            num = int(om.group(1))
            pdf.set_font("Doc", "", BODY_FONT_PT)
            hang = 10.0
            while i < n:
                mm = _RE_OL.match(lines[i])
                if not mm:
                    break
                txt = mm.group(2).strip()
                label = f"{num}. "
                pdf.set_x(pdf.l_margin + hang)
                pdf.multi_cell(pdf.epw - hang, LINE_HEIGHT_MM, label + txt, align="L")
                num += 1
                i += 1
            pdf.ln(2)
            continue

        body: list[str] = []
        while i < n:
            s = lines[i]
            ts = s.strip()
            if not ts:
                break
            if (
                ts.startswith("#")
                or ts == "---"
                or ts.startswith("```")
                or _RE_IMG.match(s)
                or ts.startswith("- ")
                or _RE_OL.match(s)
            ):
                break
            body.append(ts)
            i += 1
        if body:
            _paragraph_abnt(pdf, " ".join(body))
            continue

        i += 1

    pdf.output(buf)
    return buf.getvalue(), "relatorio_farmtech.pdf"
