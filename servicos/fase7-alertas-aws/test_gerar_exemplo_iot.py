"""Exemplos IoT sintéticos; nunca capturam Wokwi, sensores físicos ou SNS."""

import contextlib
import csv
import io
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

PASTA = Path(__file__).resolve().parent
if str(PASTA) not in sys.path:
    sys.path.insert(0, str(PASTA))

import gerar_exemplo_iot
from sensores import MARCADOR_EXEMPLO, avaliar_sensor, ler_leitura_csv

AGORA = datetime(2026, 11, 6, 12, tzinfo=timezone.utc)


class GerarExemploIoTTest(unittest.TestCase):
    def test_contrato_preserva_os_onze_campos_originais(self):
        esperado = ("ts_iso", "t_rel_ms", "umidade", "temp_c", "ldr", "ph_base", "ph_corr",
                    "N", "P", "K", "bomba_fw")
        leitura = gerar_exemplo_iot.gerar_leitura("normal", agora=AGORA)
        self.assertEqual(tuple(leitura), esperado)
        self.assertEqual(leitura["t_rel_ms"], 30000)
        self.assertEqual(leitura["temp_c"], 25)

    def test_cenarios_e_bomba_coerentes_com_firmware(self):
        esperados = {
            "umidade_baixa": (40, 6.4, 1, 1),
            "umidade_alta": (85, 6.4, 1, 0),
            "ph_fora_faixa": (60, 7.2, 1, 1),
            "npk_ausente": (60, 6.1, 0, 1),
            "normal": (60, 6.4, 1, 0),
        }
        for tipo, esperado in esperados.items():
            with self.subTest(tipo=tipo):
                leitura = gerar_exemplo_iot.gerar_leitura(tipo, agora=AGORA)
                self.assertEqual((leitura["umidade"], leitura["ph_corr"], leitura["N"],
                                  leitura["bomba_fw"]), esperado)
                self.assertEqual((leitura["P"], leitura["K"]), (1, 1))

    def test_timestamp_utc_trinta_segundos_atras_com_fuso_ou_sem_fuso(self):
        referencias = (AGORA, AGORA.astimezone(timezone(timedelta(hours=-3))),
                       AGORA.replace(tzinfo=None))
        for agora in referencias:
            with self.subTest(agora=agora):
                leitura = gerar_exemplo_iot.gerar_leitura("normal", agora=agora)
                self.assertEqual(leitura["ts_iso"], "2026-11-06T11:59:30Z")

    def test_sem_referencia_usa_instante_atual_sem_reescrever_historico(self):
        antes = datetime.now(timezone.utc)
        leitura = gerar_exemplo_iot.gerar_leitura("normal")
        depois = datetime.now(timezone.utc)
        instante = datetime.fromisoformat(leitura["ts_iso"].replace("Z", "+00:00"))
        self.assertGreaterEqual(instante, antes - timedelta(seconds=31))
        self.assertLessEqual(instante, depois - timedelta(seconds=30))

    def test_tipo_e_referencia_invalidos_sao_rejeitados(self):
        for tipo in (None, True, [], "outro"):
            with self.subTest(tipo=tipo), self.assertRaises(ValueError):
                gerar_exemplo_iot.gerar_leitura(tipo)
        with self.assertRaises(ValueError):
            gerar_exemplo_iot.gerar_leitura("normal", agora="inválido")

    def test_cli_help_identifica_dados_gerados_sem_wokwi_ou_sensor_fisico(self):
        with tempfile.TemporaryDirectory() as pasta, patch.object(gerar_exemplo_iot, "PASTA", Path(pasta)):
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                with self.assertRaises(SystemExit) as exc:
                    gerar_exemplo_iot.main(["--help"])
            self.assertEqual(exc.exception.code, 0)
            self.assertIn("sintético em Python", stdout.getvalue())
            self.assertIn("não é captura Wokwi nem sensor físico", stdout.getvalue())
            self.assertEqual(list(Path(pasta).iterdir()), [])

    def test_cli_roundtrip_cenarios_mantem_origem_exemplo_mesmo_se_recente(self):
        with tempfile.TemporaryDirectory() as pasta:
            for tipo in gerar_exemplo_iot.TIPOS:
                with self.subTest(tipo=tipo):
                    caminho = Path(pasta) / (tipo + ".csv")
                    stdout = io.StringIO()
                    with contextlib.redirect_stdout(stdout):
                        self.assertEqual(gerar_exemplo_iot.main(["--tipo", tipo, "--saida", str(caminho)]), 0)
                    self.assertEqual(stdout.getvalue(), str(caminho.resolve()) + "\n")
                    linhas = caminho.read_text(encoding="utf-8").splitlines()
                    self.assertEqual(linhas[0], "# FARMTECH_EXEMPLO_IOT_SINTETICO")
                    self.assertEqual(linhas[0], MARCADOR_EXEMPLO)
                    self.assertEqual(tuple(next(csv.reader([linhas[1]]))), gerar_exemplo_iot.CAMPOS)
                    self.assertEqual(len(linhas), 3)
                    leitura = ler_leitura_csv(caminho)
                    self.assertIs(leitura["_sintetico"], True)
                    alerta = avaliar_sensor(leitura, origem="wokwi")
                    if tipo == "normal":
                        self.assertIsNone(alerta)
                    else:
                        self.assertEqual(alerta["tipo"], "iot_" + tipo)
                        self.assertEqual(alerta["origem"], "exemplo")
                        self.assertIs(alerta["sintetico"], True)

    def test_cli_nao_sobrescreve_arquivo_historico(self):
        with tempfile.TemporaryDirectory() as pasta:
            caminho = Path(pasta) / "historico_irrigacao.csv"
            original = b"evidencia historica preservada"
            caminho.write_bytes(original)
            stdout, stderr = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                with self.assertRaises(SystemExit) as exc:
                    gerar_exemplo_iot.main(["--saida", str(caminho)])
            self.assertEqual(exc.exception.code, 2)
            self.assertEqual(caminho.read_bytes(), original)
            self.assertEqual(stdout.getvalue(), "")

    def test_cli_padrao_cria_nomes_unicos_no_diretorio_do_servico(self):
        with tempfile.TemporaryDirectory() as pasta, patch.object(gerar_exemplo_iot, "PASTA", Path(pasta)):
            caminhos = []
            for _ in range(2):
                stdout = io.StringIO()
                with contextlib.redirect_stdout(stdout):
                    gerar_exemplo_iot.main([])
                caminho = Path(stdout.getvalue().strip())
                self.assertTrue(caminho.is_absolute())
                self.assertEqual(caminho.parent, Path(pasta).resolve())
                self.assertTrue(caminho.name.startswith(".exemplo-iot-"))
                self.assertEqual(caminho.suffix, ".csv")
                self.assertEqual(caminho.read_text(encoding="utf-8").splitlines()[0], MARCADOR_EXEMPLO)
                caminhos.append(caminho)
            self.assertNotEqual(caminhos[0], caminhos[1])

    def test_cli_tipo_invalido_ou_diretorio_ausente_nao_cria_csv(self):
        with tempfile.TemporaryDirectory() as pasta:
            caminho = Path(pasta) / "ausente" / "exemplo.csv"
            for argumentos in (["--tipo", "invalido", "--saida", str(caminho)],
                               ["--saida", str(caminho)]):
                with self.subTest(argumentos=argumentos), contextlib.redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit) as exc:
                        gerar_exemplo_iot.main(argumentos)
                    self.assertEqual(exc.exception.code, 2)
                    self.assertFalse(caminho.exists())


if __name__ == "__main__":
    unittest.main()
