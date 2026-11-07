"""Condições simultâneas e legibilidade sem mudar a prioridade do serviço."""

from datetime import datetime, timezone
from itertools import product
from pathlib import Path
import sys
import unittest

PASTA = Path(__file__).resolve().parent
if str(PASTA) not in sys.path:
    sys.path.insert(0, str(PASTA))

from mensagem import assunto, corpo
from regras import avaliar
from sensores import avaliar_sensor, condicoes_sensor

AGORA = datetime(2026, 11, 6, 12, tzinfo=timezone.utc)
RECOMENDACAO_METEO = "Verificar a umidade do solo e as necessidades da cultura antes de decidir pelo acionamento da irrigação."


def leitura(**alteracoes):
    return {
        "ts_iso": "2026-11-06T11:59:30Z", "t_rel_ms": 30000, "umidade": 60,
        "temp_c": 25, "ldr": 2223, "ph_base": 6.4, "ph_corr": 6.4,
        "N": 1, "P": 1, "K": 1, "bomba_fw": 0, **alteracoes,
    }


class CondicoesSimultaneasTest(unittest.TestCase):
    def test_caso_historico_alta_ph_e_npk_coexistem_sem_trocar_principal(self):
        dados = leitura(umidade=80.5, ph_base=5.347, ph_corr=5.147, N=1, P=0, K=1)
        original = dados.copy()
        principal_antes = avaliar_sensor(dados, agora=AGORA)
        condicoes = condicoes_sensor(dados)
        self.assertEqual([item["tipo"] for item in condicoes],
                         ["iot_umidade_alta", "iot_ph_fora_faixa", "iot_npk_ausente"])
        self.assertEqual([item["valor"] for item in condicoes], [80.5, 5.147, "1/0/1"])
        self.assertIn("P ausente", condicoes[2]["condicao"])
        self.assertEqual(principal_antes["tipo"], "iot_umidade_alta")
        self.assertEqual(principal_antes["bomba_esperada"], 0)
        self.assertEqual(avaliar_sensor(dados, agora=AGORA), principal_antes)
        self.assertEqual(dados, original)
        self.assertTrue(all(set(item) == {"tipo", "condicao", "valor", "limiar"} for item in condicoes))

    def test_prioridade_primaria_permanece_baixa_alta_ph_npk(self):
        for dados, esperado in ((leitura(umidade=40, ph_corr=7, N=0), "iot_umidade_baixa"),
                                (leitura(umidade=85, ph_corr=7, N=0), "iot_umidade_alta"),
                                (leitura(ph_corr=7, N=0), "iot_ph_fora_faixa"),
                                (leitura(N=0), "iot_npk_ausente")):
            with self.subTest(esperado=esperado):
                self.assertEqual(condicoes_sensor(dados)[0]["tipo"], esperado)
                self.assertEqual(avaliar_sensor(dados, agora=AGORA)["tipo"], esperado)

    def test_normais_e_limites_inclusivos_nao_geram_condicoes(self):
        for umidade, ph in product((45, 60, 80), (6.0, 6.4, 6.8)):
            with self.subTest(umidade=umidade, ph=ph):
                self.assertEqual(condicoes_sensor(leitura(umidade=umidade, ph_corr=ph)), [])
        self.assertEqual(condicoes_sensor(leitura(temp_c=-40, bomba_fw=1)), [])

    def test_npk_nomeia_ausencias_e_mantem_valor_de_presenca(self):
        for flags in product((0, 1), repeat=3):
            with self.subTest(flags=flags):
                condicoes = condicoes_sensor(leitura(**dict(zip(("N", "P", "K"), flags))))
                if flags == (1, 1, 1):
                    self.assertEqual(condicoes, [])
                    continue
                self.assertEqual(len(condicoes), 1)
                self.assertEqual(condicoes[0]["tipo"], "iot_npk_ausente")
                self.assertEqual(condicoes[0]["valor"], "/".join(map(str, flags)))
                for campo, valor in zip(("N", "P", "K"), flags):
                    if valor == 0:
                        self.assertIn(f"{campo} ausente", condicoes[0]["condicao"])
                self.assertIn("presença didática", condicoes[0]["limiar"])

    def test_condicoes_validam_contrato_sem_modificar_entradas(self):
        for dados in (None, {}, leitura(umidade=True), leitura(ph_corr=15), leitura(P=2),
                      leitura(N=False), leitura(temp_c=float("nan")), leitura(ts_iso="sem data")):
            with self.subTest(dados=dados), self.assertRaises(ValueError):
                condicoes_sensor(dados)


