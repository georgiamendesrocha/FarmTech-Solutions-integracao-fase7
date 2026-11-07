"""HTML, autenticação preservada e indisponibilidade: verificações locais F7."""

import contextlib
from datetime import datetime, timezone
import inspect
import io
import logging
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from farmtech_integracao import fase2, fase3, fase7, runtime
from farmtech_integracao.contracts import Result

SENTINELA = "SENTINELA_PRIVADA_F7"
DETALHE_PRIVADO = SENTINELA + r" C:\simulado\arquivo-interno.txt"
HTML_CONTROLADO = "HTML_PROBE <script>alert(1)</script><img src=x onerror=alert(1)>"


class AlertasSegurancaTests(unittest.TestCase):
    def setUp(self):
        self.recursos = contextlib.ExitStack()
        self.addCleanup(self.recursos.close)
        pasta = self.recursos.enter_context(tempfile.TemporaryDirectory())
        self.recursos.enter_context(patch.dict(os.environ, {
            "FARMTECH_INTEGRACAO": "1", "FARMTECH_SIMULACAO": "0",
            "DB_PATH": str(Path(pasta) / "nao-criar.db"),
            "AWS_EC2_METADATA_DISABLED": "true",
        }))
        self.recursos.enter_context(patch.dict(sys.modules, {
            "boto3": None, "botocore": None, "publicar_sns": None,
        }))
        import streamlit as st
        # As páginas isoladas não registram os destinos do st.navigation.
        # A navegação verdadeira já tem sua própria verificação das 14 telas.
        self.recursos.enter_context(patch.object(st, "page_link", return_value=None))
        self.execute = self.recursos.enter_context(patch.object(
            runtime, "_execute", side_effect=AssertionError("Este teste não executa serviços")))
        self.forecast = self.recursos.enter_context(patch.object(
            fase2, "forecast", side_effect=AssertionError("Este teste não consulta a rede")))
        self.assinatura_oracle = inspect.signature(fase3.query_sensors_authenticated)
        self.oracle = self.recursos.enter_context(patch.object(
            fase3, "query_sensors_authenticated", side_effect=AssertionError("Oracle real não autorizado")))
        self.csv = self.recursos.enter_context(patch.object(
            fase3, "query_sensors", side_effect=AssertionError("Não consultar ao abrir")))
        self.logs = io.StringIO()
        handler = logging.StreamHandler(self.logs)
        for nome in ("", "streamlit.runtime.scriptrunner.exec_code"):
            logger = logging.getLogger(nome)
            logger.addHandler(handler)
            self.recursos.callback(logger.removeHandler, handler)
        self.recursos.callback(handler.close)

    def _abrir(self, nome="13_Alertas_Fase7.py"):
        from streamlit.testing.v1 import AppTest
        pagina = runtime.SERVICE_DIRS["fase4"] / "src" / "frontend" / "pages" / nome
        app = AppTest.from_file(str(pagina), default_timeout=30).run()
        self._seguro(app)
        return app

    def _seguro(self, app):
        self.assertEqual(len(app.exception), 0, "A página deve conter falhas do serviço opcional")
        self.execute.assert_not_called()

    def _texto(self, app):
        return "\n".join(str(elemento.value) for tipo in
                         ("markdown", "caption", "text", "warning", "error", "info", "success")
                         for elemento in app.get(tipo))

    def _sem_detalhes_privados(self, app):
        self.assertFalse(SENTINELA in self._texto(app), "Detalhe privado exposto na interface")
        self.assertFalse(SENTINELA in self.logs.getvalue(), "Detalhe privado exposto nos logs")

    def _clicar(self, app, prefixo):
        next(botao for botao in app.button if botao.label.startswith(prefixo)).click().run()
        self._seguro(app)
        return app

    def _modo(self, app, valor):
        next(radio for radio in app.radio if radio.key == "fase7_mode").set_value(valor).run()
        self._seguro(app)
        return app

    def test_item3_html_externo_permanece_literal_sem_unsafe_html(self):
        resposta = Result("ok", "Fixture controlada", {
            "alert": {"alerta": HTML_CONTROLADO, "acao": HTML_CONTROLADO}, "has_alert": True,
            "subject": HTML_CONTROLADO, "body": HTML_CONTROLADO, "reading": {}, "local": {},
            "preview_only": True, "sns_enabled": False, "mode": "demonstracao",
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
        }, {"origin": "controlada", "provider": HTML_CONTROLADO, "historical": False,
            "synthetic": True})
        with patch.object(fase7, "demo_iot", return_value=resposta):
            app = self._abrir()
            self._clicar(app, "Avaliar demonstra")
        dinamicos = [elemento for elemento in app.get("markdown") if "HTML_PROBE" in elemento.value]
        self.assertTrue(dinamicos, "A fixture deve alcançar a apresentação dos dados externos")
        self.assertTrue(all(not elemento.proto.allow_html for elemento in dinamicos))
        textos = [elemento.value for elemento in app.get("text")]
        self.assertEqual(textos.count(HTML_CONTROLADO), 2, "Assunto e corpo devem usar texto literal")

    def test_item3_info_card_escapa_mensagem_e_titulo(self):
        import streamlit as st
        from farmtech_integracao.ui import info_card
        with patch.object(st, "markdown") as markdown:
            info_card(HTML_CONTROLADO, title=HTML_CONTROLADO)
        html = markdown.call_args.args[0]
        self.assertTrue(markdown.call_args.kwargs["unsafe_allow_html"])
        self.assertNotIn("<script>", html)
        self.assertNotIn("<img src=x", html)
        self.assertEqual(html.count("&lt;script&gt;"), 2)

    def test_item7_stat_sem_permissao_retorna_indisponivel_generico(self):
        with patch.object(Path, "is_file", side_effect=PermissionError(DETALHE_PRIVADO)):
            resposta = fase7.availability()
        self.assertEqual(resposta.status, "unavailable")
        self.assertFalse(SENTINELA in str(resposta.as_dict()), "A inspeção não deve expor detalhes privados")
        self.execute.assert_not_called()

    def test_item7_excecao_no_preflight_nao_interrompe_pagina(self):
        with patch.object(fase7, "availability", side_effect=PermissionError(DETALHE_PRIVADO)):
            app = self._abrir()
        self.assertTrue(list(app.warning) or list(app.error))
        self._sem_detalhes_privados(app)
        self.forecast.assert_not_called()
        self.oracle.assert_not_called()

    def test_item7_excecao_no_avaliador_nao_expoe_mensagem_ou_caminho(self):
        with patch.object(fase7, "demo_iot", side_effect=RuntimeError(DETALHE_PRIVADO)):
            app = self._abrir()
            self._clicar(app, "Avaliar demonstra")
        self.assertTrue(list(app.warning) or list(app.error))
        self._sem_detalhes_privados(app)

    def test_item7_result_erro_meteorologico_nao_expoe_detalhes_privados(self):
        self.forecast.side_effect = None
        self.forecast.return_value = Result("error", DETALHE_PRIVADO)
        app = self._modo(self._abrir(), "Previsão Open-Meteo")
        self.forecast.assert_not_called()
        self._clicar(app, "Solicitar previsão")
        self.forecast.assert_called_once_with("Irecê")
        self.assertTrue(list(app.warning) or list(app.error))
        self._sem_detalhes_privados(app)

    def test_upload_csv_limita_tamanho_no_widget_a_um_mib(self):
        app = self._modo(self._abrir(), "CSV IoT da Fase 2")
        next(radio for radio in app.radio if radio.key == "fase7_csv_source").set_value("Enviar CSV").run()
        self._seguro(app)
        upload = app.get("file_uploader")[0]
        self.assertEqual(upload.proto.max_upload_size_mb, 1)
        self.forecast.assert_not_called()
        self.oracle.assert_not_called()

    def test_item5_alertas_sem_credenciais_preserva_formulario_oracle_existente(self):
        from streamlit.proto.TextInput_pb2 import TextInput as TextInputProto
        assinatura = self.assinatura_oracle
        self.assertEqual(list(assinatura.parameters), ["rm", "password", "dsn", "limit", "timeout"])
        app = self._abrir()
        for modo in ("CSV IoT da Fase 2", "Previsão Open-Meteo"):
            self._modo(app, modo)
            for entrada in app.text_input:
                self.assertNotEqual(entrada.proto.type, TextInputProto.PASSWORD)
                self.assertFalse(any(palavra in entrada.label.casefold()
                                     for palavra in ("senha", "credencial", "access key", "secret key")))
        self.oracle.assert_not_called()
        self.csv.assert_not_called()
        # A integração mantém a autenticação Oracle própria, por operação.
        pagina_oracle = self._abrir("11_Oracle_Consultas.py")
        pagina_oracle.radio[0].set_value("Oracle — consulta real").run()
        self._seguro(pagina_oracle)
        senha = next(entrada for entrada in pagina_oracle.text_input if "Senha Oracle" in entrada.label)
        self.assertEqual(senha.proto.type, TextInputProto.PASSWORD)
        next(entrada for entrada in pagina_oracle.text_input if entrada.label == "RM FIAP").set_value("RM123456")
        senha.set_value("SENHA_SINTETICA_TESTE")
        next(entrada for entrada in pagina_oracle.text_input if "(DSN)" in entrada.label).set_value("oracle-invalido.local:1521/TESTE")
        self.oracle.side_effect = None
        self.oracle.return_value = Result("invalid", "Resposta controlada sem conectar ao banco")
        self._clicar(pagina_oracle, "Conectar e consultar")
        self.oracle.assert_called_once_with("RM123456", "SENHA_SINTETICA_TESTE",
                                            "oracle-invalido.local:1521/TESTE", limit=200)
        self.csv.assert_not_called()
        self.assertNotIn("SENHA_SINTETICA_TESTE", self._texto(pagina_oracle))


if __name__ == "__main__":
    unittest.main()
