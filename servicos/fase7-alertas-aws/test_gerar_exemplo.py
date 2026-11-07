"""Cenários sintéticos locais; sem consultas nem publicação de mensagens."""

import contextlib
import io
import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

PASTA = Path(__file__).resolve().parent
if str(PASTA) not in sys.path:
    sys.path.insert(0, str(PASTA))

import gerar_exemplo
from monitorar import ler_previsao
from regras import avaliar

AGORA = datetime(2026, 11, 6, 12, tzinfo=timezone.utc)


class GerarExemploTest(unittest.TestCase):
    def test_quatro_cenarios_validam_contra_as_regras(self):
        for tipo in gerar_exemplo.TIPOS:
            with self.subTest(tipo=tipo):
                previsao = gerar_exemplo.gerar_previsao(tipo, agora=AGORA)
                alerta = avaliar(previsao["data"]["hourly"], agora=AGORA)
                self.assertEqual(alerta["tipo"] if alerta else None, tipo if tipo != "normal" else None)
                self.assertEqual(previsao["status"], "ok")
                self.assertIs(previsao["source"]["synthetic"], True)
                self.assertEqual(previsao["source"]["provider"], "exemplo_sintetico")
                self.assertIn("dry-run", previsao["message"])

    def test_chuva_concorre_com_baixa_umidade_e_tem_prioridade(self):
        dados = gerar_exemplo.gerar_previsao("chuva", agora=AGORA)
        self.assertEqual(dados["data"]["hourly"][0]["umidade"], 42)
        self.assertEqual(dados["data"]["hourly"][0]["rain_mm"], 1.5)
        self.assertEqual(avaliar(dados["data"]["hourly"], agora=AGORA)["tipo"], "chuva")

    def test_timestamp_utc_uma_hora_adiante_inclusive_referencia_com_offset(self):
        for agora in (AGORA, AGORA.astimezone(timezone(timedelta(hours=-3))),
                      AGORA.replace(tzinfo=None)):
            with self.subTest(agora=agora):
                dados = gerar_exemplo.gerar_previsao("normal", agora=agora)
                self.assertEqual(dados["data"]["hourly"][0]["ts_iso"], "2026-11-06T13:00:00Z")

    def test_geracao_sem_referencia_usa_tempo_atual(self):
        antes = datetime.now(timezone.utc)
        dados = gerar_exemplo.gerar_previsao("normal")
        depois = datetime.now(timezone.utc)
        instante = datetime.fromisoformat(dados["data"]["hourly"][0]["ts_iso"].replace("Z", "+00:00"))
        self.assertGreaterEqual(instante, antes + timedelta(hours=1, seconds=-1))
        self.assertLessEqual(instante, depois + timedelta(hours=1))

    def test_tipo_e_referencia_invalidos_sao_rejeitados(self):
        for tipo in (None, True, [], "outro"):
            with self.subTest(tipo=tipo), self.assertRaises(ValueError):
                gerar_exemplo.gerar_previsao(tipo)
        with self.assertRaises(ValueError):
            gerar_exemplo.gerar_previsao("normal", agora="inválido")

    def test_cli_grava_utf8_e_roundtrip_com_leitor_fase2(self):
        with tempfile.TemporaryDirectory() as pasta:
            caminho = Path(pasta) / "nova-previsao.json"
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                self.assertEqual(gerar_exemplo.main(["--tipo", "chuva", "--saida", str(caminho)]), 0)
            self.assertEqual(stdout.getvalue(), str(caminho.resolve()) + "\n")
            self.assertIn("Irecê", caminho.read_text(encoding="utf-8"))
            local, hourly = ler_previsao(caminho)
            self.assertEqual(local["name"], "Irecê")
            self.assertEqual(avaliar(hourly)["tipo"], "chuva")

    def test_cli_recusa_sobrescrever_arquivo_existente(self):
        with tempfile.TemporaryDirectory() as pasta:
            caminho = Path(pasta) / "historico.json"
            conteudo = b"evidencia historica"
            caminho.write_bytes(conteudo)
            stdout, stderr = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                with self.assertRaises(SystemExit) as exc:
                    gerar_exemplo.main(["--saida", str(caminho)])
            self.assertEqual(exc.exception.code, 2)
            self.assertEqual(caminho.read_bytes(), conteudo)
            self.assertEqual(stdout.getvalue(), "")

    def test_cli_padrao_cria_nomes_unicos_sem_sobrescrever(self):
        with tempfile.TemporaryDirectory() as pasta, patch.object(gerar_exemplo, "PASTA", Path(pasta)):
            caminhos = []
            for _ in range(2):
                stdout = io.StringIO()
                with contextlib.redirect_stdout(stdout):
                    gerar_exemplo.main([])
                caminho = Path(stdout.getvalue().strip())
                self.assertTrue(caminho.is_absolute())
                self.assertEqual(caminho.parent, Path(pasta).resolve())
                self.assertTrue(caminho.name.startswith(".exemplo-previsao-"))
                self.assertIs(json.loads(caminho.read_text(encoding="utf-8"))["source"]["synthetic"], True)
                caminhos.append(caminho)
            self.assertNotEqual(caminhos[0], caminhos[1])


if __name__ == "__main__":
    unittest.main()