class MensagensLegiveisTest(unittest.TestCase):
    def test_baixa_meteorologica_recomenda_verificacao_sem_mudar_limiar_ou_assunto(self):
        alerta = avaliar([{"ts_iso": "2026-11-06T13:00:00Z", "umidade": 40, "rain_mm": 0}], agora=AGORA)
        self.assertEqual(alerta["tipo"], "umidade_baixa")
        self.assertEqual(alerta["acao"], RECOMENDACAO_METEO)
        self.assertEqual(assunto(alerta), "FarmTech: " + alerta["alerta"])
        texto = corpo(alerta, {"name": "Irecê", "admin1": "Bahia", "country": "Brasil"})
        self.assertIn("\n\nAlerta: " + alerta["alerta"], texto)
        self.assertIn("\n\nAção corretiva: " + RECOMENDACAO_METEO, texto)
        self.assertIn("\n\nFonte: previsão da Fase 2 (Open-Meteo)", texto)
        self.assertIn("\n\nRegra acadêmica: a previsão não mede a umidade do solo.", texto)
        self.assertIn("Horário UTC do evento: 2026-11-06T13:00:00Z", texto)
        self.assertIn("Umidade relativa do ar prevista: 40.0%", texto)
        self.assertIn("Confirme as condições do solo e do cultivo antes de acionar a irrigação.", texto)
        self.assertNotIn("Ligar a irrigação do tomate.", texto)

    def test_corpo_iot_agrupa_contexto_tempo_dados_acao_e_limites_sem_remover_textos(self):
        alerta = avaliar_sensor(leitura(umidade=80.5, ph_corr=5.147, P=0), origem="wokwi", agora=AGORA)
        texto = corpo(alerta, {"name": "Irecê", "iot_dispositivo": "ESP32-a"})
        for inicio in ("Local declarado:", "Fonte: CSV", "Horário original", "Alerta:",
                       "Umidade do DHT22", "Ação recomendada:", "Critérios didáticos:", "Sem calibração"):
            with self.subTest(inicio=inicio):
                self.assertIn("\n\n" + inicio, texto)
        for conteudo in ("Dispositivo declarado: ESP32-a", "Simulação de sensores no Wokwi",
                         "não é medição física", "até cinco minutos", "não comprova nova aquisição válida no DHT22",
                         "Idade do registro: 30 segundos.", "Tempo relativo do firmware: 30000 ms",
                         "Temperatura ambiente registrada: 25.0 °C; sem regra de alerta",
                         "pH base simulado: 6.400; pH corrigido simulado: 5.147",
                         "Indicadores N/P/K dos botões: 1/0/1", "não são concentrações",
                         "Estado registrado da bomba no firmware: 0", "Estado esperado pela regra didática do firmware: desligada",
                         alerta["alerta"], alerta["acao"], "LDR e botões não medem pH ou nutrientes reais.",
                         "não envia comandos nem aciona uma bomba física."):
            with self.subTest(conteudo=conteudo):
                self.assertIn(conteudo, texto)
        self.assertIn("SIMULAÇÃO WOKWI", assunto(alerta))
        self.assertLessEqual(len(assunto(alerta)), 100)
        self.assertNotIn("<html", texto.lower())


if __name__ == "__main__":
    unittest.main()
