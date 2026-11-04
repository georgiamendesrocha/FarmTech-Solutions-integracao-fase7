"""Nenhuma imagem alterada é entregue ao decodificador Pillow."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from src.frontend.assets import carregar_logo


class AssetSafetyTests(unittest.TestCase):
    def test_verified_logo_remains_readable(self):
        logo = carregar_logo()
        self.assertGreater(logo.width, 0)
        self.assertGreater(logo.height, 0)

    def test_altered_bytes_are_rejected_before_decoding(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "logo.webp"
            path.write_bytes(b"not a trusted image")
            with patch("src.frontend.assets.Image.open") as decoder:
                with self.assertRaises(ValueError):
                    carregar_logo(path)
                decoder.assert_not_called()
