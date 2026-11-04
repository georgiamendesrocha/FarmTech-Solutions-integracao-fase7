"""Confere links relativos, imagens e âncoras Markdown/HTML, sem acessar a rede."""

import re
import sys
import unicodedata
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
IGNORED = {".git", ".pio", ".venv", "venv", "__pycache__", ".tmp_r_audit"}


def without_fences(text):
    return re.sub(r"^(`{3,}|~{3,})[^\n]*\n.*?^\1\s*$", "", text, flags=re.M | re.S)


def anchors(text):
    result = set(re.findall(r"<(?:a|h[1-6])\b[^>]*\b(?:name|id)=[\"']([^\"']+)[\"']", text, re.I))
    counts = {}
    for title in re.findall(r"^#{1,6}\s+(.+?)\s*#*\s*$", without_fences(text), re.M):
        title = re.sub(r"<[^>]+>", "", title).lower()
        slug = "".join(c for c in title if unicodedata.category(c)[0] in "LN" or c in " _-")
        slug = slug.replace(" ", "-")
        count = counts.get(slug, 0)
        result.add(slug if not count else f"{slug}-{count}")
        counts[slug] = count + 1
    return result


def main():
    documents = sorted(path for path in ROOT.rglob("*.md") if not any(p in IGNORED or p.startswith(".tmp") for p in path.relative_to(ROOT).parts))
    checked = 0
    errors = []
    for source in documents:
        text = without_fences(source.read_text(encoding="utf-8-sig"))
        links = re.findall(r"!?\[[^\]\n]*\]\(([^)\n]+)\)", text)
        links += re.findall(r"\b(?:href|src)=[\"']([^\"']+)[\"']", text, re.I)
        for link in links:
            target = re.sub(r'\s+[\"\'][^\"\']*[\"\']$', '', link.strip()).strip("<>")
            parsed = urlsplit(target)
            if parsed.scheme or parsed.netloc:
                continue
            checked += 1
            destination = (source.parent / unquote(parsed.path)).resolve() if parsed.path else source
            try:
                destination.relative_to(ROOT)
            except ValueError:
                errors.append(f"{source.relative_to(ROOT)}: destino fora do projeto: {target}")
                continue
            if not destination.exists():
                errors.append(f"{source.relative_to(ROOT)}: ausente: {target}")
            elif parsed.fragment and destination.suffix.lower() == ".md":
                available = anchors(destination.read_text(encoding="utf-8-sig"))
                if unquote(parsed.fragment) not in available:
                    errors.append(f"{source.relative_to(ROOT)}: ancora ausente: {target}")
    for error in errors:
        print(error)
    print(f"{len(documents)} documentos; {checked} links relativos/imagens/ancoras; {len(errors)} erros.")
    return bool(errors)


if __name__ == "__main__":
    sys.exit(main())
