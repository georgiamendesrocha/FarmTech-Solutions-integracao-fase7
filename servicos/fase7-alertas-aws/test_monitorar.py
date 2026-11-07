"""Validação local do monitor e do contrato F2, sem rede nem SDK AWS."""

import contextlib
import io
import json
import subprocess
import sys
import tempfile
import types
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

PASTA = Path(__file__).resolve().parent
if str(PASTA) not in sys.path:
    sys.path.insert(0, str(PASTA))

import monitorar


class MonitorarTests(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        self.addCleanup(self.pasta.cleanup)
        self.registro = Path(self.pasta.name) / ".ultimo-alerta.json"
        self.patch_registro = mock.patch.object(monitorar, "REGISTRO", self.registro)
        self.patch_registro.start()
        self.addCleanup(self.patch_registro.stop)
        self.agora = datetime.now(timezone.utc)
        self.local = {"name": "Irecê", "admin1": "Bahia", "country": "Brasil"}
        self.outra = {"name": "Salvador", "admin1": "Bahia", "country": "Brasil"}
        self.alerta = {"tipo": "umidade_baixa"}
        self.hourly = [{"ts_iso": (self.agora + timedelta(hours=1)).isoformat(),
                        "umidade": 42, "rain_mm": 0, "temp_c": 29}]

    def _escrever(self, valor):
        self.registro.write_text(json.dumps(valor), encoding="utf-8")

    def _legado(self, quando=None):
        return {"tipo": "umidade_baixa", "publicado_em": (quando or self.agora).isoformat(),
                "message_id": "publicacao-anterior"}

    def _cli(self, argumentos, publicar=None):
        modulo = types.ModuleType("publicar_sns")
        modulo.publicar = publicar or mock.Mock(return_value="mensagem-confirmada")
        with mock.patch.object(monitorar, "consultar_cidade", return_value=(self.local, self.hourly)), \
                mock.patch.dict(sys.modules, {"publicar_sns": modulo}), \
                contextlib.redirect_stdout(io.StringIO()) as saida:
            retorno = monitorar.main(argumentos)
        return retorno, saida.getvalue(), modulo.publicar

    def test_registro_ausente_permite_primeiro_envio(self):
        self.assertFalse(monitorar.repetido(self.alerta, self.agora, self.local))

    def test_bloqueia_antes_de_seis_horas_e_libera_na_fronteira(self):
        monitorar.gravar_registro(self.alerta, self.agora, "id-a", self.local)
        self.assertTrue(monitorar.repetido(self.alerta, self.agora + timedelta(hours=6, microseconds=-1), self.local))
        self.assertFalse(monitorar.repetido(self.alerta, self.agora + timedelta(hours=6), self.local))

    def test_cidades_distintas_e_sequencia_a_b_a(self):
        monitorar.gravar_registro(self.alerta, self.agora, "id-a", self.local)
        self.assertFalse(monitorar.repetido(self.alerta, self.agora, self.outra))
        monitorar.gravar_registro(self.alerta, self.agora + timedelta(minutes=1), "id-b", self.outra)
        depois = self.agora + timedelta(minutes=2)
        self.assertTrue(monitorar.repetido(self.alerta, depois, self.local))
        self.assertTrue(monitorar.repetido(self.alerta, depois, self.outra))

    def test_tipos_distintos_nao_apagam_historico(self):
        outro_alerta = {"tipo": "chuva"}
        monitorar.gravar_registro(self.alerta, self.agora, "id-a", self.local)
        self.assertFalse(monitorar.repetido(outro_alerta, self.agora, self.local))
        monitorar.gravar_registro(outro_alerta, self.agora, "id-b", self.local)
        self.assertTrue(monitorar.repetido(self.alerta, self.agora, self.local))

    def test_nome_cidade_normaliza_caixa_e_espacos(self):
        monitorar.gravar_registro(self.alerta, self.agora, "id-a", self.local)
        equivalente = {"name": "  IRECÊ ", "admin1": "BAHIA", "country": " Brasil "}
        self.assertTrue(monitorar.repetido(self.alerta, self.agora, equivalente))

    def test_local_sem_nome_e_rejeitado(self):
        for local in ({}, {"name": " "}, "Irecê"):
            with self.subTest(local=local), self.assertRaises(ValueError):
                monitorar.repetido(self.alerta, self.agora, local)

    def test_legado_preserva_bloqueio_com_cidade_desconhecida(self):
        self._escrever(self._legado())
        self.assertTrue(monitorar.repetido(self.alerta, self.agora, self.local))
        self.assertTrue(monitorar.repetido(self.alerta, self.agora, self.outra))
        self.assertFalse(monitorar.repetido(self.alerta, self.agora + timedelta(hours=6), self.local))

    def test_legado_sem_fuso_e_interpretado_em_utc(self):
        legado = self._legado()
        legado["publicado_em"] = self.agora.replace(tzinfo=None).isoformat()
        self._escrever(legado)
        self.assertTrue(monitorar.repetido(self.alerta, self.agora, self.local))

    def test_migra_legado_sem_perder_bloqueio(self):
        self._escrever(self._legado())
        monitorar.gravar_registro({"tipo": "chuva"}, self.agora, "id-b", self.local)
        dados = json.loads(self.registro.read_text(encoding="utf-8"))
        self.assertEqual(len(dados["registros"]), 2)
        self.assertTrue(monitorar.repetido(self.alerta, self.agora, self.local))

    def test_descarta_registros_expirados_ao_gravar(self):
        monitorar.gravar_registro(self.alerta, self.agora, "id-antigo", self.local)
        depois = self.agora + timedelta(hours=6)
        monitorar.gravar_registro(self.alerta, depois, "id-novo", self.local)
        dados = json.loads(self.registro.read_text(encoding="utf-8"))
        self.assertEqual([r["message_id"] for r in dados["registros"]], ["id-novo"])

    def test_json_vazio_ou_corrompido_bloqueia_envio(self):
        for texto in ("", "{", "null", "[]", "{}", '{"registros": null}'):
            with self.subTest(texto=texto):
                self.registro.write_text(texto, encoding="utf-8")
                with self.assertRaisesRegex(RuntimeError, "Registro"):
                    monitorar.repetido(self.alerta, self.agora, self.local)

    def test_campos_invalidos_no_registro_bloqueiam_envio(self):
        for campo, valor in (("publicado_em", 123), ("publicado_em", "ontem"),
                             ("tipo", []), ("tipo", "desconhecido"),
                             ("message_id", ""), ("message_id", None), ("cidade", "")):
            with self.subTest(campo=campo, valor=valor):
                registro = self._legado()
                registro[campo] = valor
                self._escrever(registro)
                with self.assertRaises(RuntimeError):
                    monitorar.repetido(self.alerta, self.agora, self.local)

    def test_timestamp_futuro_bloqueia_com_erro(self):
        self._escrever(self._legado(self.agora + timedelta(seconds=1)))
        with self.assertRaisesRegex(RuntimeError, "futuro"):
            monitorar.repetido(self.alerta, self.agora, self.local)

    def test_erro_de_leitura_nao_equivale_a_ausencia(self):
        with mock.patch.object(Path, "read_text", side_effect=PermissionError("sem leitura")):
            with self.assertRaisesRegex(RuntimeError, "ilegível"):
                monitorar.repetido(self.alerta, self.agora, self.local)

    def test_registro_em_diretorio_e_rejeitado(self):
        self.registro.mkdir()
        with self.assertRaises(RuntimeError):
            monitorar.repetido(self.alerta, self.agora, self.local)

    def test_gravacao_atomica_preserva_registro_se_replace_falhar(self):
        self._escrever(self._legado())
        original = self.registro.read_bytes()
        with mock.patch.object(monitorar.os, "replace", side_effect=PermissionError("sem escrita")):
            with self.assertRaises(OSError):
                monitorar.gravar_registro({"tipo": "chuva"}, self.agora, "id-b", self.local)
        self.assertEqual(self.registro.read_bytes(), original)
        self.assertEqual(list(Path(self.pasta.name).iterdir()), [self.registro])

    def test_falha_criacao_temporario_preserva_registro(self):
        self._escrever(self._legado())
        original = self.registro.read_bytes()
        with mock.patch.object(monitorar.tempfile, "NamedTemporaryFile", side_effect=PermissionError("sem escrita")):
            with self.assertRaises(OSError):
                monitorar.gravar_registro({"tipo": "chuva"}, self.agora, "id-b", self.local)
        self.assertEqual(self.registro.read_bytes(), original)

    def test_dry_run_nao_importa_sns_nem_le_ou_modifica_registro(self):
        self.registro.write_text("estado inválido preservado", encoding="utf-8")
        original = self.registro.read_bytes()
        with mock.patch.dict(sys.modules, {"publicar_sns": None, "boto3": None}), \
                mock.patch.dict(monitorar.os.environ, {}, clear=True), \
                mock.patch.object(monitorar, "consultar_cidade", return_value=(self.local, self.hourly)), \
                mock.patch.object(monitorar, "repetido", side_effect=AssertionError("dry-run leu estado")), \
                contextlib.redirect_stdout(io.StringIO()) as saida:
            self.assertEqual(monitorar.main(["--cidade", "Irecê"]), 0)
        self.assertIn("Modo local", saida.getvalue())
        self.assertIn("Irecê", saida.getvalue())
        self.assertEqual(self.registro.read_bytes(), original)

    def test_arquivo_com_enviar_e_rejeitado_antes_de_qualquer_io(self):
        with mock.patch.object(monitorar, "ler_previsao") as ler, \
                mock.patch.object(monitorar, "consultar_cidade") as consultar, \
                contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as erro:
            monitorar.main(["--arquivo", "inexistente.json", "--enviar"])
        self.assertEqual(erro.exception.code, 2)
        ler.assert_not_called()
        consultar.assert_not_called()

    def test_arquivo_json_valido_e_dry_run_sem_sns(self):
        caminho = Path(self.pasta.name) / "previsao.json"
        caminho.write_text(json.dumps({"status": "ok", "data": {"location": self.local, "hourly": self.hourly}}), encoding="utf-8")
        with mock.patch.dict(sys.modules, {"publicar_sns": None}), contextlib.redirect_stdout(io.StringIO()) as saida:
            self.assertEqual(monitorar.main(["--arquivo", str(caminho)]), 0)
        self.assertIn("Modo local", saida.getvalue())
        self.assertFalse(self.registro.exists())

    def test_arquivo_rejeita_result_ou_hourly_invalidos(self):
        caminho = Path(self.pasta.name) / "previsao.json"
        for dados in ([], {"status": "error"}, {"status": "ok", "data": {}},
                      {"status": "ok", "data": {"hourly": {}}}):
            with self.subTest(dados=dados):
                caminho.write_text(json.dumps(dados), encoding="utf-8")
                with self.assertRaises(ValueError):
                    monitorar.ler_previsao(caminho)

    def test_estado_corrompido_impede_chamada_sns(self):
        self.registro.write_text("{", encoding="utf-8")
        publicar = mock.Mock()
        with self.assertRaises(RuntimeError):
            self._cli(["--cidade", "Irecê", "--enviar"], publicar)
        publicar.assert_not_called()

    def test_publicacao_simulada_persiste_id_e_mesmo_payload_impresso(self):
        retorno, saida, publicar = self._cli(["--cidade", "Irecê", "--enviar"])
        self.assertEqual(retorno, 0)
        publicar.assert_called_once()
        alerta, local = publicar.call_args.args
        self.assertEqual(alerta["tipo"], "umidade_baixa")
        self.assertEqual(local, self.local)
        self.assertIn(publicar.call_args.kwargs["assunto"], saida)
        self.assertIn(publicar.call_args.kwargs["corpo"], saida)
        dados = json.loads(self.registro.read_text(encoding="utf-8"))
        self.assertEqual(dados["registros"][0]["message_id"], "mensagem-confirmada")

    def test_repeticao_impede_segunda_publicacao(self):
        self._cli(["--cidade", "Irecê", "--enviar"])
        retorno, saida, publicar = self._cli(["--cidade", "Irecê", "--enviar"])
        self.assertEqual(retorno, 0)
        self.assertIn("recusada", saida)
        publicar.assert_not_called()

    def test_falha_publicacao_nao_grava_estado(self):
        publicar = mock.Mock(side_effect=RuntimeError("boto3 simulado indisponível"))
        with self.assertRaisesRegex(RuntimeError, "boto3 simulado"):
            self._cli(["--cidade", "Irecê", "--enviar"], publicar)
        publicar.assert_called_once()
        self.assertFalse(self.registro.exists())

    def test_falha_pos_sns_expoe_message_id_sem_retry(self):
        publicar = mock.Mock(return_value="id-confirmado-123")
        with mock.patch.object(monitorar, "gravar_registro", side_effect=OSError("disco indisponível")):
            with self.assertRaisesRegex(RuntimeError, "MessageId: id-confirmado-123.*não repita"):
                self._cli(["--cidade", "Irecê", "--enviar"], publicar)
        publicar.assert_called_once()

    def test_sem_alerta_nao_importa_sns_nem_grava_estado(self):
        self.hourly[0]["umidade"] = 60
        with mock.patch.dict(sys.modules, {"publicar_sns": None}), \
                mock.patch.object(monitorar, "consultar_cidade", return_value=(self.local, self.hourly)), \
                contextlib.redirect_stdout(io.StringIO()) as saida:
            self.assertEqual(monitorar.main(["--cidade", "Irecê", "--enviar"]), 0)
        self.assertIn("Sem alerta", saida.getvalue())
        self.assertFalse(self.registro.exists())

    def test_consulta_result_indisponivel_propaga_erro(self):
        modulo = types.ModuleType("farmtech_integracao.fase2")
        modulo.forecast = mock.Mock(return_value=types.SimpleNamespace(ok=False, message="serviço indisponível"))
        with mock.patch.dict(sys.modules, {"farmtech_integracao.fase2": modulo}):
            with self.assertRaisesRegex(RuntimeError, "serviço indisponível"):
                monitorar.consultar_cidade("Irecê")

    def test_contrato_real_adapter_fase2_d9dabed_sem_rede(self):
        raiz = PASTA.parents[1]
        codigo = subprocess.run(["git", "show", "d9dabed:farmtech_integracao/fase2.py"],
                                cwd=raiz, check=True, capture_output=True, encoding="utf-8").stdout
        from farmtech_integracao.contracts import Result

        pacote = types.ModuleType("_fase2_d9_auditada")
        pacote.__path__ = []
        contracts = types.ModuleType(pacote.__name__ + ".contracts")
        contracts.Result = Result
        r = types.ModuleType(pacote.__name__ + ".fase2_r")
        r.localizar_rscript = mock.Mock(return_value=None)
        runtime = types.ModuleType(pacote.__name__ + ".runtime")
        runtime.PROJECT_ROOT = Path(self.pasta.name)
        runtime.SERVICE_DIRS = {"fase2": Path(self.pasta.name)}
        hourly = [{"city": "Irecê", "country": "Brasil", "latitude": -11.3, "longitude": -41.8,
                   **self.hourly[0], "wind_ms": 2, "weathercode": 0}]
        resultado = Result("ok", "previsão real no contrato F2", {
            "location": self.local, "hourly": hourly, "timezone": "UTC", "persistence": False,
            "units": {"umidade": "%", "rain_mm": "mm", "temp_c": "°C", "wind_ms": "m/s"},
        }, {"phase": "fase2", "provider": "Open-Meteo", "retrieved_at": self.agora.isoformat()})
        runtime.run_json_worker = mock.Mock(return_value=resultado)
        modulo = types.ModuleType(pacote.__name__ + ".fase2")
        modulo.__package__ = pacote.__name__
        modulos = {p.__name__: p for p in (pacote, contracts, r, runtime, modulo)}
        with mock.patch.dict(sys.modules, modulos):
            exec(compile(codigo, "d9dabed:farmtech_integracao/fase2.py", "exec"), modulo.__dict__)
            with mock.patch.object(modulo, "_export_csv", return_value=Path(self.pasta.name) / "previsao.csv"):
                with mock.patch.dict(sys.modules, {"farmtech_integracao.fase2": modulo}):
                    local, serie = monitorar.consultar_cidade("Irecê")
        runtime.run_json_worker.assert_called_once_with("fase2", {"operation": "forecast", "city": "Irecê"}, timeout=40)
        self.assertEqual(local, self.local)
        self.assertEqual(serie, hourly)
        self.assertTrue(resultado.source["csv_exported"])
        self.assertTrue(resultado.data["persistence"])
        self.assertEqual(monitorar.avaliar(serie, agora=self.agora)["tipo"], "umidade_baixa")
        self.assertFalse(self.registro.exists())


if __name__ == "__main__":
    unittest.main()
