
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# Wrapper para `streamlit run app.py` na raiz.
# A execução efetiva ocorre em `src/frontend/app.py` (que chama pg.run()).
import src.frontend.app  # noqa: F401
