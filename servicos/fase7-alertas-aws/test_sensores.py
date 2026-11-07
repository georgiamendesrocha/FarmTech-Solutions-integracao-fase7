"""Testes locais do contrato CSV e alertas IoT, sem serial, rede ou AWS."""

import csv
import io
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

PASTA = Path(__file__).resolve().parent
if str(PASTA) not in sys.path:
    sys.path.insert(0, str(PASTA))

from sensores import CAMPOS_CSV, MARCADOR_EXEMPLO, TIPOS_IOT, avaliar_sensor, ler_leitura_csv

AGORA = datetime(2026, 11, 6, 12, tzinfo=timezone.utc)


def leitura(**alteracoes):
    dados = {
        "ts_iso": "2026-11-06T11:59:30Z", "t_rel_ms": 30000, "umidade": 60,
        "temp_c": 25, "ldr": 2222, "ph_base": 6.4, "ph_corr": 6.4,
        "N": 1, "P": 1, "K": 1, "bomba_fw": 0,
    }
    return {**dados, **alteracoes}


def conteudo_csv(linhas, *, marcador=False, campos=CAMPOS_CSV):
    saida = io.StringIO(newline="")
    if marcador:
        saida.write(MARCADOR_EXEMPLO + "\n")
    writer = csv.writer(saida, lineterminator="\n")
    writer.writerow(campos)
    for linha in linhas:
        writer.writerow([linha[campo] for campo in campos])
    return saida.getvalue()


