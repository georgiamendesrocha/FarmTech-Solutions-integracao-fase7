"""MODELO Python da decisao, separado da execucao C++ e sem validade de campo.

Execute: python -X utf8 -m unittest discover -s tests -p test_firmware_model.py -v
Constantes sao lidas do .ino atual. A logica abaixo e uma especificacao Python;
aprovar estes testes NAO demonstra que o firmware C++ foi executado.
"""

import math
import unittest

from firmware_host_harness import FIRMWARE, numeric_constants


def decision_model(humidity, corrected_ph, n, p, k, constants):
    if not math.isfinite(humidity) or humidity < 0 or humidity > 100:
        return False
    if humidity > constants["UMIDADE_ALTA_TOMATE"]:
        return False
    if humidity < constants["UMIDADE_BAIXA_TOMATE"]:
        return True
    ideal_ph = math.isfinite(corrected_ph) and constants["PH_MIN_TOMATE"] <= corrected_ph <= constants["PH_MAX_TOMATE"]
    return not (n and p and k) or not ideal_ph


class PythonDecisionModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.constants = numeric_constants(FIRMWARE.read_text(encoding="utf-8-sig"))

    def test_model_isolates_absent_n_with_same_humidity_and_corrected_ph(self):
        self.assertTrue(decision_model(70.0, 6.3, False, True, True, self.constants))
        self.assertFalse(decision_model(70.0, 6.3, True, True, True, self.constants))

    def test_model_ph_base_6_6_remains_ideal_without_n(self):
        corrected = 6.6 - self.constants["AJUSTE_FALTA_N"]
        self.assertAlmostEqual(corrected, 6.3)
        self.assertTrue(self.constants["PH_MIN_TOMATE"] <= corrected <= self.constants["PH_MAX_TOMATE"])
        self.assertTrue(decision_model(70.0, corrected, False, True, True, self.constants))

    def test_model_outside_ph_with_full_npk_and_other_absent_nutrients(self):
        for ph in (5.9, 6.9):
            self.assertTrue(decision_model(70.0, ph, True, True, True, self.constants))
        self.assertTrue(decision_model(70.0, 6.3, True, False, True, self.constants))
        self.assertTrue(decision_model(70.0, 6.3, True, True, False, self.constants))

    def test_model_moisture_boundaries_and_non_finite_values(self):
        self.assertTrue(decision_model(44.99, 6.3, True, True, True, self.constants))
        for humidity in (45.0, 80.0):
            self.assertFalse(decision_model(humidity, 6.3, True, True, True, self.constants))
            self.assertTrue(decision_model(humidity, 6.3, False, True, True, self.constants))
        for humidity in (80.01, -1.0, 101.0, math.nan, math.inf):
            self.assertFalse(decision_model(humidity, 6.3, False, True, True, self.constants))
        self.assertTrue(decision_model(70.0, math.nan, True, True, True, self.constants))


if __name__ == "__main__":
    unittest.main()
