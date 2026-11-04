import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from regras import avaliar


AGORA = datetime(2026, 11, 4, 12, 0, tzinfo=timezone.utc)


def hora(offset, umidade=None, chuva=None):
    instante = (AGORA + timedelta(hours=offset)).isoformat().replace("+00:00", "Z")
    return {"ts_iso": instante, "umidade": umidade, "rain_mm": chuva}


class RegrasTomate(unittest.TestCase):
    def test_umidade_baixa_pede_irrigacao(self):
        alerta = avaliar([hora(1, umidade=40, chuva=0)], agora=AGORA)
        self.assertEqual(alerta["tipo"], "umidade_baixa")
        self.assertIn("Ligar a irrigação", alerta["acao"])

    def test_chuva_vence_umidade_baixa(self):
        alerta = avaliar([hora(1, umidade=30, chuva=2)], agora=AGORA)
        self.assertEqual(alerta["tipo"], "chuva")
        self.assertIn("desligada", alerta["acao"])

    def test_umidade_alta(self):
        alerta = avaliar([hora(2, umidade=85, chuva=0)], agora=AGORA)
        self.assertEqual(alerta["tipo"], "umidade_alta")

    def test_faixa_normal_nao_alerta(self):
        self.assertIsNone(avaliar([hora(1, umidade=60, chuva=0)], agora=AGORA))

    def test_hora_fora_da_janela_e_ignorada(self):
        self.assertIsNone(avaliar([hora(13, umidade=20, chuva=0)], agora=AGORA))

    def test_arquivo_de_exemplo_gera_alerta(self):
        exemplo = Path(__file__).with_name("exemplo-previsao.json")
        dados = json.loads(exemplo.read_text(encoding="utf-8"))
        alerta = avaliar(dados["data"]["hourly"], agora=AGORA, horas=12)
        self.assertEqual(alerta["tipo"], "umidade_baixa")


class Mensagem(unittest.TestCase):
    def test_corpo_traz_alerta_e_acao(self):
        from mensagem import assunto, corpo

        alerta = avaliar([hora(1, umidade=40, chuva=0)], agora=AGORA)
        texto = corpo(alerta, {"name": "Irecê", "admin1": "Bahia", "country": "Brasil"})
        self.assertIn("Umidade prevista: 40.0%", texto)
        self.assertIn("Ligar a irrigação", texto)
        self.assertTrue(assunto(alerta).startswith("FarmTech:"))


class MonitorArquivo(unittest.TestCase):
    def test_modo_local_nao_publica(self):
        from monitorar import main

        instante = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat().replace("+00:00", "Z")
        with tempfile.TemporaryDirectory() as pasta:
            arquivo = Path(pasta) / "previsao.json"
            arquivo.write_text(json.dumps({
                "status": "ok",
                "message": "teste",
                "data": {
                    "location": {"name": "Irecê"},
                    "hourly": [{"ts_iso": instante, "umidade": 42, "rain_mm": 0}],
                },
                "source": {},
            }), encoding="utf-8")
            codigo = main(["--arquivo", str(arquivo)])
        self.assertEqual(codigo, 0)


if __name__ == "__main__":
    unittest.main()