class CsvSensorTest(unittest.TestCase):
    def ler(self, texto, **kwargs):
        with tempfile.TemporaryDirectory() as pasta:
            caminho = Path(pasta) / "captura.csv"
            caminho.write_text(texto, encoding="utf-8")
            antes = caminho.read_bytes()
            resultado = ler_leitura_csv(caminho, **kwargs)
            self.assertEqual(caminho.read_bytes(), antes)
            return resultado

    def test_cabecalho_autentico_de_onze_campos(self):
        self.assertEqual(CAMPOS_CSV, ("ts_iso", "t_rel_ms", "umidade", "temp_c", "ldr",
                                      "ph_base", "ph_corr", "N", "P", "K", "bomba_fw"))

    def test_normaliza_numeros_e_preserva_timestamp_original(self):
        dados = self.ler(conteudo_csv([leitura(ts_iso="2026-11-06T08:59:30-03:00")]))
        self.assertEqual(dados["ts_iso"], "2026-11-06T11:59:30Z")
        self.assertEqual(dados["_ts_original"], "2026-11-06T08:59:30-03:00")
        self.assertIs(dados["_sintetico"], False)
        self.assertIs(type(dados["umidade"]), float)
        self.assertIs(type(dados["ldr"]), int)
        self.assertIs(type(dados["N"]), int)

    def test_naive_exige_fuso_explicito(self):
        texto = conteudo_csv([leitura(ts_iso="2026-11-06T08:59:30")])
        with self.assertRaisesRegex(ValueError, "fuso-iot"):
            self.ler(texto)
        self.assertEqual(self.ler(texto, fuso="-03:00")["ts_iso"], "2026-11-06T11:59:30Z")
        self.assertEqual(self.ler(texto, fuso="UTC")["ts_iso"], "2026-11-06T08:59:30Z")
        self.assertEqual(self.ler(texto, fuso="+01:00")["ts_iso"], "2026-11-06T07:59:30Z")

    def test_fuso_explicito_da_linha_prevalece_sobre_padrao(self):
        self.assertEqual(self.ler(conteudo_csv([leitura()]), fuso="-03:00")["ts_iso"],
                         "2026-11-06T11:59:30Z")

    def test_fusos_invalidos_sao_rejeitados(self):
        for fuso in ("America/Bahia", "-3:00", "+24:00", "+03:60", "", 3, True):
            with self.subTest(fuso=fuso), self.assertRaises(ValueError):
                self.ler(conteudo_csv([leitura()]), fuso=fuso)

    def test_seleciona_mais_recente_independente_da_ordem(self):
        anterior = leitura(ts_iso="2026-11-06T11:58:00Z", umidade=40)
        atual = leitura(umidade=85)
        for linhas in ([atual, anterior], [anterior, atual]):
            with self.subTest(linhas=linhas):
                self.assertEqual(self.ler(conteudo_csv(linhas))["umidade"], 85)

    def test_repeticoes_identicas_sao_permitidas(self):
        dados = self.ler(conteudo_csv([leitura(), leitura(ts_iso="2026-11-06T08:59:30-03:00")]))
        self.assertEqual(dados["umidade"], 60)

    def test_mesmo_timestamp_e_contador_conflitantes_sao_rejeitados_inclusive_antigos(self):
        for linhas in ([leitura(), leitura(umidade=40)],
                       [leitura(), leitura(umidade=40), leitura(ts_iso="2026-11-06T12:00:00Z")]):
            with self.subTest(linhas=linhas), self.assertRaisesRegex(ValueError, "conflitantes"):
                self.ler(conteudo_csv(linhas))

    def test_tres_leituras_no_mesmo_segundo_usam_ultima_linha(self):
        linhas = [leitura(t_rel_ms=1000, umidade=40), leitura(t_rel_ms=1200, umidade=60),
                  leitura(t_rel_ms=1400, umidade=85)]
        atual = self.ler(conteudo_csv(linhas))
        self.assertEqual(atual["umidade"], 85)
        self.assertEqual(atual["t_rel_ms"], 1400)

    def test_desempate_nao_usa_maior_contador_que_pode_reiniciar(self):
        linhas = [leitura(t_rel_ms=4294967295, umidade=85), leitura(t_rel_ms=0, umidade=40)]
        atual = self.ler(conteudo_csv(linhas))
        self.assertEqual(atual["umidade"], 40)
        self.assertEqual(atual["t_rel_ms"], 0)

    def test_desempate_compara_instante_utc_mesmo_com_offsets_distintos(self):
        linhas = [leitura(t_rel_ms=30000, umidade=40),
                  leitura(ts_iso="2026-11-06T08:59:30-03:00", t_rel_ms=30200, umidade=85)]
        self.assertEqual(self.ler(conteudo_csv(linhas))["umidade"], 85)

    def test_conflito_do_mesmo_par_e_rejeitado_mesmo_com_outra_leitura_entre_elas(self):
        linhas = [leitura(t_rel_ms=1000, umidade=40), leitura(t_rel_ms=1200, umidade=60),
                  leitura(t_rel_ms=1000, umidade=85)]
        with self.assertRaisesRegex(ValueError, "timestamp e t_rel_ms"):
            self.ler(conteudo_csv(linhas))

    def test_marcador_sintetico_somente_na_primeira_linha(self):
        self.assertIs(self.ler(conteudo_csv([leitura()], marcador=True))["_sintetico"], True)
        texto = conteudo_csv([leitura()]) + MARCADOR_EXEMPLO + "\n"
        with self.assertRaises(ValueError):
            self.ler(texto)

    def test_csv_vazio_sem_leituras_ou_cabecalho_errado(self):
        for texto in ("", conteudo_csv([]), MARCADOR_EXEMPLO + "\n", "ts_iso,umidade\n",
                      conteudo_csv([leitura()], campos=tuple(reversed(CAMPOS_CSV)))):
            with self.subTest(texto=texto), self.assertRaises(ValueError):
                self.ler(texto)

    def test_toda_linha_e_validada_mesmo_quando_antiga(self):
        ruim = leitura(ts_iso="2026-11-06T11:00:00Z", umidade="nan")
        with self.assertRaisesRegex(ValueError, "umidade"):
            self.ler(conteudo_csv([ruim, leitura()]))

    def test_linha_de_console_campos_extras_ausentes_e_vazia_sao_rejeitados(self):
        base = conteudo_csv([leitura()])
        for sufixo in ("=========== LEITURA ATUAL ===========\n", ",".join(["1"] * 12) + "\n",
                       ",".join(["1"] * 10) + "\n", "\n", '"campo sem fechamento\n'):
            with self.subTest(sufixo=sufixo), self.assertRaises(ValueError):
                self.ler(base + sufixo)

    def test_fim_parcial_recusa_recuo_mas_linha_completa_sem_newline_e_valida(self):
        base = conteudo_csv([leitura()])
        with self.assertRaisesRegex(ValueError, "quantidade de campos"):
            self.ler(base + "2026-11-06T12:00:00Z,30001,40")
        self.assertEqual(self.ler(base.rstrip("\n"))["ts_iso"], "2026-11-06T11:59:30Z")

    def test_timestamps_invalidos_sao_rejeitados(self):
        for ts in ("erro", "", "2026-11-06", "2026-02-30T11:59:00Z",
                   "0001-01-01T00:00:00+23:00"):
            with self.subTest(ts=ts), self.assertRaises(ValueError):
                self.ler(conteudo_csv([leitura(ts_iso=ts)]))

    def test_rejeita_numeros_nao_finitos_e_faixas_invalidas(self):
        invalidos = {"t_rel_ms": (-1, 4294967296, "1.5"), "umidade": (-1, 101),
                     "ldr": (-1, 4096, "1.5"), "ph_base": (-0.1, 14.1), "ph_corr": (-0.1, 14.1),
                     "N": ("0.0", -1, 2), "P": (2,), "K": (2,), "bomba_fw": (2,)}
        for campo in CAMPOS_CSV[1:]:
            valores = ("NaN", "inf", "-inf", "", "erro") + invalidos.get(campo, ())
            for valor in valores:
                with self.subTest(campo=campo, valor=valor), self.assertRaises(ValueError):
                    self.ler(conteudo_csv([leitura(**{campo: valor})]))

    def test_limites_validos_e_temperatura_sem_limiar_inventado(self):
        for dados in (leitura(t_rel_ms=0, umidade=0, ldr=0, ph_base=0, ph_corr=0, temp_c=-50),
                      leitura(t_rel_ms=4294967295, umidade=100, ldr=4095, ph_base=14, ph_corr=14, temp_c=100)):
            with self.subTest(dados=dados):
                self.assertEqual(self.ler(conteudo_csv([dados]))["temp_c"], dados["temp_c"])


