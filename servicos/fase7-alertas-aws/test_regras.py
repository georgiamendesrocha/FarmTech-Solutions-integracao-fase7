"""Validação local das regras e mensagens; não consulta previsão nem AWS."""

import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

PASTA = Path(__file__).resolve().parent
if str(PASTA) not in sys.path:
    sys.path.insert(0, str(PASTA))

from mensagem import assunto, corpo
from regras import JANELA_HORAS, avaliar

AGORA = datetime(2026, 11, 6, 12, tzinfo=timezone.utc)


def leitura(*, umidade=60, chuva=0, instante=None):
    return {
        "ts_iso": (instante or AGORA + timedelta(hours=1)).isoformat(),
        "umidade": umidade,
        "rain_mm": chuva,
    }


class RegrasTest(unittest.TestCase):
    def avaliar(self, linhas, **kwargs):
        return avaliar(linhas, agora=AGORA, **kwargs)

    def test_janela_padrao_de_doze_horas(self):
        self.assertEqual(JANELA_HORAS, 12)
        alerta = self.avaliar([leitura(umidade=44, instante=AGORA + timedelta(hours=11))])
        self.assertEqual(alerta["tipo"], "umidade_baixa")

    def test_limite_inferior_inclusivo_e_superior_exclusivo(self):
        self.assertIsNotNone(self.avaliar([leitura(umidade=44, instante=AGORA)]))
        self.assertIsNone(self.avaliar([leitura(umidade=44, instante=AGORA + timedelta(hours=12))]))

    def test_ultima_fracao_da_janela_e_considerada(self):
        instante = AGORA + timedelta(hours=12) - timedelta(microseconds=1)
        self.assertIsNotNone(self.avaliar([leitura(umidade=44, instante=instante)]))

    def test_previsao_desatualizada_e_futura_distante_nao_alertam(self):
        for delta in (timedelta(seconds=-1), timedelta(days=-2), timedelta(days=2)):
            with self.subTest(delta=delta):
                self.assertIsNone(self.avaliar([leitura(umidade=40, instante=AGORA + delta)]))

    def test_limites_estritos_de_umidade(self):
        for umidade, esperado in ((0, "umidade_baixa"), (44.99, "umidade_baixa"),
                                  (45, None), (60, None), (80, None),
                                  (80.01, "umidade_alta"), (100, "umidade_alta")):
            with self.subTest(umidade=umidade):
                alerta = self.avaliar([leitura(umidade=umidade)])
                self.assertEqual(alerta["tipo"] if alerta else None, esperado)

    def test_chuva_de_um_milimetro_tem_prioridade(self):
        linhas = [leitura(umidade=40), leitura(umidade=85), leitura(chuva=1)]
        self.assertEqual(self.avaliar(linhas)["tipo"], "chuva")

    def test_chuva_horaria_nao_e_soma_da_janela(self):
        linhas = [leitura(chuva=0.6), leitura(chuva=0.6, instante=AGORA + timedelta(hours=2))]
        self.assertIsNone(self.avaliar(linhas))

    def test_chuva_abaixo_do_limiar_preserva_regra_de_umidade(self):
        self.assertEqual(self.avaliar([leitura(umidade=44, chuva=0.999)])["tipo"], "umidade_baixa")

    def test_baixa_tem_prioridade_sobre_alta_sem_chuva(self):
        self.assertEqual(self.avaliar([leitura(umidade=85), leitura(umidade=40)])["tipo"], "umidade_baixa")

    def test_utc_z_e_offset_representam_mesmo_instante(self):
        for texto in ("2026-11-06T13:00:00Z", "2026-11-06T10:00:00-03:00",
                      "2026-11-06T14:00:00+01:00"):
            with self.subTest(texto=texto):
                row = leitura(umidade=40)
                row["ts_iso"] = texto
                self.assertEqual(self.avaliar([row])["instante"], "2026-11-06T13:00:00Z")

    def test_timestamp_sem_fuso_mantem_convencao_utc(self):
        row = leitura(umidade=40)
        row["ts_iso"] = "2026-11-06T13:00:00"
        self.assertEqual(self.avaliar([row])["instante"], "2026-11-06T13:00:00Z")

    def test_referencia_com_offset_e_comparada_corretamente(self):
        referencia = AGORA.astimezone(timezone(timedelta(hours=-3)))
        alerta = avaliar([leitura(umidade=40)], agora=referencia)
        self.assertEqual(alerta["instante"], "2026-11-06T13:00:00Z")

    def test_referencia_sem_fuso_mantem_convencao_utc(self):
        alerta = avaliar([leitura(umidade=40)], agora=AGORA.replace(tzinfo=None))
        self.assertEqual(alerta["tipo"], "umidade_baixa")

    def test_timestamps_invalidos_e_overflow_sao_ignorados(self):
        for texto in (None, "", "erro", 123, "2026-02-30T00:00:00Z",
                      "0001-01-01T00:00:00+23:00", "9999-12-31T23:59:59-23:00"):
            with self.subTest(texto=texto):
                row = leitura(umidade=40)
                row["ts_iso"] = texto
                self.assertIsNone(self.avaliar([row]))

    def test_previsao_vazia(self):
        self.assertIsNone(self.avaliar([]))

    def test_registros_invalidos_e_campos_ausentes_sao_ignorados(self):
        self.assertIsNone(self.avaliar([None, 1, "erro", [], {}, {"ts_iso": "2026-11-06T13:00:00Z"}]))

    def test_tipo_da_serie_invalido_e_rejeitado(self):
        for serie in (None, {}, "erro", (), 1):
            with self.subTest(serie=serie), self.assertRaises(ValueError):
                self.avaliar(serie)

    def test_janelas_invalidas_incluindo_booleanos_sao_rejeitadas(self):
        for horas in (0, -1, 49, 12.0, "12", None, True, False):
            with self.subTest(horas=horas), self.assertRaises(ValueError):
                self.avaliar([], horas=horas)

    def test_limites_permitidos_de_janela(self):
        for horas in (1, 48):
            with self.subTest(horas=horas):
                self.assertIsNone(self.avaliar([], horas=horas))

    def test_tipo_da_referencia_invalido_e_rejeitado(self):
        for referencia in ("2026-11-06", 0, False):
            with self.subTest(referencia=referencia), self.assertRaises(ValueError):
                avaliar([], agora=referencia)

    def test_umidade_invalida_nao_gera_alerta(self):
        valores = (None, "40", True, False, -1, 101, float("nan"),
                   float("inf"), -float("inf"), 10 ** 1000)
        for valor in valores:
            with self.subTest(valor=valor):
                self.assertIsNone(self.avaliar([leitura(umidade=valor)]))

    def test_chuva_invalida_nao_gera_alerta(self):
        valores = (None, "2", True, False, -1, float("nan"),
                   float("inf"), -float("inf"), 10 ** 1000)
        for valor in valores:
            with self.subTest(valor=valor):
                self.assertIsNone(self.avaliar([leitura(chuva=valor)]))

    def test_chuva_valida_independe_de_umidade_ausente(self):
        alerta = self.avaliar([leitura(umidade=None, chuva=1)])
        self.assertEqual(alerta["tipo"], "chuva")
        self.assertIsNone(alerta["umidade"])

    def test_campo_ausente_nao_muda_a_regra_existente_de_umidade(self):
        alerta = self.avaliar([leitura(umidade=40, chuva=None)])
        self.assertEqual(alerta["tipo"], "umidade_baixa")

    def test_contrato_do_alerta_e_acoes_academicas_preservados(self):
        for row, acao in ((leitura(umidade=40), "Verificar a umidade do solo e as necessidades da cultura antes de decidir pelo acionamento da irrigação."),
                          (leitura(umidade=85), "Manter a bomba de irrigação desligada."),
                          (leitura(chuva=1), "Manter a bomba de irrigação desligada.")):
            with self.subTest(row=row):
                alerta = self.avaliar([row])
                self.assertEqual(set(alerta), {"tipo", "instante", "chuva_mm", "umidade", "alerta", "acao"})
                self.assertEqual(alerta["acao"], acao)


