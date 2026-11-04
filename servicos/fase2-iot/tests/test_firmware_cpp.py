"""C++ real extraido do firmware; descoberta sem compilador produz SKIP explicito.

Execute: python -X utf8 -m unittest discover -s tests -p test_firmware_cpp.py -v
Os testes de SourceExtractionTests verificam somente a extracao/inspecao textual.
FirmwareCppTests compila e executa nove cenarios, se houver compilador host.
Nao representa compilacao ESP32 completa, simulador ou teste fisico.
"""

import subprocess
import unittest

from firmware_host_harness import (
    CONSTANT_NAMES, FIRMWARE, FUNCTION_NAMES, build_source, compile_harness,
    extract_constant, extract_function, find_host_compiler, literal_snippets,
    numeric_constants, prepare_harness,
)


class SourceExtractionTests(unittest.TestCase):
    def test_current_source_is_embedded_literally(self):
        source = FIRMWARE.read_text(encoding="utf-8-sig")
        prepared = build_source(source)
        snippets = literal_snippets(source)
        self.assertEqual(len(snippets), len(CONSTANT_NAMES) + len(FUNCTION_NAMES))
        for snippet in snippets:
            self.assertIn(snippet, source)
            self.assertIn(snippet, prepared)

    def test_source_contains_independent_npk_condition_and_audited_thresholds(self):
        source = FIRMWARE.read_text(encoding="utf-8-sig")
        decision = extract_function(source, "decidirIrrigacaoTomate")
        self.assertRegex(decision, r"if\s*\(\s*!nutrientesAdequados\s*\|\|\s*!phOk\s*\)")
        self.assertRegex(decision, r"nutrientesAdequados\s*=\s*\(n\s*&&\s*p\s*&&\s*k\)")
        constants = numeric_constants(source)
        self.assertEqual((constants["UMIDADE_BAIXA_TOMATE"], constants["UMIDADE_ALTA_TOMATE"]), (45.0, 80.0))
        self.assertEqual((constants["PH_MIN_TOMATE"], constants["PH_MAX_TOMATE"]), (6.0, 6.8))

    def test_extraction_ignores_braces_in_comments_and_strings(self):
        function = 'float calcularPhBase(int x) { /* } */ const char* label = "}"; if (x) { return 1; } return 0; }'
        source = "// float calcularPhBase(int x) { }\n" + function + "\nbool other() { return false; }"
        self.assertEqual(extract_function(source, "calcularPhBase"), function)

    def test_missing_or_duplicate_source_definitions_fail(self):
        source = FIRMWARE.read_text(encoding="utf-8-sig")
        with self.assertRaises(ValueError):
            extract_function(source, "missingFunction")
        with self.assertRaises(ValueError):
            extract_function(source + "\n" + extract_function(source, FUNCTION_NAMES[0]), FUNCTION_NAMES[0])
        with self.assertRaises(ValueError):
            extract_constant(source + "\n" + extract_constant(source, CONSTANT_NAMES[0]), CONSTANT_NAMES[0])


class FirmwareCppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory, cls.cpp_path = prepare_harness()
        cls.compiler = find_host_compiler()
        print(f"\nTrechos C++ preparados em {cls.cpp_path}")
        if cls.compiler is not None:
            print(f"Compilador host: {cls.compiler}")
            cls.executable, cls.environment = compile_harness(cls.compiler, cls.directory, cls.cpp_path)

    def setUp(self):
        if self.compiler is None:
            self.skipTest("C++ host NAO EXECUTADO: nenhum g++/clang++/MSVC instalado localizado; fonte extraida, sem instalacao/download")

    def check_scenario(self, name):
        result = subprocess.run([str(self.executable), name], cwd=self.directory,
                                env=self.environment, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PASS C++ host: " + name, result.stdout)

    def test_01_isolated_n_missing(self):
        self.check_scenario("isolated_n_missing")

    def test_02_same_values_n_present(self):
        self.check_scenario("same_values_n_present")

    def test_03_corrected_ph_stays_ideal(self):
        self.check_scenario("corrected_ph_stays_ideal")

    def test_04_ph_outside_npk_full(self):
        self.check_scenario("ph_outside_npk_full")

    def test_05_moisture_boundaries(self):
        self.check_scenario("moisture_boundaries")

    def test_06_invalid_humidity(self):
        self.check_scenario("invalid_humidity")

    def test_07_ph_mapping_and_adjustments(self):
        self.check_scenario("ph_mapping_and_adjustments")

    def test_08_invalid_ph(self):
        self.check_scenario("invalid_ph")

    def test_09_other_nutrients_missing(self):
        self.check_scenario("other_nutrients_missing")


if __name__ == "__main__":
    unittest.main()