class AvaliarSensorTest(unittest.TestCase):
    def avaliar(self, dados, **kwargs):
        return avaliar_sensor(dados, agora=AGORA, **kwargs)

    def test_normal_nao_alerta(self):
        self.assertIsNone(self.avaliar(leitura()))

    def test_umidade_limites_45_e_80_inclusivos_sao_normais(self):
        for umidade in (45, 80):
            with self.subTest(umidade=umidade):
                self.assertIsNone(self.avaliar(leitura(umidade=umidade)))

    def test_baixa_e_alta_com_prioridade_sobre_ph_e_npk(self):
        for umidade, tipo, bomba in ((0, "iot_umidade_baixa", 1), (44.99, "iot_umidade_baixa", 1),
                                     (80.01, "iot_umidade_alta", 0), (100, "iot_umidade_alta", 0)):
            with self.subTest(umidade=umidade):
                alerta = self.avaliar(leitura(umidade=umidade, ph_corr=10, N=0))
                self.assertEqual(alerta["tipo"], tipo)
                self.assertEqual(alerta["bomba_esperada"], bomba)

    def test_faixa_ph_inclusiva_e_fora_prioritaria_sobre_npk(self):
        for ph in (6.0, 6.8):
            with self.subTest(ph=ph):
                self.assertIsNone(self.avaliar(leitura(ph_corr=ph)))
        for ph in (0, 5.99, 6.81, 14):
            with self.subTest(ph=ph):
                alerta = self.avaliar(leitura(ph_corr=ph, N=0))
                self.assertEqual(alerta["tipo"], "iot_ph_fora_faixa")
                self.assertEqual(alerta["bomba_esperada"], 1)

    def test_npk_indicador_de_presenca_cada_botao_ausente(self):
        for campo in ("N", "P", "K"):
            with self.subTest(campo=campo):
                alerta = self.avaliar(leitura(**{campo: 0}))
                self.assertEqual(alerta["tipo"], "iot_npk_ausente")
                self.assertEqual(alerta["bomba_esperada"], 1)
                self.assertIn("não representam concentrações", alerta["acao"])

    def test_ph_e_npk_acionam_na_faixa_inclusiva_de_umidade(self):
        for umidade in (45, 80):
            for extra, tipo in (({"ph_corr": 7}, "iot_ph_fora_faixa"), ({"N": 0}, "iot_npk_ausente")):
                with self.subTest(umidade=umidade, extra=extra):
                    self.assertEqual(self.avaliar(leitura(umidade=umidade, **extra))["tipo"], tipo)

    def test_temperatura_e_bomba_observada_nao_criam_regras(self):
        self.assertIsNone(self.avaliar(leitura(temp_c=-40, bomba_fw=1)))

    def test_idade_maxima_de_cinco_minutos_inclusiva(self):
        dados = leitura(umidade=40, ts_iso="2026-11-06T11:55:00Z")
        self.assertEqual(self.avaliar(dados)["idade_segundos"], 300)
        dados["ts_iso"] = "2026-11-06T11:54:59Z"
        with self.assertRaisesRegex(ValueError, "historico-iot"):
            self.avaliar(dados)

    def test_futuro_e_rejeitado_mesmo_em_replay(self):
        for historico in (False, True):
            with self.subTest(historico=historico), self.assertRaisesRegex(ValueError, "futuro"):
                self.avaliar(leitura(ts_iso="2026-11-06T12:00:00.000001Z"), historico=historico)

    def test_replay_historico_nao_reescreve_timestamp(self):
        dados = leitura(umidade=40, ts_iso="2026-05-03T20:03:40-03:00")
        antes = dados.copy()
        alerta = self.avaliar(dados, historico=True)
        self.assertIs(alerta["historico"], True)
        self.assertEqual(alerta["instante"], "2026-05-03T23:03:40Z")
        self.assertEqual(alerta["leitura"]["_ts_original"], dados["ts_iso"])
        self.assertGreater(alerta["idade_segundos"], 300)
        self.assertEqual(dados, antes)

    def test_replay_e_indicado_mesmo_para_leitura_recente(self):
        self.assertIs(self.avaliar(leitura(umidade=40), historico=True)["historico"], True)

    def test_timestamps_naive_e_tipos_invalidos_sao_rejeitados(self):
        for dados in (None, {}, leitura(ts_iso="2026-11-06T11:59:30"), leitura(umidade=True)):
            with self.subTest(dados=dados), self.assertRaises(ValueError):
                self.avaliar(dados)
        for agora in (False, "agora", AGORA.replace(tzinfo=None)):
            with self.subTest(agora=agora), self.assertRaises(ValueError):
                avaliar_sensor(leitura(), agora=agora)

    def test_origens_e_historico_invalidos_sao_rejeitados(self):
        for origem in ("outro", None, []):
            with self.subTest(origem=origem), self.assertRaises(ValueError):
                self.avaliar(leitura(), origem=origem)
        with self.assertRaises(ValueError):
            self.avaliar(leitura(), historico="sim")

    def test_marcador_sintetico_forca_origem_exemplo(self):
        dados = {**leitura(umidade=40), "_sintetico": True}
        alerta = self.avaliar(dados, origem="esp32")
        self.assertIs(alerta["sintetico"], True)
        self.assertEqual(alerta["origem"], "exemplo")
        with self.assertRaises(ValueError):
            self.avaliar({**dados, "_sintetico": "sim"})

    def test_contrato_e_acao_didatica_sem_acionamento_fisico(self):
        alerta = self.avaliar(leitura(umidade=40), origem="wokwi")
        self.assertEqual(alerta["fonte"], "iot_fase2")
        self.assertEqual(alerta["origem"], "wokwi")
        self.assertIn(alerta["tipo"], TIPOS_IOT)
        self.assertIs(alerta["historico"], False)
        self.assertIs(alerta["sintetico"], False)
        self.assertIn("Não acionar bomba física", alerta["acao"])
        self.assertNotIn("chuva_mm", alerta)
        self.assertNotIn("rain_mm", alerta["leitura"])


if __name__ == "__main__":
    unittest.main()
