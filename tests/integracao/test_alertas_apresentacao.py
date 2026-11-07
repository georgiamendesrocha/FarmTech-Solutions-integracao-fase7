"""Apresentação literal, condições coexistentes e invalidação definitiva da F7."""

import csv
from datetime import datetime, timedelta, timezone
import io
import unittest
from unittest.mock import patch

from farmtech_integracao import fase7
from farmtech_integracao.contracts import Result

try:
    from . import test_alertas_dashboard as suporte
except ImportError:
    import test_alertas_dashboard as suporte


INTRO = ("Consulte os dados dos sensores e as condições meteorológicas, identifique possíveis alertas "
         "e visualize as ações corretivas recomendadas. As análises são demonstrativas e não enviam notificações reais.")


class AlertasApresentacaoTests(unittest.TestCase):
    def setUp(self):
        # Composição: os dezessete testes da classe de apoio não são herdados
        # nem incluídos novamente na descoberta desta suíte dirigida.
        self.apoio = suporte.AlertasDashboardTests(methodName="runTest")
        self.apoio.setUp()
        self.addCleanup(self.apoio.doCleanups)

    def _resultado(self, *, body="Mensagem controlada de prévia.", subject="Assunto controlado"):
        return Result("ok", "Avaliação controlada", {
            "alert": {"tipo": "iot_umidade_baixa", "alerta": "Condição controlada", "acao": "Conferir os dados."},
            "has_alert": True, "subject": subject, "body": body, "reading": {}, "local": {},
            "preview_only": True, "sns_enabled": False, "mode": "demonstracao", "conditions": [],
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
            "forecast_retrieved_at": None, "forecast_event_at": None,
        }, {"origin": "exemplo", "synthetic": True, "historical": False, "provider": "Fixture local"})

    def _sem_previa(self, app):
        texto = self.apoio._texto(app)
        self.assertIn("A seleção foi alterada. Avalie novamente", texto)
        self.assertNotIn("Prévia da mensagem", texto)
        self.assertNotIn("Alerta principal", texto)

    def _dados(self, app):
        return app.session_state["fase7_preview_result"]["result"]["data"]

    def test_intro_literal_e_seletores_fora_de_formularios(self):
        app = self.apoio._abrir()
        self.assertIn(INTRO, self.apoio._texto(app))
        for chave in ("fase7_demo_source", "fase7_demo_case"):
            self.assertEqual(self.apoio._widget(app, "selectbox", chave).proto.form_id, "")
        self.apoio._escolher(app, "radio", "fase7_mode", "CSV IoT da Fase 2")
        for tipo, chave in (("selectbox", "fase7_origin"), ("selectbox", "fase7_timezone"),
                            ("checkbox", "fase7_history"), ("text_input", "fase7_local"),
                            ("text_input", "fase7_device")):
            self.assertEqual(self.apoio._widget(app, tipo, chave).proto.form_id, "")
        self.apoio._escolher(app, "radio", "fase7_mode", "Previsão Open-Meteo")
        self.assertEqual(self.apoio._widget(app, "text_input", "fase7_city").proto.form_id, "")
        self.assertTrue(all(not botao.proto.is_form_submitter for botao in app.button))
        self.apoio.execute.assert_not_called()
        self.apoio.forecast.assert_not_called()

    def test_previa_preserva_cada_paragrafo_origem_e_texto_literal(self):
        import streamlit as st
        body = ("Primeiro parágrafo: <script>alert(1)</script>.\nLinha preservada.\n\n"
                "Segundo parágrafo: **texto literal**, sem Markdown.\n\n"
                "Último parágrafo: <img src=x onerror=alert(1)>.")
        resultado = self._resultado(body=body)
        with patch.object(fase7, "demo_iot", return_value=resultado), \
                patch.object(st, "text", wraps=st.text) as render_texto:
            app = self.apoio._abrir()
            self.apoio._clicar(app, "Avaliar demonstração")
        textos = [elemento.value for elemento in app.text]
        indice = textos.index(resultado.data["subject"])
        paragrafos = textos[indice + 1:]
        self.assertEqual(paragrafos, body.split("\n\n"))
        self.assertEqual("\n\n".join(paragrafos), body)
        for chamada in render_texto.call_args_list:
            if chamada.args[0] in paragrafos:
                self.assertEqual(chamada.kwargs.get("width"), "stretch")
        self.assertIn("Origem: Exemplo sintético", self.apoio._texto(app))
        self.assertIn("Alerta principal", self.apoio._texto(app))
        self.assertTrue(all(not elemento.proto.allow_html for elemento in app.markdown
                            if "<script>" in elemento.value or "<img src=x" in elemento.value))
        self.apoio.execute.assert_not_called()
        self.apoio.forecast.assert_not_called()

    def test_umidade_alta_ph_e_npk_coexistentes_mantem_principal_e_tabela(self):
        saida = io.StringIO(newline="")
        writer = csv.writer(saida, lineterminator="\n")
        writer.writerow(("ts_iso", "t_rel_ms", "umidade", "temp_c", "ldr", "ph_base", "ph_corr", "N", "P", "K", "bomba_fw"))
        writer.writerow(((datetime.now(timezone.utc) - timedelta(days=90)).isoformat(),
                         30000, 80.5, 25, 2531, 5.347, 5.147, 1, 0, 1, 0))
        with self.apoio._upload(saida.getvalue().encode("utf-8")):
            app = self.apoio._modo_upload(self.apoio._abrir())
            self.apoio._clicar(app, "Avaliar CSV IoT")
        dados = self._dados(app)
        self.assertEqual(dados["alert"]["tipo"], "iot_umidade_alta")
        self.assertEqual(len(dados["conditions"]), 3)
        self.assertEqual(sum(bool(condicao["primary"]) for condicao in dados["conditions"]), 1)
        self.assertIn("Alerta principal", self.apoio._texto(app))
        self.assertIn("Demais condições detectadas", self.apoio._texto(app))
        self.assertEqual(len(app.table), 1)
        tabela = app.table[0].value
        self.assertEqual(list(tabela.columns), ["Condição", "Valor", "Critério didático"])
        self.assertEqual(len(tabela), 2)
        secundarios = [condicao for condicao in dados["conditions"] if not condicao["primary"]]
        self.assertEqual(list(tabela["Condição"]), [condicao["condicao"] for condicao in secundarios])
        self.assertEqual(list(tabela["Valor"]), [str(condicao["valor"]) for condicao in secundarios])
        self.assertEqual(len(app.dataframe), 0, "As demais condições devem usar tabela não editável")
        self.assertEqual(len(app.metric), 4)
        self.assertTrue(any(metrica.value == "1/0/1" for metrica in app.metric))
        self.apoio.forecast.assert_not_called()

    def test_mudar_e_voltar_modo_tipo_ou_cenario_nao_restaura_resultado(self):
        mudancas = (("radio", "fase7_mode", "CSV IoT da Fase 2"),
                    ("selectbox", "fase7_demo_source", "Previsão meteorológica"),
                    ("selectbox", "fase7_demo_case", "normal"))
        for tipo, chave, novo in mudancas:
            with self.subTest(chave=chave), patch.object(fase7, "demo_iot", return_value=self._resultado()) as avaliar:
                app = self.apoio._abrir()
                original = self.apoio._widget(app, tipo, chave).value
                self.apoio._clicar(app, "Avaliar demonstração")
                avaliar.assert_called_once()
                chamadas = self.apoio.execute.call_count
                self.apoio._escolher(app, tipo, chave, novo)
                self._sem_previa(app)
                self.apoio._escolher(app, tipo, chave, original)
                self._sem_previa(app)
                avaliar.assert_called_once()
                self.assertEqual(self.apoio.execute.call_count, chamadas)
                self.apoio._clicar(app, "Avaliar demonstração")
                self.assertEqual(avaliar.call_count, 2)
                self.assertIn("Prévia da mensagem", self.apoio._texto(app))
        self.apoio.forecast.assert_not_called()

    def test_mudar_e_voltar_metadados_csv_exige_nova_avaliacao_explicita(self):
        mudancas = (("selectbox", "fase7_origin", "wokwi"),
                    ("selectbox", "fase7_timezone", "UTC"),
                    ("checkbox", "fase7_history", False),
                    ("text_input", "fase7_local", "Outro local"),
                    ("text_input", "fase7_device", "Outro dispositivo"))
        for tipo, chave, novo in mudancas:
            with self.subTest(chave=chave), self.apoio._upload(self.apoio._csv()), \
                    patch.object(fase7, "evaluate_iot_csv", return_value=self._resultado()) as avaliar:
                app = self.apoio._modo_upload(self.apoio._abrir())
                original = self.apoio._widget(app, tipo, chave).value
                self.apoio._clicar(app, "Avaliar CSV IoT")
                avaliar.assert_called_once()
                self.apoio._escolher(app, tipo, chave, novo)
                self._sem_previa(app)
                self.apoio._escolher(app, tipo, chave, original)
                self._sem_previa(app)
                avaliar.assert_called_once()
                self.apoio._clicar(app, "Avaliar CSV IoT")
                self.assertEqual(avaliar.call_count, 2)
        self.apoio.forecast.assert_not_called()

    def test_mudar_e_voltar_cidade_nao_consulta_nem_restaura_previa(self):
        self.apoio.forecast.side_effect = None
        self.apoio.forecast.return_value = self.apoio._previsao()
        with patch.object(fase7, "evaluate_weather", return_value=self._resultado()) as avaliar:
            app = self.apoio._abrir()
            self.apoio._escolher(app, "radio", "fase7_mode", "Previsão Open-Meteo")
            self.apoio._clicar(app, "Solicitar previsão e avaliar")
            self.apoio.forecast.assert_called_once_with("Irecê")
            self.apoio._escolher(app, "text_input", "fase7_city", "Salvador")
            self._sem_previa(app)
            self.apoio._escolher(app, "text_input", "fase7_city", "Irecê")
            self._sem_previa(app)
            self.apoio.forecast.assert_called_once()
            avaliar.assert_called_once()
            self.apoio._clicar(app, "Solicitar previsão e avaliar")
            self.assertEqual(self.apoio.forecast.call_count, 2)
            self.assertEqual(avaliar.call_count, 2)

    def test_cenario_iot_exclusivo_reinicia_com_seguranca_ao_trocar_tipo(self):
        with patch.object(fase7, "demo_iot") as iot, patch.object(fase7, "demo_weather") as weather:
            app = self.apoio._abrir()
            self.apoio._escolher(app, "selectbox", "fase7_demo_case", "ph_fora_faixa")
            self.apoio._escolher(app, "selectbox", "fase7_demo_source", "Previsão meteorológica")
            caso = self.apoio._widget(app, "selectbox", "fase7_demo_case")
            self.assertIn(caso.value, {"chuva", "umidade_baixa", "umidade_alta", "normal"})
            self.assertNotEqual(caso.value, "ph_fora_faixa")
            iot.assert_not_called()
            weather.assert_not_called()
        self.apoio.forecast.assert_not_called()

    def test_tempos_consulta_avaliacao_e_evento_separados_sem_inventar_consulta(self):
        for modo in ("consulta_com_metadado", "consulta_sem_metadado", "demonstracao"):
            with self.subTest(modo=modo):
                app = self.apoio._abrir()
                if modo == "demonstracao":
                    self.apoio._escolher(app, "selectbox", "fase7_demo_source", "Previsão meteorológica")
                    self.apoio._clicar(app, "Avaliar demonstração")
                else:
                    previsao = self.apoio._previsao()
                    if modo == "consulta_sem_metadado":
                        previsao.source.pop("retrieved_at", None)
                    self.apoio.forecast.side_effect = None
                    self.apoio.forecast.return_value = previsao
                    self.apoio._escolher(app, "radio", "fase7_mode", "Previsão Open-Meteo")
                    self.apoio._clicar(app, "Solicitar previsão e avaliar")
                dados = self._dados(app)
                captions = [elemento.value for elemento in app.caption]
                consulta = next(texto for texto in captions if texto.startswith("Consulta à fonte:"))
                avaliacao = next(texto for texto in captions if texto.startswith("Avaliação local:"))
                evento = next(texto for texto in captions if texto.startswith("Evento meteorológico previsto:"))
                self.assertIn(dados["evaluated_at"], avaliacao)
                self.assertIn(dados["forecast_event_at"], evento)
                if modo == "consulta_com_metadado":
                    self.assertEqual(dados["forecast_retrieved_at"], previsao.source["retrieved_at"])
                    self.assertIn(previsao.source["retrieved_at"], consulta)
                else:
                    self.assertIsNone(dados["forecast_retrieved_at"])
                    self.assertIn("indisponível (metadado não fornecido)", consulta)
                    self.assertNotIn(dados["evaluated_at"], consulta)
        # Somente os dois cliques de consulta controlados chamaram a Fase 2.
        self.assertEqual(self.apoio.forecast.call_count, 2)


if __name__ == "__main__":
    unittest.main()
