
import sys
import unittest
from io import StringIO
from pathlib import Path
from contextlib import redirect_stdout

# Permite importar as funções da pasta src.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from farm import dose_ha_para_por_metro, calcular_insumos_talhao


class TestInsumos(unittest.TestCase):

    def test_conversao_litros_para_mililitros(self):
        resultado = dose_ha_para_por_metro(0.75, "L/ha", 0.5)
        self.assertAlmostEqual(resultado, 0.0375)

    def test_conversao_quilogramas_para_gramas(self):
        resultado = dose_ha_para_por_metro(2, "kg/ha", 0.5)
        self.assertAlmostEqual(resultado, 0.1)

    def test_espacamento_diferente(self):
        resultado = dose_ha_para_por_metro(2, "kg/ha", 1.0)
        self.assertAlmostEqual(resultado, 0.2)

    def test_dose_zero(self):
        resultado = dose_ha_para_por_metro(0, "L/ha", 0.5)
        self.assertEqual(resultado, 0)

    def obter_saida_insumos(self):
        buffer = StringIO()
        with redirect_stdout(buffer):
            calcular_insumos_talhao("Soja", 0.02)
        return buffer.getvalue()

    def test_quantidade_curbix(self):
        saida = self.obter_saida_insumos()
        self.assertIn("0.0150 L", saida)

    def test_custo_curbix(self):
        saida = self.obter_saida_insumos()
        self.assertIn("Total: R$ 4.80", saida)

    def test_classificacao_menor_custo(self):
        saida = self.obter_saida_insumos()
        self.assertIn("MENOR CUSTO ESTIMADO", saida)
        self.assertNotIn("MELHOR CUSTO-BENEFÍCIO", saida)


if __name__ == "__main__":
    unittest.main()
