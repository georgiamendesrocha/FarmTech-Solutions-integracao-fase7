"""Decodifica apenas os bytes conhecidos do logo local, sem aceitar imagens externas."""

from hashlib import sha256
from io import BytesIO
from pathlib import Path
from PIL import Image

LOGO = Path(__file__).resolve().parents[2] / "assets" / "logo_fiap.webp"
LOGO_SHA256 = "88fcf629c91768f001178a54ec1d470ffdf361c280353e9c0636b4a27db21a93"


def carregar_logo(path: Path = LOGO) -> Image.Image:
    content = Path(path).read_bytes()
    if sha256(content).hexdigest() != LOGO_SHA256:
        raise ValueError("Integridade do logo local inválida.")
    # Restringe o decodificador e evita janela entre verificar e abrir o arquivo.
    with Image.open(BytesIO(content), formats=["WEBP"]) as logo:
        logo.load()
        return logo.copy()
