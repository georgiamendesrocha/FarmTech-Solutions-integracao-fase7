"""Limites de leitura e caminhos F7; fixtures exclusivas, sem AWS ou rede."""

from datetime import datetime, timedelta, timezone
import importlib.util
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from farmtech_integracao import fase7
from farmtech_integracao.contracts import Result

spec = importlib.util.spec_from_file_location("_fase7_file_security_tests", ROOT / "farmtech_integracao/workers/fase7_worker.py")
before = list(sys.path)
worker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(worker)
sys.path[:] = before


def csv_content():
    stamp = (datetime.now(timezone.utc) - timedelta(seconds=30)).isoformat().replace("+00:00", "Z")
    header = "ts_iso,t_rel_ms,umidade,temp_c,ldr,ph_base,ph_corr,N,P,K,bomba_fw\n"
    row = f"{stamp},30000,40,25,2223,6.4,6.4,1,1,1,1\n"
    return (header + row).encode(), header, row


class Fase7FileSecurityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="farmtech_file_security_")
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.paths = list(sys.path)
        self.modules = {name: sys.modules.get(name) for name in
                        ("sensores", "regras", "mensagem", "gerar_exemplo", "gerar_exemplo_iot")}
        self.addCleanup(self._restore)
        worker._modules.cache_clear()
        self.content, self.header, self.row = csv_content()
        self.source = self.directory / "history.csv"
        self.source.write_bytes(self.content)
        self.uploads = self.directory / "uploads"
        self.uploads.mkdir()

    def _restore(self):
        sys.path[:] = self.paths
        for name, module in self.modules.items():
            if module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module
        worker._modules.cache_clear()

    def junction(self, target, link):
        self.assertTrue(target.absolute().is_relative_to(self.directory.absolute()))
        self.assertTrue(link.absolute().is_relative_to(self.directory.absolute()))
        if sys.platform == "win32":
            import _winapi
            _winapi.CreateJunction(str(target), str(link))
        else:
            link.symlink_to(target, target_is_directory=True)
        self.addCleanup(lambda: link.rmdir() if sys.platform == "win32" else link.unlink())

    def test_availability_permission_error_e_generico(self):
        sentinel = "SENTINELA_NAO_EXIBIR"
        with mock.patch.object(Path, "is_file", side_effect=PermissionError(sentinel)):
            result = fase7.availability()
        self.assertEqual(result.status, "unavailable")
        self.assertNotIn(sentinel, repr(result.as_dict()))

    def test_adapter_recusa_junction_na_raiz_antes_de_escrever(self):
        outside = self.directory / "outside"
        outside.mkdir()
        link = self.directory / "redirected_uploads"
        self.junction(outside, link)
        with mock.patch.object(fase7, "UPLOAD_DIR", link), mock.patch.object(fase7, "run_json_worker", return_value=Result("ok", "simulado")) as run:
            result = fase7.evaluate_iot_csv(self.content)
        self.assertNotEqual(result.status, "ok")
        run.assert_not_called()
        self.assertEqual(list(outside.iterdir()), [])

    def test_adapter_recusa_junction_em_ancestral_antes_de_criar_pasta(self):
        outside = self.directory / "outside"
        outside.mkdir()
        link = self.directory / "runtime"
        self.junction(outside, link)
        with mock.patch.object(fase7, "UPLOAD_DIR", link / "fase7"), mock.patch.object(fase7, "run_json_worker", return_value=Result("ok", "simulado")) as run:
            result = fase7.evaluate_iot_csv(self.content)
        self.assertNotEqual(result.status, "ok")
        run.assert_not_called()
        self.assertFalse((outside / "fase7").exists())

    def test_worker_recusa_junction_na_raiz_de_upload(self):
        outside = self.directory / "outside"
        outside.mkdir()
        link = self.directory / "redirected_uploads"
        self.junction(outside, link)
        token = "a" * 32
        (outside / f"upload-{token}.csv").write_bytes(self.content)
        with mock.patch.object(worker, "UPLOAD_DIR", link):
            result = worker.handle({"operation": "evaluate_iot_csv", "upload_id": token})
        self.assertEqual(result.status, "invalid")

    def test_worker_recusa_junction_em_ancestral_do_historico(self):
        outside = self.directory / "outside"
        outside.mkdir()
        (outside / "history.csv").write_bytes(self.content)
        link = self.directory / "dados"
        self.junction(outside, link)
        with mock.patch.object(worker, "HISTORY_CSV", link / "history.csv"):
            result = worker.handle({"operation": "evaluate_iot_csv"})
        self.assertEqual(result.status, "invalid")

    def test_cleanup_nao_exclui_arquivo_apos_raiz_ser_redirecionada(self):
        outside = self.directory / "outside"
        outside.mkdir()
        moved = self.directory / "original_uploads"
        evidence = {}

        def run(phase, payload, **kwargs):
            self.uploads.rename(moved)
            self.junction(outside, self.uploads)
            victim = outside / f"upload-{payload['upload_id']}.csv"
            victim.write_bytes(b"arquivo de terceiro preservado")
            evidence["victim"] = victim
            return Result("ok", "simulado")

        with mock.patch.object(fase7, "UPLOAD_DIR", self.uploads), mock.patch.object(fase7, "run_json_worker", side_effect=run):
            result = fase7.evaluate_iot_csv(self.content)
        self.assertEqual(result.status, "error")
        self.assertEqual(evidence["victim"].read_bytes(), b"arquivo de terceiro preservado")

    def test_leitura_limitada_rejeita_fonte_crescente_apos_stat(self):
        large = (self.header + self.row * ((worker.MAX_CSV_BYTES // len(self.row)) + 2)).encode()
        original_stat = Path.stat
        swapped = [False]

        def stat(path, *args, **kwargs):
            result = original_stat(path, *args, **kwargs)
            if path == self.source and not swapped[0]:
                swapped[0] = True
                self.source.write_bytes(large)
            return result

        with mock.patch.object(worker, "HISTORY_CSV", self.source), mock.patch.object(worker, "UPLOAD_DIR", self.uploads), mock.patch.object(Path, "stat", stat):
            result = worker.handle({"operation": "evaluate_iot_csv"})
        self.assertTrue(swapped[0])
        self.assertEqual(result.status, "invalid")
        self.assertEqual(list(self.uploads.iterdir()), [])

    def test_read_bounded_maximo_mais_um_sem_confiar_no_stat(self):
        large = (self.header + self.row * ((worker.MAX_CSV_BYTES // len(self.row)) + 2)).encode()
        requests = []

        class Stream(io.BytesIO):
            def read(self, size=-1):
                requests.append(size)
                return super().read(size)

        original_open = Path.open

        def open_file(path, *args, **kwargs):
            if path == self.source and args and args[0] == "rb":
                return Stream(large)
            return original_open(path, *args, **kwargs)

        with mock.patch.object(worker, "HISTORY_CSV", self.source), mock.patch.object(worker, "UPLOAD_DIR", self.uploads), mock.patch.object(Path, "open", open_file):
            result = worker.handle({"operation": "evaluate_iot_csv"})
        self.assertEqual(result.status, "invalid")
        self.assertEqual(requests, [worker.MAX_CSV_BYTES + 1])

    def test_parser_recebe_snapshot_proprio_e_nao_fonte_mutavel(self):
        sensors = worker._modules()[0]
        parse = sensors.ler_leitura_csv
        snapshots = []

        def parse_snapshot(path, **kwargs):
            path = Path(path)
            self.assertNotEqual(path, self.source)
            self.assertEqual(path.parent, self.uploads)
            self.assertEqual(path.read_bytes(), self.content)
            snapshots.append(path)
            self.source.write_bytes(b"fonte temporaria mudou apos leitura")
            return parse(path, **kwargs)

        with mock.patch.object(worker, "HISTORY_CSV", self.source), mock.patch.object(worker, "UPLOAD_DIR", self.uploads), mock.patch.object(sensors, "ler_leitura_csv", side_effect=parse_snapshot):
            result = worker.handle({"operation": "evaluate_iot_csv"})
        self.assertEqual(result.status, "ok")
        self.assertEqual(result.data["reading"]["umidade"], 40)
        self.assertEqual(len(snapshots), 1)
        self.assertFalse(snapshots[0].exists())

    def test_snapshot_e_removido_quando_parser_recusa_conteudo(self):
        self.source.write_bytes(b"cabecalho errado\n")
        original = self.source.read_bytes()
        with mock.patch.object(worker, "HISTORY_CSV", self.source), mock.patch.object(worker, "UPLOAD_DIR", self.uploads):
            result = worker.handle({"operation": "evaluate_iot_csv"})
        self.assertEqual(result.status, "invalid")
        self.assertEqual(self.source.read_bytes(), original)
        self.assertEqual(list(self.uploads.iterdir()), [])

    def test_caminhos_normais_autorizados_e_cabecalho_original_funcionam(self):
        with mock.patch.object(worker, "HISTORY_CSV", self.source), mock.patch.object(worker, "UPLOAD_DIR", self.uploads):
            result = worker.handle({"operation": "evaluate_iot_csv"})
        self.assertEqual(result.status, "ok")
        self.assertEqual(result.data["reading"]["umidade"], 40)
        self.assertEqual(self.source.read_bytes(), self.content)
        self.assertEqual(list(self.uploads.iterdir()), [])

    def test_token_upload_recusa_paths_e_valores_nao_hexadecimais(self):
        for token in ("../history", "A" * 32, "a" * 31, "a" * 33, 123):
            with self.subTest(token=token):
                result = worker.handle({"operation": "evaluate_iot_csv", "upload_id": token})
                self.assertEqual(result.status, "invalid")


if __name__ == "__main__":
    unittest.main()
