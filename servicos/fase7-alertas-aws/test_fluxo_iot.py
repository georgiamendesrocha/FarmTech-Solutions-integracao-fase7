"""Fluxo IoT local: origem, tempo, mensagem, deduplicação e SNS simulado."""

import contextlib
import csv
import io
import json
import sys
import tempfile
import types
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch

PASTA = Path(__file__).resolve().parent
if str(PASTA) not in sys.path:
    sys.path.insert(0, str(PASTA))

import monitorar
from mensagem import assunto, corpo
from sensores import CAMPOS_CSV, MARCADOR_EXEMPLO, avaliar_sensor, ler_leitura_csv


class FluxoIoTTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.pasta = Path(self.temp.name)
        self.csv = self.pasta / "captura.csv"
        self.registro = self.pasta / ".ultimo-alerta.json"
        registro = patch.object(monitorar, "REGISTRO", self.registro)
        registro.start()
        self.addCleanup(registro.stop)
        self.agora = datetime.now(timezone.utc)
        self.linha = {
            "ts_iso": (self.agora - timedelta(seconds=30)).isoformat(),
            "t_rel_ms": 30000, "umidade": 40, "temp_c": 24, "ldr": 2223,
            "ph_base": 6.4, "ph_corr": 6.4, "N": 1, "P": 1, "K": 1, "bomba_fw": 1,
        }
        self._gravar([self.linha])
        self.publicar = Mock(return_value="id-iot-simulado")
        modulo = types.ModuleType("publicar_sns")
        modulo.publicar = self.publicar
        sdk = patch.dict(sys.modules, {"publicar_sns": modulo, "boto3": None})
        sdk.start()
        self.addCleanup(sdk.stop)

    def _gravar(self, linhas, *, sintetico=False):
        with self.csv.open("w", newline="", encoding="utf-8") as destino:
            if sintetico:
                destino.write(MARCADOR_EXEMPLO + "\n")
            escritor = csv.DictWriter(destino, fieldnames=CAMPOS_CSV)
            escritor.writeheader()
            escritor.writerows(linhas)

    def _executar(self, *args):
        saida = io.StringIO()
        with contextlib.redirect_stdout(saida):
            retorno = monitorar.main(["--iot-csv", str(self.csv), *args])
        return retorno, saida.getvalue()

    def _enviar(self, *, origem="wokwi", dispositivo="esp32-a", local="Irecê"):
        return self._executar("--origem-iot", origem, "--dispositivo-iot", dispositivo,
                              "--local-iot", local, "--enviar")

    def test_dry_run_simulacao_nao_le_estado_nem_importa_publicador(self):
        self.registro.write_text("estado inválido preservado", encoding="utf-8")
        original = self.registro.read_bytes()
        with patch.dict(sys.modules, {"publicar_sns": None, "boto3": None}), \
                patch.object(monitorar, "repetido", side_effect=AssertionError("leu estado")):
            retorno, texto = self._executar("--origem-iot", "wokwi")
        self.assertEqual(retorno, 0)
        self.assertIn("SIMULAÇÃO WOKWI", texto)
        self.assertIn("não é medição física", texto)
        self.assertIn("proxy didático de solo", texto)
        self.assertIn("pH corrigido simulado", texto)
        self.assertIn("não são concentrações", texto)
        self.assertNotIn("Open-Meteo", texto)
        self.assertNotIn("Chuva prevista", texto)
        self.assertEqual(original, self.registro.read_bytes())

    def test_captura_esp32_nao_e_descrita_como_validacao_fisica(self):
        _, texto = self._executar("--origem-iot", "esp32")
        self.assertIn("ESP32 DECLARADO", texto)
        self.assertIn("origem física não verificada", texto)
        self.assertIn("não comprova nova aquisição válida no DHT22", texto)
        self.publicar.assert_not_called()

    def test_origem_desconhecida_e_padrao_explicito(self):
        _, texto = self._executar()
        self.assertIn("ORIGEM NÃO COMPROVADA", texto)
        self.assertIn("não classificar como medição física real", texto)
        self.assertIn("local IoT não informado", texto)

    def test_historico_preserva_data_e_identifica_reproducao(self):
        antiga = {**self.linha, "ts_iso": "2026-05-03T20:03:40"}
        self._gravar([antiga])
        original = self.csv.read_bytes()
        _, texto = self._executar("--fuso-iot=-03:00", "--historico-iot")
        self.assertIn("HISTÓRICO", texto)
        self.assertIn("não representa uma medição atual", texto)
        self.assertIn("2026-05-03T20:03:40", texto)
        self.assertIn("2026-05-03T23:03:40Z", texto)
        self.assertEqual(original, self.csv.read_bytes())
        self.assertFalse(self.registro.exists())

    def test_antigo_sem_modo_historico_e_rejeitado(self):
        self._gravar([{**self.linha, "ts_iso": (self.agora - timedelta(days=2)).isoformat()}])
        with self.assertRaises(ValueError):
            self._executar("--origem-iot", "wokwi")
        self.publicar.assert_not_called()

    def test_futuro_e_rejeitado_inclusive_em_reproducao(self):
        self._gravar([{**self.linha, "ts_iso": (self.agora + timedelta(hours=1)).isoformat()}])
        for args in ((), ("--historico-iot",)):
            with self.subTest(args=args), self.assertRaises(ValueError):
                self._executar(*args)
        self.publicar.assert_not_called()

    def test_naive_exige_fuso_da_captura(self):
        local = (self.agora - timedelta(seconds=30)).astimezone(timezone(timedelta(hours=-3)))
        self._gravar([{**self.linha, "ts_iso": local.replace(tzinfo=None).isoformat()}])
        with self.assertRaises(ValueError):
            self._executar()
        _, texto = self._executar("--fuso-iot=-03:00", "--origem-iot", "wokwi")
        self.assertIn("Horário UTC de recepção no PC", texto)

    def test_historico_exemplo_e_desconhecido_nao_enviam_antes_de_ler_arquivo(self):
        argumentos = (("--historico-iot", "--origem-iot", "wokwi"),
                      ("--origem-iot", "exemplo"), ())
        for args in argumentos:
            with self.subTest(args=args), patch.object(monitorar, "ler_leitura_csv") as ler, \
                    contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as erro:
                self._executar(*args, "--enviar")
            self.assertEqual(erro.exception.code, 2)
            ler.assert_not_called()
        self.publicar.assert_not_called()

    def test_envio_exige_local_e_dispositivo_explicitos(self):
        for args in ((), ("--local-iot", "Irecê"), ("--dispositivo-iot", "esp32-a"),
                     ("--local-iot", " ", "--dispositivo-iot", "esp32-a")):
            with self.subTest(args=args), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                self._executar("--origem-iot", "wokwi", *args, "--enviar")
        self.publicar.assert_not_called()

    def test_marcador_sintetico_bloqueia_envio_mesmo_declarado_esp32(self):
        self._gravar([self.linha], sintetico=True)
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as erro:
            self._enviar(origem="esp32")
        self.assertEqual(erro.exception.code, 2)
        self.publicar.assert_not_called()
        self.assertFalse(self.registro.exists())

    def test_marcador_sintetico_prevalece_sobre_rotulo_fisico_no_dry_run(self):
        self._gravar([self.linha], sintetico=True)
        _, texto = self._executar("--origem-iot", "esp32")
        self.assertIn("EXEMPLO SINTÉTICO", texto)
        self.assertNotIn("ESP32 DECLARADO", texto)
        self.assertIn("não é captura Wokwi nem medição física", texto)

    def test_publicacao_iot_simulada_persiste_tipo_e_payload(self):
        retorno, texto = self._enviar()
        self.assertEqual(retorno, 0)
        self.publicar.assert_called_once()
        alerta, local = self.publicar.call_args.args
        self.assertEqual(alerta["tipo"], "iot_umidade_baixa")
        self.assertEqual(local["iot_dispositivo"], "esp32-a")
        self.assertIn("SIMULAÇÃO WOKWI", self.publicar.call_args.kwargs["assunto"])
        self.assertIn(self.publicar.call_args.kwargs["corpo"], texto)
        estado = json.loads(self.registro.read_text(encoding="utf-8"))
        self.assertEqual(estado["registros"][0]["message_id"], "id-iot-simulado")

    def test_repeticao_por_dispositivo_local_e_origem_sem_interferencia(self):
        self._enviar()
        self._enviar(dispositivo="esp32-b")
        self._enviar(local="Salvador")
        self._enviar(origem="esp32")
        self.assertEqual(self.publicar.call_count, 4)
        _, texto = self._enviar()
        self.assertIn("recusada", texto)
        self.assertEqual(self.publicar.call_count, 4)

    def test_tipos_iot_e_meteorologico_nao_se_bloqueiam(self):
        local = {"name": "Irecê", "iot_dispositivo": "esp32-a", "iot_origem": "wokwi"}
        monitorar.gravar_registro({"tipo": "umidade_baixa"}, self.agora, "id-previsao", {"name": "Irecê"})
        self.assertFalse(monitorar.repetido({"tipo": "iot_umidade_baixa"}, self.agora, local))
        self._enviar()
        self.publicar.assert_called_once()

    def test_seis_horas_iot_preserva_fronteira(self):
        local = {"name": "Irecê", "iot_dispositivo": "esp32-a", "iot_origem": "wokwi"}
        alerta = {"tipo": "iot_umidade_baixa"}
        monitorar.gravar_registro(alerta, self.agora, "id-iot", local)
        self.assertTrue(monitorar.repetido(alerta, self.agora + timedelta(hours=6, microseconds=-1), local))
        self.assertFalse(monitorar.repetido(alerta, self.agora + timedelta(hours=6), local))

    def test_estado_invalido_bloqueia_sns_iot(self):
        self.registro.write_text("{", encoding="utf-8")
        with self.assertRaises(RuntimeError):
            self._enviar()
        self.publicar.assert_not_called()

    def test_falha_sns_iot_nao_cria_registro(self):
        self.publicar.side_effect = RuntimeError("falha SNS simulada")
        with self.assertRaisesRegex(RuntimeError, "falha SNS simulada"):
            self._enviar()
        self.assertFalse(self.registro.exists())

    def test_falha_pos_sns_iot_exige_reconciliacao_sem_retry(self):
        with patch.object(monitorar, "gravar_registro", side_effect=OSError("sem escrita")):
            with self.assertRaisesRegex(RuntimeError, "MessageId: id-iot-simulado.*não repita"):
                self._enviar()
        self.publicar.assert_called_once()

    def test_ultima_leitura_normal_nao_reutiliza_alerta_antigo(self):
        normal = {**self.linha, "ts_iso": (self.agora - timedelta(seconds=5)).isoformat(),
                  "umidade": 60, "bomba_fw": 0}
        self._gravar([normal, self.linha])
        _, texto = self._executar("--origem-iot", "wokwi")
        self.assertIn("Sem alerta IoT", texto)
        self.assertIn("simulação Wokwi declarada", texto)
        self.publicar.assert_not_called()

    def test_opcoes_iot_nao_sao_silenciosamente_aceitas_na_previsao(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            monitorar.main(["--cidade", "Irecê", "--historico-iot"])
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            self._executar("--horas", "6")

    def test_assunto_historico_preserva_identificacao_antes_do_corte(self):
        leitura = ler_leitura_csv(self.csv)
        alerta = avaliar_sensor(leitura, origem="wokwi", historico=True, agora=self.agora)
        alerta["alerta"] = "x" * 200
        texto = assunto(alerta)
        self.assertEqual(len(texto), 100)
        self.assertIn("HISTÓRICO / SIMULAÇÃO WOKWI", texto)


if __name__ == "__main__":
    unittest.main()
