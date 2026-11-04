"""Testes offline: serial simulada, arquivos temporários dentro do repositório."""

import contextlib
import io
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from scripts import serial_grava_csv as capture


ROW = b"CSV_ROW,30000,55.00,25.00,2048,7.000,6.300,0,0,0,1\n"


class SerialError(Exception):
    pass


class CaptureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix=".tmp_py_", dir=Path(__file__).parent)
        self.addCleanup(self.temp.cleanup)
        self.out = Path(self.temp.name) / "history.csv"

    def run_capture(self, chunks, port="COM6", extra=(), open_error=None):
        device = Mock()
        device.readline.side_effect = list(chunks) + [KeyboardInterrupt()]
        serial = types.SimpleNamespace(SerialException=SerialError, serial_for_url=Mock(return_value=device))
        if open_error is not None:
            serial.serial_for_url.side_effect = open_error
        argv = ["serial_grava_csv.py", "--port", port, "--out", str(self.out), *extra]
        with patch.dict(sys.modules, {"serial": serial}), patch.object(sys, "argv", argv):
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                code = capture.main()
        return code, serial, device

    def test_com_and_rfc2217_append_without_duplicate_header(self):
        for port in ("COM6", "rfc2217://127.0.0.1:4000"):
            code, serial, device = self.run_capture([ROW], port=port)
            self.assertEqual(code, 0)
            serial.serial_for_url.assert_called_once_with(port, baudrate=115200, timeout=0.5)
            device.close.assert_called_once()
        lines = self.out.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 3)
        self.assertEqual(lines[0], capture.CSV_HEADER_OUT.strip())
        self.assertEqual(len(lines[1].split(",")), 11)

    def test_partial_reads_and_invalid_rows(self):
        chunks = [b"CSV_HDR,ignored\n", b"debug\n", ROW[:20], b"", ROW[20:],
                  ROW.replace(b"55.00", b"nan"), ROW.replace(b"25.00", b"=1+1"),
                  b"CSV_ROW,missing,fields\n", ROW.replace(b",0,0,0,1", b",0,0,2,1")]
        code, _, _ = self.run_capture(chunks)
        self.assertEqual(code, 0)
        self.assertEqual(len(self.out.read_text().splitlines()), 2)

    def test_oversize_line_is_discarded_until_newline(self):
        code, _, _ = self.run_capture([b"CSV_ROW," + b"1" * 4096, b"rest\n", ROW])
        self.assertEqual(code, 0)
        self.assertEqual(len(self.out.read_text().splitlines()), 2)

    def test_disconnect_closes_and_keeps_flushed_row(self):
        code, _, device = self.run_capture([ROW, SerialError("connection lost")])
        self.assertEqual(code, 3)
        device.close.assert_called_once()
        self.assertEqual(len(self.out.read_text().splitlines()), 2)

    def test_failed_connection_does_not_truncate_even_with_fresh(self):
        self.out.write_text("existing evidence\n", encoding="utf-8")
        code, _, _ = self.run_capture([], extra=("--fresh",), open_error=SerialError("refused"))
        self.assertEqual(code, 2)
        self.assertEqual(self.out.read_text(), "existing evidence\n")

    def test_incompatible_header_is_preserved(self):
        self.out.write_text("different,header\n", encoding="utf-8")
        code, serial, _ = self.run_capture([ROW])
        self.assertEqual(code, 4)
        serial.serial_for_url.assert_not_called()
        self.assertEqual(self.out.read_text(), "different,header\n")

    def test_output_directory_is_rejected_before_connecting(self):
        self.out.mkdir()
        code, serial, _ = self.run_capture([])
        self.assertEqual(code, 4)
        serial.serial_for_url.assert_not_called()

    def test_output_write_error_closes_serial(self):
        with patch.object(Path, "open", side_effect=OSError("write denied")):
            code, _, device = self.run_capture([])
        self.assertEqual(code, 4)
        device.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