class MensagemTest(unittest.TestCase):
    def setUp(self):
        self.local = {"name": "Irecê", "admin1": "Bahia", "country": "Brasil"}

    def test_mensagem_identifica_ar_utc_e_acao(self):
        alerta = avaliar([leitura(umidade=40)], agora=AGORA)
        texto = corpo(alerta, self.local)
        self.assertIn("Irecê, Bahia, Brasil", texto)
        self.assertIn("Horário UTC do evento: 2026-11-06T13:00:00Z", texto)
        self.assertIn("Umidade relativa do ar prevista: 40.0%", texto)
        self.assertIn("Ação corretiva: Verificar a umidade do solo e as necessidades da cultura antes de decidir pelo acionamento da irrigação.", texto)
        self.assertIn("não mede a umidade do solo", texto)
        self.assertIn("Confirme as condições do solo", texto)

    def test_chuva_horaria_e_umidade_ausente(self):
        alerta = avaliar([leitura(umidade=None, chuva=1)], agora=AGORA)
        texto = corpo(alerta, self.local)
        self.assertIn("Chuva prevista na hora do evento: 1.0 mm", texto)
        self.assertNotIn("Umidade relativa do ar prevista:", texto)

    def test_local_ausente_usa_fallback(self):
        alerta = avaliar([leitura(umidade=40)], agora=AGORA)
        self.assertIn("Local: local não informado", corpo(alerta, {}))

    def test_assunto_e_limitado_a_cem_caracteres(self):
        self.assertEqual(assunto({"alerta": "x" * 200}), "FarmTech: " + "x" * 90)
        self.assertEqual(len(assunto({"alerta": "x" * 200})), 100)


if __name__ == "__main__":
    unittest.main()
