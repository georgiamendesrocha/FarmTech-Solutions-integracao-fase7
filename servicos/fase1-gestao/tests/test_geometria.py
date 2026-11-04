
import math
import sys
import unittest
from pathlib import Path

# Permite importar o módulo farm.py da pasta src.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from farm import calcular_area


class TestGeometria(unittest.TestCase):

    def test_pentagono(self):
        esperado = 172.0477400589
        self.assertAlmostEqual(calcular_area(5, [10] * 5), esperado, places=4)

    def test_hexagono(self):
        esperado = 259.8076211353
        self.assertAlmostEqual(calcular_area(6, [10] * 6), esperado, places=4)

    def test_heptagono(self):
        esperado = 363.3912444002
        self.assertAlmostEqual(calcular_area(7, [10] * 7), esperado, places=4)

    def test_octogono(self):
        esperado = 482.8427124746
        self.assertAlmostEqual(calcular_area(8, [10] * 8), esperado, places=4)

    def test_medidas_decimais(self):
        esperado = 5 * (10.5 ** 2) / (4 * math.tan(math.pi / 5))
        self.assertAlmostEqual(calcular_area(5, [10.5] * 5), esperado)

    def test_lados_diferentes(self):
        with self.assertRaises(ValueError):
            calcular_area(5, [10, 10, 10, 10, 9])

    def test_medidas_zero(self):
        with self.assertRaises(ValueError):
            calcular_area(5, [0] * 5)

    def test_medidas_negativas(self):
        with self.assertRaises(ValueError):
            calcular_area(5, [-10] * 5)

    def test_numero_lados_nao_suportado(self):
        with self.assertRaises(ValueError):
            calcular_area(9, [10] * 9)


if __name__ == "__main__":
    unittest.main()
