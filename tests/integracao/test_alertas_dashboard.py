"""Página de alertas com regras reais, entradas controladas e AWS indisponível."""

import contextlib
import csv
import io
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from datetime import datetime, timedelta, timezone

from farmtech_integracao import fase2, fase7, runtime
from farmtech_integracao.contracts import Result


class AlertasDashboardTests(unittest.TestCase):
    def setUp(self):
        self.guards = contextlib.ExitStack()
        self.addCleanup(self.guards.close)
        self.temp = self.guards.enter_context(tempfile.TemporaryDirectory())
        self.guards.enter_context(patch.dict(os.environ, {
            "FARMTECH_INTEGRACAO": "1", "FARMTECH_SIMULACAO": "0",
            "DB_PATH": str(Path(self.temp) / "nao_criar.db"),
            "AWS_SNS_TOPIC_ARN": "arn:aws:sns:sa-east-1:000000000000:nao-publicar",
            "AWS_DEFAULT_REGION": "sa-east-1", "AWS_ACCESS_KEY_ID": "TESTE_SEM_CREDENCIAL",
            "AWS_SECRET_ACCESS_KEY": "TESTE_SEM_CREDENCIAL", "AWS_EC2_METADATA_DISABLED": "true",
        }))
        self.guards.enter_context(patch.dict(sys.modules, {
            "boto3": None, "botocore": None, "publicar_sns": None,
        }))
        # Cada AppTest executa a página isolada, sem o registro st.navigation.
        # A navegação real é coberta pelo teste das quatorze telas em test_dashboard.
        import streamlit as st
        self.guards.enter_context(patch.object(st, "page_link", return_value=None))
        # Conserva a trava real, em diretório exclusivo, para não disputar o
        # worker F7 com outras validações locais executadas em paralelo.
        self.guards.enter_context(patch.object(runtime, "PROJECT_ROOT", Path(self.temp)))
        executar_local = runtime._execute

        def somente_worker_fase7(comando, payload, **opcoes):
            self.assertEqual(Path(comando[-1]).resolve(), runtime.WORKERS["fase7"].resolve())
            self.assertFalse(any(chave.upper().startswith("AWS_") for chave in opcoes["env"]))
            return executar_local(comando, payload, **opcoes)

        self.execute = self.guards.enter_context(patch.object(
            runtime, "_execute", side_effect=somente_worker_fase7))
        self.forecast = self.guards.enter_context(patch.object(
            fase2, "forecast", side_effect=AssertionError("Consulta exige ação explícita")))

    def _abrir(self):
        from streamlit.testing.v1 import AppTest
        caminho = runtime.SERVICE_DIRS["fase4"] / "src" / "frontend" / "pages" / "13_Alertas_Fase7.py"
        chamadas = self.execute.call_count
        pagina = AppTest.from_file(str(caminho), default_timeout=30).run()
        self._sem_excecoes(pagina)
        self.assertEqual(self.execute.call_count, chamadas, "A abertura deve apenas inspecionar pré-condições")
        return pagina

    def _sem_excecoes(self, pagina):
        self.assertEqual(list(pagina.exception), [])

    def _widget(self, pagina, tipo, chave):
        return next(elemento for elemento in pagina.get(tipo) if elemento.key == chave)

    def _escolher(self, pagina, tipo, chave, valor):
        chamadas = self.execute.call_count
        self._widget(pagina, tipo, chave).set_value(valor).run()
        self._sem_excecoes(pagina)
        self.assertEqual(self.execute.call_count, chamadas, "Alterar seleção não deve avaliar automaticamente")
        return pagina

    def _clicar(self, pagina, rotulo):
        next(botao for botao in pagina.button if botao.label == rotulo).click().run()
        self._sem_excecoes(pagina)
        return pagina

    def _texto(self, pagina):
        valores = []
        for tipo in ("title", "header", "subheader", "markdown", "caption", "text", "code",
                     "warning", "error", "success", "info", "text_area"):
            for elemento in pagina.get(tipo):
                try:
                    valores.append(str(elemento.value))
                except (AttributeError, KeyError):
                    pass
        return "\n".join(valores)

    def _csv(self, *, idade=30, umidade=40, marcador=False, timestamp=None):
        instante = timestamp or (datetime.now(timezone.utc) - timedelta(seconds=idade)).isoformat()
        campos = ("ts_iso", "t_rel_ms", "umidade", "temp_c", "ldr", "ph_base", "ph_corr",
                  "N", "P", "K", "bomba_fw")
        saida = io.StringIO(newline="")
        if marcador:
            saida.write("# FARMTECH_EXEMPLO_IOT_SINTETICO\n")
        writer = csv.writer(saida, lineterminator="\n")
        writer.writerow(campos)
        writer.writerow((instante, 30000, umidade, 25, 2223, 6.4, 6.4, 1, 1, 1, int(umidade < 45)))
        return saida.getvalue().encode("utf-8")

    def _upload(self, conteudo):
        import streamlit as st
        arquivo = SimpleNamespace(name="captura_controlada.csv", getvalue=lambda: conteudo,
                                  size=len(conteudo))
        return patch.object(st, "file_uploader", return_value=arquivo)

    def _modo_upload(self, pagina):
        self._escolher(pagina, "radio", "fase7_mode", "CSV IoT da Fase 2")
        self._escolher(pagina, "radio", "fase7_csv_source", "Enviar CSV")
        return pagina

    def _previsao(self, *, idade=0, umidade=40, chuva=0):
        agora = datetime.now(timezone.utc)
        instante = agora + timedelta(hours=1) if not idade else agora - timedelta(hours=idade)
        return Result("ok", "Previsão controlada sem rede", {
            "location": {"name": "Irecê", "admin1": "Bahia", "country": "Brasil", "latitude": -11.3, "longitude": -41.8},
            "hourly": [{"ts_iso": instante.isoformat(), "umidade": umidade, "rain_mm": chuva,
                        "temp_c": 25, "wind_ms": 2}], "timezone": "UTC",
        }, {"phase": "fase2", "provider": "fixture sem rede", "retrieved_at": agora.isoformat()})

    def test_abertura_inspeciona_disponibilidade_sem_avaliar_rede_ou_sns(self):
        with patch.object(fase7, "evaluate_iot_csv", side_effect=AssertionError("Não avaliar ao abrir")), \
                patch.object(fase7, "evaluate_weather", side_effect=AssertionError("Não avaliar ao abrir")), \
                patch.object(fase7, "demo_iot", side_effect=AssertionError("Não gerar ao abrir")), \
                patch.object(fase7, "demo_weather", side_effect=AssertionError("Não gerar ao abrir")):
            pagina = self._abrir()
        self.forecast.assert_not_called()
        self.assertFalse(Path(os.environ["DB_PATH"]).exists())
        self.assertFalse(any("enviar" in botao.label.casefold() or "publicar" in botao.label.casefold()
                             for botao in pagina.button))

    def test_demonstracao_iot_explicita_exibe_origem_assunto_e_corpo_sem_aws(self):
        pagina = self._abrir()
        self._clicar(pagina, "Avaliar demonstração")
        texto = self._texto(pagina)
        self.assertIn("SINTÉTICO", texto.upper())
        self.assertIn("FarmTech", texto)
        self.assertIn("45", texto)
        self.assertTrue("prévia" in texto.casefold() or "assunto" in texto.casefold())
        self.forecast.assert_not_called()

    def test_servico_ausente_mantem_pagina_disponivel_com_aviso(self):
        with patch.object(fase7, "availability", return_value=Result("unavailable", "Fontes locais ausentes")), \
                patch.object(fase7, "demo_iot", side_effect=AssertionError("Não avaliar serviço ausente")):
            pagina = self._abrir()
        self.assertIn("Fontes locais ausentes", self._texto(pagina))
        self.assertEqual(list(pagina.button), [])
        self.execute.assert_not_called()
        self.forecast.assert_not_called()

    def test_troca_de_cenario_oculta_previa_anterior_sem_reavaliar(self):
        pagina = self._abrir()
        with patch.object(fase7, "demo_iot", wraps=fase7.demo_iot) as avaliar:
            self._clicar(pagina, "Avaliar demonstração")
            avaliar.assert_called_once()
            caso = self._widget(pagina, "selectbox", "fase7_demo_case")
            atual = caso.value
            # Os valores técnicos permanecem estáveis sob format_func português.
            outro = "normal" if atual != "normal" else "umidade_baixa"
            caso.set_value(outro).run()
            self._sem_excecoes(pagina)
            avaliar.assert_called_once()
        self.assertNotIn("FarmTech [EXEMPLO SINTÉTICO]", self._texto(pagina))

    def test_demonstracao_meteorologica_e_avaliacao_local_sem_consulta(self):
        pagina = self._abrir()
        self._escolher(pagina, "selectbox", "fase7_demo_source", "Previsão meteorológica")
        self._clicar(pagina, "Avaliar demonstração")
        texto = self._texto(pagina)
        self.assertIn("FarmTech", texto)
        self.assertIn("previs", texto.casefold())
        self.forecast.assert_not_called()

    def test_csv_replay_historico_exibe_idade_e_nao_alega_leitura_atual(self):
        with self._upload(self._csv(idade=3600 * 24 * 90)):
            pagina = self._modo_upload(self._abrir())
            self._escolher(pagina, "selectbox", "fase7_origin", "wokwi")
            self._clicar(pagina, "Avaliar CSV IoT")
        texto = self._texto(pagina)
        self.assertIn("HISTÓRICO", texto.upper())
        self.assertIn("WOKWI", texto.upper())
        self.assertIn("recepção", texto.casefold())
        self.assertIn("não representa uma medição atual", texto.casefold())

    def test_csv_atual_com_origem_declarada_mostra_previa_sem_publicar(self):
        with self._upload(self._csv()):
            pagina = self._modo_upload(self._abrir())
            self._escolher(pagina, "checkbox", "fase7_history", False)
            self._escolher(pagina, "selectbox", "fase7_origin", "esp32")
            self._clicar(pagina, "Avaliar CSV IoT")
        texto = self._texto(pagina)
        self.assertIn("ESP32 DECLARADO", texto)
        self.assertIn("não verificada", texto.casefold())
        self.assertIn("DHT22", texto)

    def test_csv_sintetico_mantem_rotulo_mesmo_origem_esp32(self):
        with self._upload(self._csv(marcador=True)):
            pagina = self._modo_upload(self._abrir())
            self._escolher(pagina, "selectbox", "fase7_origin", "esp32")
            self._clicar(pagina, "Avaliar CSV IoT")
        texto = self._texto(pagina)
        self.assertIn("EXEMPLO SINTÉTICO", texto)
        self.assertNotIn("FarmTech [HISTÓRICO / ESP32 DECLARADO]", texto)

    def test_csv_normal_nao_reutiliza_alerta_de_baixa_umidade(self):
        with self._upload(self._csv(umidade=60)):
            pagina = self._modo_upload(self._abrir())
            self._clicar(pagina, "Avaliar CSV IoT")
        texto = self._texto(pagina).casefold()
        self.assertTrue("sem alerta" in texto or "nenhum alerta" in texto or "nenhum limiar" in texto)
        self.assertNotIn("farmtech [histórico", texto)

    def test_csv_invalido_ausente_futuro_e_antigo_sem_replay_exibem_erro(self):
        cenarios = (
            (b"cabecalho,invalido\n1,2\n", True),
            (self._csv(timestamp=(datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()), True),
            (self._csv(idade=3600), False),
        )
        for conteudo, historico in cenarios:
            with self.subTest(conteudo=conteudo, historico=historico), self._upload(conteudo):
                pagina = self._modo_upload(self._abrir())
                self._escolher(pagina, "checkbox", "fase7_history", historico)
                self._clicar(pagina, "Avaliar CSV IoT")
                self.assertTrue(list(pagina.warning) or list(pagina.error))
        import streamlit as st
        with patch.object(st, "file_uploader", return_value=None):
            pagina = self._modo_upload(self._abrir())
            botao = next(botao for botao in pagina.button if botao.label == "Avaliar CSV IoT")
            self.assertTrue(botao.disabled)
            with patch.object(fase7, "evaluate_iot_csv") as avaliar:
                pagina.run()
                self._sem_excecoes(pagina)
                avaliar.assert_not_called()

    def test_csv_naive_exige_fuso_e_recupera_com_offset_explicito(self):
        local = (datetime.now(timezone.utc) - timedelta(seconds=30)).astimezone(timezone(timedelta(hours=-3)))
        with self._upload(self._csv(timestamp=local.replace(tzinfo=None).isoformat())):
            pagina = self._modo_upload(self._abrir())
            self._clicar(pagina, "Avaliar CSV IoT")
            self.assertTrue(list(pagina.warning) or list(pagina.error))
            self._escolher(pagina, "selectbox", "fase7_timezone", "-03:00")
            self._clicar(pagina, "Avaliar CSV IoT")
        self.assertIn("Horário UTC de recepção", self._texto(pagina))

    def test_mudar_origem_csv_oculta_resultado_sem_nova_avaliacao(self):
        with self._upload(self._csv()), patch.object(fase7, "evaluate_iot_csv", wraps=fase7.evaluate_iot_csv) as avaliar:
            pagina = self._modo_upload(self._abrir())
            self._clicar(pagina, "Avaliar CSV IoT")
            avaliar.assert_called_once()
            self._escolher(pagina, "selectbox", "fase7_origin", "wokwi")
            avaliar.assert_called_once()
        self.assertNotIn("FarmTech [HISTÓRICO / ORIGEM NÃO COMPROVADA]", self._texto(pagina))

    def test_substituir_conteudo_csv_oculta_resultado_ate_novo_clique(self):
        with self._upload(self._csv()) as uploader:
            pagina = self._modo_upload(self._abrir())
            self._clicar(pagina, "Avaliar CSV IoT")
            chamadas = self.execute.call_count
            conteudo = self._csv(umidade=85)
            uploader.return_value.getvalue = lambda: conteudo
            uploader.return_value.size = len(conteudo)
            pagina.run()
            self._sem_excecoes(pagina)
            self.assertEqual(self.execute.call_count, chamadas)
            self.assertIn("A seleção foi alterada", self._texto(pagina))
            self.assertNotIn("FarmTech [HISTÓRICO", self._texto(pagina))

    def test_resultado_recente_armazenado_nao_permanece_atual_apos_cinco_minutos(self):
        with self._upload(self._csv()):
            pagina = self._modo_upload(self._abrir())
            self._escolher(pagina, "checkbox", "fase7_history", False)
            self._clicar(pagina, "Avaliar CSV IoT")
            armazenado = json.loads(json.dumps(pagina.session_state["fase7_preview_result"]))
            armazenado["result"]["data"]["reading"]["ts_iso"] = (
                datetime.now(timezone.utc) - timedelta(seconds=301)).isoformat()
            pagina.session_state["fase7_preview_result"] = armazenado
            chamadas = self.execute.call_count
            pagina.run()
            self._sem_excecoes(pagina)
            self.assertEqual(self.execute.call_count, chamadas)
        self.assertIn("ultrapassou cinco minutos", self._texto(pagina))
        self.assertNotIn("Prévia da mensagem", self._texto(pagina))

    def test_previsao_so_consulta_apos_clique_e_reutiliza_resultado_fase2(self):
        self.forecast.side_effect = None
        self.forecast.return_value = self._previsao()
        pagina = self._abrir()
        self._escolher(pagina, "radio", "fase7_mode", "Previsão Open-Meteo")
        self.forecast.assert_not_called()
        self._clicar(pagina, "Solicitar previsão e avaliar")
        self.forecast.assert_called_once_with("Irecê")
        texto = self._texto(pagina)
        self.assertIn("Umidade relativa do ar prevista", texto)
        self.assertIn("não mede a umidade do solo", texto)
        self.assertEqual(pagina.session_state["fase2_integration_result"]["status"], "ok")
        self._clicar(pagina, "Avaliar previsão já consultada")
        self.forecast.assert_called_once()

    def test_previsao_armazenada_desatualizada_nao_e_revalidada_como_atual(self):
        pagina = self._abrir()
        pagina.session_state["fase2_integration_result"] = self._previsao(idade=48).as_dict()
        self._escolher(pagina, "radio", "fase7_mode", "Previsão Open-Meteo")
        self._clicar(pagina, "Avaliar previsão já consultada")
        self.assertTrue(list(pagina.warning) or list(pagina.error))
        self.assertNotIn("FarmTech: Umidade", self._texto(pagina))
        self.forecast.assert_not_called()

    def test_previsao_cache_com_localizacao_invalida_exibe_aviso_sem_quebrar(self):
        for localizacao in (None, ["Irecê"]):
            with self.subTest(localizacao=localizacao):
                pagina = self._abrir()
                armazenada = self._previsao().as_dict()
                armazenada["data"]["location"] = localizacao
                pagina.session_state["fase2_integration_result"] = armazenada
                self._escolher(pagina, "radio", "fase7_mode", "Previsão Open-Meteo")
                self._clicar(pagina, "Avaliar previsão já consultada")
                self.assertTrue(list(pagina.warning) or list(pagina.error))
                self.assertNotIn("Prévia da mensagem", self._texto(pagina))
        self.forecast.assert_not_called()


if __name__ == "__main__":
    unittest.main()
