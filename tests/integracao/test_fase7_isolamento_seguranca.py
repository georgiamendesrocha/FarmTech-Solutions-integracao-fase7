"""Negação de envio no contrato F7; não constitui teste de sandbox do sistema."""

import builtins
from contextlib import nullcontext
from datetime import datetime, timedelta, timezone
import importlib.util
import io
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from unittest import mock
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from farmtech_integracao import fase7, runtime
from farmtech_integracao.contracts import Result

_path_before = list(sys.path)
_spec = importlib.util.spec_from_file_location(
    "_fase7_worker_isolation_test", ROOT / "farmtech_integracao/workers/fase7_worker.py")
worker = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(worker)
sys.path[:] = _path_before


def previsao():
    instante = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    return {"status": "ok", "message": "Teste local sem consulta.", "data": {
        "location": {"name": "Local de teste"}, "timezone": "UTC",
        "hourly": [{"ts_iso": instante, "umidade": 40, "rain_mm": 0}],
    }, "source": {"provider": "teste local"}}


class EntradaBytes:
    def __init__(self, conteudo):
        self.buffer = io.BytesIO(conteudo)

    def reconfigure(self, **kwargs):
        pass


class IsolamentoFase7Test(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.paths = list(sys.path)
        nomes = ("sensores", "regras", "mensagem", "gerar_exemplo", "gerar_exemplo_iot")
        self.modules = {nome: sys.modules.get(nome) for nome in nomes}
        self.addCleanup(self._restaurar_modulos)
        worker._modules.cache_clear()
        self.tentativas = []
        self.estado = ROOT / "servicos/fase7-alertas-aws/.ultimo-alerta.json"
        self.estado_antes = self.estado.read_bytes() if self.estado.is_file() else None
        importar = builtins.__import__
        proibidos = {"monitorar", "publicar_sns", "boto3", "botocore", "farmtech_integracao.fase2"}

        def importacao_verificada(nome, globals=None, locals=None, fromlist=(), level=0):
            nomes = [nome] + [f"{nome}.{item}" for item in (fromlist or ()) if isinstance(item, str)]
            if any(candidato == proibido or candidato.startswith(proibido + ".")
                   for candidato in nomes for proibido in proibidos):
                self.tentativas.append("importacao_proibida")
                raise AssertionError("Importação de publicação ou consulta não permitida no worker F7.")
            return importar(nome, globals, locals, fromlist, level)

        def bloquear(*args, **kwargs):
            self.tentativas.append("rede_ou_processo")
            raise AssertionError("Contato de rede ou processo não permitido neste teste local.")

        for patcher in (
            mock.patch("builtins.__import__", side_effect=importacao_verificada),
            mock.patch.object(socket, "socket", side_effect=bloquear),
            mock.patch.object(socket, "create_connection", side_effect=bloquear),
            mock.patch.object(urllib.request, "urlopen", side_effect=bloquear),
            mock.patch.object(runtime.subprocess, "Popen", side_effect=bloquear),
            mock.patch.object(runtime.subprocess, "run", side_effect=bloquear),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)
        self.addCleanup(self._verificar_ausencia_de_envio)

    def _restaurar_modulos(self):
        sys.path[:] = self.paths
        for nome, anterior in self.modules.items():
            if anterior is None:
                sys.modules.pop(nome, None)
            else:
                sys.modules[nome] = anterior
        worker._modules.cache_clear()

    def _verificar_ausencia_de_envio(self):
        self.assertFalse(self.tentativas, "Houve tentativa de importar publicação, rede ou processo.")
        depois = self.estado.read_bytes() if self.estado.is_file() else None
        self.assertTrue(depois == self.estado_antes, "O estado de publicação SNS foi alterado.")

    def assert_previa(self, resultado):
        self.assertIs(resultado.data["preview_only"], True)
        self.assertIs(resultado.data["sns_enabled"], False)

    def test_operacoes_manipuladas_e_opcoes_de_envio_sao_rejeitadas(self):
        for operacao in ("publicar", "publish", "--enviar", '__import__("boto3")', ["demo_iot"], None):
            with self.subTest(operacao=operacao):
                resultado = worker.handle({"operation": operacao})
                self.assertEqual(resultado.status, "invalid")
                self.assert_previa(resultado)
        for campo in ("enviar", "--enviar", "send", "publish", "env", "AWS_SNS_TOPIC_ARN",
                      "AWS_DEFAULT_REGION", "AWS_ACCESS_KEY_ID", "path", "arquivo", "command",
                      "shell", "python", "sns_enabled", "preview_only"):
            with self.subTest(campo=campo):
                resultado = worker.handle({"operation": "demo_iot", "tipo": "normal", campo: True})
                self.assertEqual(resultado.status, "invalid")
                self.assert_previa(resultado)

    def test_campos_aninhados_e_tipos_de_exemplo_nao_habilitam_envio(self):
        dados = previsao()
        dados["source"].update(enviar=True, AWS_SNS_TOPIC_ARN="sentinela", operation="publish")
        dados["data"].update(enviar=True, sns_enabled=True, command="--enviar")
        resultado = worker.handle({"operation": "evaluate_weather", "previsao": dados})
        self.assertEqual(resultado.status, "ok")
        self.assert_previa(resultado)
        self.assertNotIn("AWS_SNS_TOPIC_ARN", resultado.source)
        for tipo in ("--enviar", "normal; publish", "$(publicar)", {"enviar": True}):
            with self.subTest(tipo=tipo):
                resultado = worker.handle({"operation": "demo_weather", "tipo": tipo})
                self.assertEqual(resultado.status, "invalid")
                self.assert_previa(resultado)

    def test_quatro_rotas_nao_importam_sdk_ou_publicador_nem_contatam_rede(self):
        for payload in ({"operation": "demo_iot", "tipo": "umidade_baixa"},
                        {"operation": "demo_weather", "tipo": "chuva"},
                        {"operation": "evaluate_weather", "previsao": previsao()}):
            with self.subTest(operacao=payload["operation"]):
                resultado = worker.handle(payload)
                self.assertEqual(resultado.status, "ok")
                self.assert_previa(resultado)
        instante = (datetime.now(timezone.utc) - timedelta(seconds=30)).isoformat()
        caminho = self.directory / "iot.csv"
        caminho.write_text("ts_iso,t_rel_ms,umidade,temp_c,ldr,ph_base,ph_corr,N,P,K,bomba_fw\n"
                           + instante + ",30000,40,25,2223,6.4,6.4,1,1,1,1\n", encoding="utf-8")
        with mock.patch.object(worker, "HISTORY_CSV", caminho):
            resultado = worker.handle({"operation": "evaluate_iot_csv", "local": "--enviar; $(publish)",
                                       "dispositivo": "AWS_SNS_TOPIC_ARN=sentinela"})
        self.assertEqual(resultado.status, "ok")
        self.assert_previa(resultado)
        self.assertIn("--enviar; $(publish)", resultado.data["body"])

    def test_json_recebido_duplicado_malformado_e_acima_do_limite(self):
        # json.loads aplica o último valor. Mesmo entradas duplicadas só alcançam
        # operações permitidas ou a rejeição; não expõem um comando de publicação.
        casos = (
            (b'{"operation":"publicar","operation":"demo_iot","tipo":"normal"}', "ok"),
            (b'{"operation":"demo_iot","operation":"publicar","tipo":"normal"}', "invalid"),
            (b'{"operation":"demo_iot","tipo":"normal","enviar":false,"enviar":true}', "invalid"),
            (b'{"operation":', "invalid"), (b"[]", "invalid"), (b"\xff", "invalid"),
            (b"x" * (worker.MAX_REQUEST_BYTES + 1), "invalid"),
        )
        for conteudo, status in casos:
            with self.subTest(tamanho=len(conteudo), status=status):
                saida = io.StringIO()
                with mock.patch.object(worker.sys, "stdin", EntradaBytes(conteudo)), \
                        mock.patch.object(worker.sys, "stdout", saida), \
                        mock.patch.object(worker.sys, "stderr", io.StringIO()):
                    worker.main()
                resultado = Result.from_dict(json.loads(saida.getvalue()))
                self.assertEqual(resultado.status, status)
                self.assert_previa(resultado)

    def test_runtime_remove_configuracoes_e_usa_argv_fixo_sem_shell(self):
        nomes = ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN", "AWS_SNS_TOPIC_ARN",
                 "AWS_DEFAULT_REGION", "AWS_REGION", "AWS_PROFILE", "AWS_SHARED_CREDENTIALS_FILE",
                 "BOTO_CONFIG", "PYTHONPATH", "PYTHONHOME", "PYTHONSTARTUP", "ORACLE_USER", "ORACLE_PASS", "ORACLE_DSN")
        with mock.patch.dict(os.environ, {nome: "sentinela" for nome in nomes}):
            ambiente = runtime._environment("fase7")
        self.assertFalse(set(nomes) & set(ambiente))
        with mock.patch.object(runtime, "_phase_lock", return_value=nullcontext()), \
                mock.patch.object(runtime, "_execute", return_value=(
                    0, json.dumps(Result("ok", "local").as_dict()).encode(), None)) as executar:
            resultado = runtime.run_json_worker("fase7", {"operation": "demo_iot", "tipo": "--enviar"})
        self.assertEqual(resultado.status, "ok")
        comando = executar.call_args.args[0]
        self.assertEqual(comando[1:5], ["-X", "utf8", "-I", "-B"])
        self.assertNotIn("--enviar", comando)
        self.assertNotIn("shell", executar.call_args.kwargs)
        self.assertEqual(Path(comando[-1]), runtime.WORKERS["fase7"])

    def test_adaptador_filtra_configuracoes_e_forca_flags_de_previa(self):
        dados = previsao()
        dados["source"].update(enviar=True, AWS_SNS_TOPIC_ARN="sentinela")
        with mock.patch.object(fase7, "run_json_worker", return_value=Result(
                "ok", "sentinela", {"sns_enabled": True, "preview_only": False})) as executar:
            resultado = fase7.evaluate_weather(dados)
        self.assert_previa(resultado)
        payload = executar.call_args.args[1]
        self.assertNotIn("enviar", payload["previsao"]["source"])
        self.assertNotIn("AWS_SNS_TOPIC_ARN", payload["previsao"]["source"])


if __name__ == "__main__":
    unittest.main()
