"""Validação reproduzível: python scripts/validar_r_fase2.py (na raiz do projeto)."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from farmtech_integracao.fase2_r import validar_fase2_r

resultado = validar_fase2_r()
print(resultado["message"])
if resultado["status"] == "ok":
    print("Registros históricos analisados:", resultado["historico_linhas"])
    print("Linhas de integração demonstrativa:", resultado["demonstracao_linhas"])
    print("CSV:", ".runtime/exports/fase2/validacao_r_demonstrativa.csv")
    print("Relatório:", ".runtime/exports/fase2/analise_r_historico.txt")
else:
    sys.exit(1)
