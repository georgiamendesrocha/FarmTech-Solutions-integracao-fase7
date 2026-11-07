"""Prévias F7 locais: limites, origem, isolamento e ausência de publicação."""

import builtins
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import importlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from farmtech_integracao import fase7, runtime
from farmtech_integracao.contracts import Result

spec = importlib.util.spec_from_file_location("_fase7_worker_test", ROOT / "farmtech_integracao/workers/fase7_worker.py")
_path_before = list(sys.path)
worker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(worker)
sys.path[:] = _path_before


def csv_content(*, at=None, humidity=40, synthetic=False, naive=False, ph=6.4, n=1, p=1, k=1):
    at = at or datetime.now(timezone.utc) - timedelta(seconds=30)
    stamp = at.replace(tzinfo=None).isoformat() if naive else at.isoformat().replace("+00:00", "Z")
    header = "ts_iso,t_rel_ms,umidade,temp_c,ldr,ph_base,ph_corr,N,P,K,bomba_fw\n"
    marker = "# FARMTECH_EXEMPLO_IOT_SINTETICO\n" if synthetic else ""
    bomba = int(humidity < 45 or (humidity <= 80 and (not 6 <= ph <= 6.8 or not all((n, p, k)))))
    return (marker + header + f"{stamp},30000,{humidity},25,2223,6.4,{ph},{n},{p},{k},{bomba}\n").encode("utf-8")


def weather(*, humidity=40, rain=0, at=None):
    at = at or datetime.now(timezone.utc) + timedelta(hours=1)
    return {"status": "ok", "message": "previsão disponível", "data": {
        "location": {"name": "Irecê", "admin1": "Bahia", "country": "Brasil"},
        "hourly": [{"ts_iso": at.isoformat().replace("+00:00", "Z"), "umidade": humidity, "rain_mm": rain}],
        "timezone": "UTC",
    }, "source": {"provider": "Open-Meteo"}}


class Fase7Tests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.paths = list(sys.path)
        names = ("sensores", "regras", "mensagem", "gerar_exemplo", "gerar_exemplo_iot")
        self.modules = {name: sys.modules.get(name) for name in names}
        self.addCleanup(self._restore_modules)
        worker._modules.cache_clear()

    def _restore_modules(self):
        sys.path[:] = self.paths
        for name, previous in self.modules.items():
            if previous is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous
        worker._modules.cache_clear()

    def assert_preview(self, result):
        self.assertIs(result.data["preview_only"], True)
        self.assertIs(result.data["sns_enabled"], False)
        for name in ("alert", "has_alert", "subject", "body", "reading", "local", "mode", "evaluated_at"):
            self.assertIn(name, result.data)
        for name in ("provider", "origin", "historical", "synthetic", "resource"):
            self.assertIn(name, result.source)
        self.assertTrue(result.data["evaluated_at"].endswith("Z"))

    def test_csv_exibe_tres_condicoes_coexistentes_e_preserva_prioridade_umidade(self):
        with self.csv_file(csv_content(humidity=80.5, ph=5.147, p=0)):
            result = worker.handle({"operation": "evaluate_iot_csv", "origem": "wokwi"})
        self.assertEqual(result.status, "ok")
        self.assertEqual(result.data["alert"]["tipo"], "iot_umidade_alta")
        conditions = result.data["conditions"]
        self.assertEqual([item["tipo"] for item in conditions],
                         ["iot_umidade_alta", "iot_ph_fora_faixa", "iot_npk_ausente"])
        self.assertEqual([item["valor"] for item in conditions], [80.5, 5.147, "1/0/1"])
        self.assertEqual([item["primary"] for item in conditions], [True, False, False])
        self.assertTrue(all(set(item) == {"tipo", "condicao", "valor", "limiar", "primary"} for item in conditions))
        self.assert_preview(result)

    def test_condicoes_historicas_preservam_modo_sem_transformar_publicacao(self):
        at = datetime.now(timezone.utc) - timedelta(days=10)
        with self.csv_file(csv_content(at=at, humidity=80.5, ph=5.147, p=0)):
            result = worker.handle({"operation": "evaluate_iot_csv", "historico": True})
        self.assertEqual(len(result.data["conditions"]), 3)
        self.assertEqual(result.data["mode"], "historico")
        self.assertIs(result.source["historical"], True)
        self.assertEqual(result.source["origin"], "desconhecida")
        self.assert_preview(result)

    def test_demo_iot_tambem_exibe_todas_condicoes_sem_mudar_origem_sintetica(self):
        generator = worker._modules()[4]
        reading = generator.gerar_leitura("umidade_alta")
        reading.update(umidade=80.5, ph_corr=5.147, P=0)
        with mock.patch.object(generator, "gerar_leitura", return_value=reading):
            result = worker.handle({"operation": "demo_iot", "tipo": "umidade_alta"})
        self.assertEqual(result.status, "ok")
        self.assertEqual(len(result.data["conditions"]), 3)
        self.assertEqual(sum(item["primary"] for item in result.data["conditions"]), 1)
        self.assertEqual(result.source["origin"], "exemplo")
        self.assertIs(result.source["synthetic"], True)
        self.assertEqual(result.data["mode"], "demonstracao")
        self.assert_preview(result)

    def test_condicoes_normais_ficam_vazias_com_metadata_preservada(self):
        for source in ("csv", "demo"):
            with self.subTest(source=source):
                if source == "csv":
                    with self.csv_file(csv_content(humidity=60)):
                        result = worker.handle({"operation": "evaluate_iot_csv", "origem": "esp32"})
                    self.assertEqual(result.source["origin"], "esp32")
                    self.assertEqual(result.data["mode"], "recepcao_recente")
                else:
                    result = worker.handle({"operation": "demo_iot", "tipo": "normal"})
                    self.assertEqual(result.source["origin"], "exemplo")
                    self.assertEqual(result.data["mode"], "demonstracao")
                self.assertEqual(result.data["conditions"], [])
                self.assertIsNone(result.data["alert"])
                self.assertIs(result.data["has_alert"], False)
                self.assert_preview(result)

    def test_condicoes_ph_e_npk_coexistem_com_ph_principal_na_faixa_intermediaria(self):
        with self.csv_file(csv_content(humidity=60, ph=5.147, p=0)):
            result = worker.handle({"operation": "evaluate_iot_csv"})
        self.assertEqual(result.data["alert"]["tipo"], "iot_ph_fora_faixa")
        self.assertEqual([item["tipo"] for item in result.data["conditions"]],
                         ["iot_ph_fora_faixa", "iot_npk_ausente"])
        self.assertEqual([item["primary"] for item in result.data["conditions"]], [True, False])

    def test_meteorologia_tem_tres_horarios_distintos_sem_fallback(self):
        evaluated = datetime(2026, 11, 6, 15, tzinfo=timezone.utc)
        consulted = "2026-11-06T11:47:00-03:00"
        event = evaluated + timedelta(hours=2)
        forecast = weather(at=event)
        forecast["source"]["retrieved_at"] = consulted
        result = worker._weather(forecast, agora=evaluated)
        self.assertEqual(result.data["forecast_retrieved_at"], consulted)
        self.assertEqual(result.source["retrieved_at"], consulted)
        self.assertEqual(result.data["evaluated_at"], "2026-11-06T15:00:00Z")
        self.assertEqual(result.data["forecast_event_at"], "2026-11-06T17:00:00Z")
        self.assertEqual(result.data["forecast_event_at"], result.data["alert"]["instante"])
        self.assert_preview(result)

    def test_consulta_meteorologica_ausente_ou_invalida_permanece_none(self):
        evaluated = datetime(2026, 11, 6, 15, tzinfo=timezone.utc)
        for retrieved in (None, "", "horario-invalido", 123):
            with self.subTest(retrieved=retrieved):
                forecast = weather(at=evaluated + timedelta(hours=1))
                if retrieved is not None:
                    forecast["source"]["retrieved_at"] = retrieved
                result = worker._weather(forecast, agora=evaluated)
                self.assertIsNone(result.data["forecast_retrieved_at"])
                self.assertNotIn("retrieved_at", result.source)
                self.assertIsNotNone(result.data["forecast_event_at"])

    def test_sem_alerta_nao_inventa_horario_de_evento_na_primeira_linha(self):
        evaluated = datetime(2026, 11, 6, 15, tzinfo=timezone.utc)
        forecast = weather(humidity=60, at=evaluated + timedelta(hours=1))
        forecast["source"]["retrieved_at"] = "2026-11-06T14:55:00Z"
        result = worker._weather(forecast, agora=evaluated)
        self.assertIsNone(result.data["alert"])
        self.assertIsNone(result.data["forecast_event_at"])
        self.assertEqual(result.data["forecast_retrieved_at"], "2026-11-06T14:55:00Z")
        self.assert_preview(result)

    def test_demo_weather_nao_inventa_consulta_externa(self):
        for tipo in ("chuva", "normal"):
            with self.subTest(tipo=tipo):
                result = worker.handle({"operation": "demo_weather", "tipo": tipo})
                self.assertEqual(result.status, "ok")
                self.assertIsNone(result.data["forecast_retrieved_at"])
                self.assertNotIn("retrieved_at", result.source)
                self.assertEqual(result.source["origin"], "exemplo")
                self.assertIs(result.source["synthetic"], True)
                if tipo == "normal":
                    self.assertIsNone(result.data["forecast_event_at"])
                else:
                    self.assertEqual(result.data["forecast_event_at"], result.data["alert"]["instante"])
                    self.assertIn("DEMONSTRAÇÃO SINTÉTICA", result.data["subject"])
                self.assert_preview(result)

    @contextmanager
    def csv_file(self, content):
        path = self.directory / "history.csv"
        path.write_bytes(content)
        original = path.read_bytes()
        with mock.patch.object(worker, "HISTORY_CSV", path):
            yield path
        self.assertEqual(path.read_bytes(), original)

    def test_adapter_import_e_availability_nao_executam_ou_escrevem(self):
        before = list(sys.path)
        with mock.patch.object(Path, "open", side_effect=AssertionError("import tentou abrir arquivo")), \
                mock.patch.object(Path, "mkdir", side_effect=AssertionError("import tentou criar pasta")), \
                mock.patch.object(runtime, "run_json_worker", side_effect=AssertionError("worker no import")):
            importlib.reload(fase7)
            result = fase7.availability()
        self.assertEqual(sys.path, before)
        self.assertEqual(result.status, "ok")
        self.assert_preview(result)
        self.assertIs(result.data["available"], True)
        importlib.reload(fase7)

    def test_availability_ausencia_de_fonte_e_unavailable(self):
        with mock.patch.object(fase7, "SERVICE_ROOT", self.directory):
            result = fase7.availability()
        self.assertEqual(result.status, "unavailable")
        self.assertIn("sensores.py", result.data["missing"])
        self.assert_preview(result)

    def test_adapter_upload_transmite_so_uuid_e_limpa_copia(self):
        content = csv_content()
        called = []

        def run(phase, payload, **kwargs):
            called.append(payload.copy())
            token = payload["upload_id"]
            self.assertEqual(phase, "fase7")
            self.assertRegex(token, r"^[0-9a-f]{32}$")
            self.assertEqual((self.directory / f"upload-{token}.csv").read_bytes(), content)
            return Result("ok", "simulado")

        with mock.patch.object(fase7, "UPLOAD_DIR", self.directory), mock.patch.object(fase7, "run_json_worker", side_effect=run):
            result = fase7.evaluate_iot_csv(content, origem="wokwi", local="Irecê", dispositivo="ESP32-1")
        self.assertEqual(list(self.directory.iterdir()), [])
        self.assertNotIn("content", called[0])
        self.assertNotIn("path", called[0])
        self.assert_preview(result)

    def test_adapter_upload_limpa_copia_em_erro_do_worker(self):
        with mock.patch.object(fase7, "UPLOAD_DIR", self.directory), \
                mock.patch.object(fase7, "run_json_worker", return_value=Result("error", "falha simulada")):
            result = fase7.evaluate_iot_csv(csv_content())
        self.assertEqual(result.status, "error")
        self.assertEqual(list(self.directory.iterdir()), [])
        self.assert_preview(result)

    def test_upload_invalido_vazio_grande_ou_path_nao_cria_arquivo(self):
        with mock.patch.object(fase7, "run_json_worker") as run, mock.patch.object(fase7, "UPLOAD_DIR", self.directory):
            for content in ("caminho.csv", Path("caminho.csv"), b"", b"x" * (fase7.MAX_CSV_BYTES + 1)):
                with self.subTest(tipo=type(content).__name__):
                    result = fase7.evaluate_iot_csv(content)
                    self.assertEqual(result.status, "invalid")
                    self.assert_preview(result)
            run.assert_not_called()
        self.assertEqual(list(self.directory.iterdir()), [])

    def test_upload_tamanho_maximo_usa_token_sem_expandir_json(self):
        with mock.patch.object(fase7, "UPLOAD_DIR", self.directory), \
                mock.patch.object(fase7, "run_json_worker", return_value=Result("ok", "simulado")) as run:
            result = fase7.evaluate_iot_csv(b"x" * fase7.MAX_CSV_BYTES)
        self.assertEqual(result.status, "ok")
        self.assertLess(len(json.dumps(run.call_args.args[1])), 1000)
        self.assertEqual(list(self.directory.iterdir()), [])

    def test_uuid_existente_nao_e_sobrescrito_nem_excluido(self):
        token = "a" * 32
        existing = self.directory / f"upload-{token}.csv"
        existing.write_bytes(b"arquivo preexistente")
        with mock.patch.object(fase7, "UPLOAD_DIR", self.directory), \
                mock.patch.object(fase7.uuid, "uuid4", return_value=types.SimpleNamespace(hex=token)):
            result = fase7.evaluate_iot_csv(csv_content())
        self.assertEqual(result.status, "unavailable")
        self.assertEqual(existing.read_bytes(), b"arquivo preexistente")

    def test_none_envia_operacao_sem_caminho_ou_upload(self):
        with mock.patch.object(fase7, "run_json_worker", return_value=Result("ok", "simulado")) as run:
            fase7.evaluate_iot_csv(historico=True, fuso="-03:00")
        payload = run.call_args.args[1]
        self.assertNotIn("upload_id", payload)
        self.assertNotIn("path", payload)
        self.assertIs(payload["historico"], True)

    def test_worker_rejeita_envio_credenciais_e_caminhos(self):
        bad = [{"operation": "publicar"}, {"operation": "demo_iot", "tipo": "normal", "enviar": True},
               {"operation": "evaluate_iot_csv", "path": "arquivo.csv"},
               {"operation": "demo_weather", "tipo": "normal", "AWS_SNS_TOPIC_ARN": "inexistente"},
               {"operation": "evaluate_iot_csv", "upload_id": "../../historico"}]
        for payload in bad:
            with self.subTest(payload=payload):
                result = worker.handle(payload)
                self.assertEqual(result.status, "invalid")
                self.assert_preview(result)

    def test_worker_csv_ausente_e_unavailable(self):
        with mock.patch.object(worker, "HISTORY_CSV", self.directory / "inexistente.csv"):
            result = worker.handle({"operation": "evaluate_iot_csv"})
        self.assertEqual(result.status, "unavailable")
        self.assert_preview(result)

    def test_worker_csv_maior_que_limite_e_invalido(self):
        with self.csv_file(b"x" * (worker.MAX_CSV_BYTES + 1)):
            result = worker.handle({"operation": "evaluate_iot_csv"})
        self.assertEqual(result.status, "invalid")

    def test_worker_csv_utf8_invalido_ou_cabecalho_invalido(self):
        for content in (b"\xff\xfe", b"coluna_errada\n1\n"):
            with self.subTest(content=content), self.csv_file(content):
                result = worker.handle({"operation": "evaluate_iot_csv"})
                self.assertEqual(result.status, "invalid")
                self.assert_preview(result)

    def test_csv_atual_preserva_origem_declarada_e_mensagem_sem_envio(self):
        with self.csv_file(csv_content()):
            result = worker.handle({"operation": "evaluate_iot_csv", "origem": "wokwi", "local": "Irecê", "dispositivo": "A"})
        self.assertEqual(result.status, "ok")
        self.assertEqual(result.source["origin"], "wokwi")
        self.assertEqual(result.data["mode"], "recepcao_recente")
        self.assertEqual(result.data["alert"]["tipo"], "iot_umidade_baixa")
        self.assertIn("SIMULAÇÃO WOKWI", result.data["subject"])
        self.assertIn("não é medição física", result.data["body"])
        self.assert_preview(result)

    def test_sem_alerta_preserva_modo_origem_e_leitura(self):
        with self.csv_file(csv_content(humidity=60)):
            result = worker.handle({"operation": "evaluate_iot_csv", "origem": "esp32"})
        self.assertEqual(result.status, "ok")
        self.assertIs(result.data["has_alert"], False)
        self.assertIsNone(result.data["alert"])
        self.assertEqual(result.data["reading"]["umidade"], 60)
        self.assertEqual(result.source["origin"], "esp32")
        self.assertEqual(result.data["mode"], "recepcao_recente")
        self.assert_preview(result)

    def test_marcador_csv_forca_exemplo_inclusive_sem_alerta(self):
        with self.csv_file(csv_content(humidity=60, synthetic=True)):
            result = worker.handle({"operation": "evaluate_iot_csv", "origem": "wokwi"})
        self.assertEqual(result.source["origin"], "exemplo")
        self.assertIs(result.source["synthetic"], True)
        self.assertEqual(result.data["mode"], "demonstracao")
        self.assertIsNone(result.data["alert"])

    def test_csv_sem_offset_exige_fuso_explicito(self):
        with self.csv_file(csv_content(naive=True)):
            invalid = worker.handle({"operation": "evaluate_iot_csv"})
            valid = worker.handle({"operation": "evaluate_iot_csv", "fuso": "UTC"})
        self.assertEqual(invalid.status, "invalid")
        self.assertEqual(valid.status, "ok")
        self.assertTrue(valid.data["reading"]["ts_iso"].endswith("Z"))

    def test_csv_antigo_exige_historico_sem_reescrever_timestamp(self):
        at = datetime.now(timezone.utc) - timedelta(days=30)
        with self.csv_file(csv_content(at=at)):
            invalid = worker.handle({"operation": "evaluate_iot_csv"})
            replay = worker.handle({"operation": "evaluate_iot_csv", "historico": True})
        self.assertEqual(invalid.status, "invalid")
        self.assertEqual(replay.status, "ok")
        self.assertEqual(replay.data["mode"], "historico")
        self.assertIs(replay.source["historical"], True)
        self.assertEqual(replay.data["reading"]["ts_iso"], at.isoformat().replace("+00:00", "Z"))
        self.assert_preview(replay)

    def test_csv_futuro_rejeitado_inclusive_historico(self):
        with self.csv_file(csv_content(at=datetime.now(timezone.utc) + timedelta(hours=1))):
            result = worker.handle({"operation": "evaluate_iot_csv", "historico": True})
        self.assertEqual(result.status, "invalid")
        self.assertIn("futuro", result.message)

    def test_cinco_demos_iot_reais_no_worker_isolado(self):
        for tipo in ("umidade_baixa", "umidade_alta", "ph_fora_faixa", "npk_ausente", "normal"):
            with self.subTest(tipo=tipo):
                result = fase7.demo_iot(tipo)
                self.assertEqual(result.status, "ok", result.message)
                self.assertEqual(result.source["origin"], "exemplo")
                self.assertIs(result.source["synthetic"], True)
                self.assertEqual(result.data["mode"], "demonstracao")
                self.assertEqual(result.data["has_alert"], tipo != "normal")
                self.assert_preview(result)

    def test_demos_invalidas_rejeitadas(self):
        for operation in (fase7.demo_iot, fase7.demo_weather):
            result = operation("invalido")
            self.assertEqual(result.status, "invalid")
            self.assert_preview(result)

    def test_upload_real_via_adapter_worker_e_limpeza(self):
        result = fase7.evaluate_iot_csv(csv_content(), origem="desconhecida")
        self.assertEqual(result.status, "ok", result.message)
        self.assertEqual(result.source["resource"], "upload_csv")
        self.assertEqual(result.source["origin"], "desconhecida")
        self.assert_preview(result)

    def test_previsao_valida_alerta_e_normal_sem_rede(self):
        for humidity, expected in ((40, True), (60, False)):
            with self.subTest(humidity=humidity):
                result = worker.handle({"operation": "evaluate_weather", "previsao": weather(humidity=humidity)})
                self.assertEqual(result.status, "ok")
                self.assertEqual(result.data["has_alert"], expected)
                self.assertEqual(result.data["mode"], "previsao")
                self.assertEqual(result.source["origin"], "previsao_fase2")
                self.assert_preview(result)

    def test_previsao_chuva_preserva_prioridade(self):
        result = worker.handle({"operation": "evaluate_weather", "previsao": weather(humidity=30, rain=1)})
        self.assertEqual(result.data["alert"]["tipo"], "chuva")

    def test_previsao_vazia_invalida_ou_fora_janela_nao_e_normal(self):
        empty = weather()
        empty["data"]["hourly"] = []
        absent = weather(humidity=None, rain=None)
        for forecast in (empty, absent, weather(at=datetime.now(timezone.utc) - timedelta(days=2)),
                         weather(at=datetime.now(timezone.utc) + timedelta(hours=24))):
            with self.subTest(forecast=forecast):
                result = worker.handle({"operation": "evaluate_weather", "previsao": forecast})
                self.assertEqual(result.status, "invalid")
                self.assertIsNone(result.data["alert"])
                self.assert_preview(result)

    def test_previsao_result_indisponivel_preserva_status(self):
        result = worker.handle({"operation": "evaluate_weather", "previsao": {"status": "unavailable", "message": "sem previsão"}})
        self.assertEqual(result.status, "unavailable")
        self.assertEqual(result.message, "Previsão indisponível. Confira a consulta meteorológica.")
        self.assert_preview(result)

    def test_previsao_adapter_nao_muta_entrada_e_reduz_payload(self):
        forecast = weather()
        forecast["data"]["hourly"][0]["temp_c"] = 25
        forecast["source"]["csv_path"] = "nao-transmitir.csv"
        original = json.dumps(forecast, sort_keys=True)
        with mock.patch.object(fase7, "run_json_worker", return_value=Result("ok", "simulado")) as run:
            result = fase7.evaluate_weather(forecast)
        payload = run.call_args.args[1]["previsao"]
        self.assertNotIn("temp_c", payload["data"]["hourly"][0])
        self.assertNotIn("csv_path", payload["source"])
        self.assertEqual(json.dumps(forecast, sort_keys=True), original)
        self.assert_preview(result)

    def test_previsao_preserva_data_original_da_consulta(self):
        forecast = weather()
        forecast["source"]["retrieved_at"] = "2026-11-06T10:00:00Z"
        result = worker.handle({"operation": "evaluate_weather", "previsao": forecast})
        self.assertEqual(result.source["retrieved_at"], "2026-11-06T10:00:00Z")

    def test_result_ou_previsao_malformados_sao_invalidos(self):
        for value in (None, [], {"status": "ok", "message": 1}):
            with self.subTest(value=value):
                self.assertEqual(fase7.evaluate_weather(value).status, "invalid")
        invalid = weather()
        invalid["data"]["timezone"] = "America/Bahia"
        self.assertEqual(worker.handle({"operation": "evaluate_weather", "previsao": invalid}).status, "invalid")

    def test_quatro_demos_weather_reais_no_worker_isolado(self):
        for tipo in ("chuva", "umidade_baixa", "umidade_alta", "normal"):
            with self.subTest(tipo=tipo):
                result = fase7.demo_weather(tipo)
                self.assertEqual(result.status, "ok", result.message)
                self.assertEqual(result.data["has_alert"], tipo != "normal")
                self.assertIs(result.source["synthetic"], True)
                self.assertEqual(result.data["mode"], "demonstracao")
                if tipo != "normal":
                    self.assertIn("DEMONSTRAÇÃO SINTÉTICA", result.data["subject"])
                    self.assertIn("somente teste local", result.data["body"])
                    self.assertLessEqual(len(result.data["subject"]), 100)
                self.assert_preview(result)

    def test_worker_nunca_importa_publicador_cli_sdk_ou_consulta_fase2(self):
        importar = builtins.__import__
        forbidden = {"monitorar", "publicar_sns", "boto3", "botocore", "farmtech_integracao.fase2"}

        def checked(name, *args, **kwargs):
            if any(name == item or name.startswith(item + ".") for item in forbidden):
                raise AssertionError("Importação proibida: " + name)
            return importar(name, *args, **kwargs)

        state = ROOT / "servicos/fase7-alertas-aws/.ultimo-alerta.json"
        before = state.read_bytes() if state.is_file() else None
        with mock.patch("builtins.__import__", side_effect=checked):
            for payload in ({"operation": "demo_iot", "tipo": "normal"},
                            {"operation": "demo_weather", "tipo": "chuva"},
                            {"operation": "evaluate_weather", "previsao": weather()}):
                self.assertEqual(worker.handle(payload).status, "ok")
        after = state.read_bytes() if state.is_file() else None
        self.assertEqual(after, before)

    def test_runtime_fase7_exclui_credenciais_aws(self):
        with mock.patch.dict(runtime.os.environ, {"AWS_ACCESS_KEY_ID": "sentinela", "AWS_SECRET_ACCESS_KEY": "sentinela",
                                                 "AWS_SESSION_TOKEN": "sentinela", "AWS_SNS_TOPIC_ARN": "sentinela",
                                                 "ORACLE_USER": "sentinela", "ORACLE_PASS": "sentinela", "ORACLE_DSN": "sentinela"}):
            environment = runtime._environment("fase7")
        self.assertFalse(any(key.startswith(("AWS_", "ORACLE_")) for key in environment))


if __name__ == "__main__":
    unittest.main()
