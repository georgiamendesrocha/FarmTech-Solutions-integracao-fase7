"""Renderização real Streamlit; ações externas simuladas, consultas locais reais."""

import json
import os
from pathlib import Path
import sqlite3
import struct
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zlib

from farmtech_integracao.contracts import Result
from farmtech_integracao.runtime import PROJECT_ROOT, SERVICE_DIRS
from farmtech_integracao.workers.fase4_worker import prepare


class DashboardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.database = Path(cls.temporary.name)/"fixture.db"
        cls.environment = patch.dict(os.environ, {"DB_PATH": str(cls.database), "FARMTECH_INTEGRACAO": "1", "FARMTECH_SIMULACAO": "0"})
        cls.environment.start()
        result = prepare(cls.database)
        if not result.ok:
            raise AssertionError(result.message)

    @classmethod
    def tearDownClass(cls):
        from src.frontend.scheduler import encerrar_scheduler
        encerrar_scheduler()
        cls.environment.stop()
        cls.temporary.cleanup()

    def run_page(self, filename):
        from streamlit.testing.v1 import AppTest
        return AppTest.from_file(str(SERVICE_DIRS["fase4"] / "src" / "frontend" / filename), default_timeout=60).run()

    def test_all_thirteen_screens_render_without_executing_service_workers(self):
        from farmtech_integracao import runtime
        with patch.object(runtime, "_execute", side_effect=AssertionError("Abertura não deve executar serviços")) as execute:
            folder = SERVICE_DIRS["fase4"] / "src" / "frontend" / "pages"
            names = ["app.py", *["pages/"+p.name for p in sorted(folder.glob("*.py"))]]
            self.assertEqual(len(names), 13)
            # A navegação principal registra os destinos usados por st.page_link.
            # Executar uma página isolada no AppTest não oferece esse registro.
            page = self.run_page("app.py")
            for name in names:
                with self.subTest(page=name):
                    if name != "app.py":
                        page.switch_page(name).run()
                    self.assertEqual(list(page.exception), [])
            execute.assert_not_called()
        from src.frontend import scheduler
        self.assertIsNone(scheduler._SCHEDULER)
        connection=sqlite3.connect(self.database)
        try:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM leituras_sensores").fetchone()[0],153)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM previsoes").fetchone()[0],0)
        finally:
            connection.close()

    def test_gestao_button_executes_real_calculation(self):
        page=self.run_page("pages/9_Gestao_Agricola.py")
        next(button for button in page.button if button.label=="Calcular talhão").click().run()
        self.assertEqual(list(page.exception),[])
        self.assertEqual(len(page.metric),4)
        self.assertEqual(page.session_state["fase1_integration_result"]["status"],"ok")

    def test_fase2_button_uses_explicit_mocked_forecast(self):
        from farmtech_integracao import fase2
        result=Result("ok","Previsão de teste",data={
            "location":{"name":"Cidade da fixture","admin1":"BA","country":"Brasil","latitude":-10.0,"longitude":-40.0},
            "hourly":[{"ts_iso":"2026-11-03T12:00:00Z","temp_c":25.0,"umidade":60.0,"rain_mm":0.0,"wind_ms":2.0}]},
            source={"provider":"fixture, sem rede", "retrieved_at":"2026-11-03T12:00:00Z"})
        with patch.object(fase2,"forecast",return_value=result) as forecast:
            page=self.run_page("pages/10_IoT_Meteorologia.py")
            forecast.assert_not_called()
            next(button for button in page.button if button.label=="Consultar previsão").click().run()
            forecast.assert_called_once()
            self.assertEqual(list(page.exception),[])
            self.assertEqual(len(page.get("plotly_chart")),4)

    def test_fase6_button_uses_mock_only_and_renders_experimental_metrics(self):
        from farmtech_integracao import fase6
        data={"total_imagens":8,"tempo_medio_ms":10.0,"metricas":{
            name:{"precision":.5,"recall":.25,"f1":1/3,"tp":1,"fp":1,"fn":3}
            for name in ("banana","milho")}}
        with patch.object(fase6,"availability",return_value=Result("ok","Fixture de pré-condições")), patch.object(fase6,"evaluate_customizada",return_value=Result("ok","Avaliação simulada",data)) as evaluate:
            page=self.run_page("pages/12_Visao_Computacional.py")
            evaluate.assert_not_called()
            next(button for button in page.button if button.label=="Avaliar YOLO customizada").click().run()
            evaluate.assert_called_once()
            self.assertEqual(list(page.exception),[])
            self.assertEqual(len(page.get("plotly_chart")),1)

    def test_fase6_invalid_checkout_configuration_keeps_screen_available(self):
        from farmtech_integracao import runtime
        with patch.dict(os.environ, {"FARMTECH_YOLO_REPO": "x" * 4097}), patch.object(
            runtime, "_execute", side_effect=AssertionError("Configuração inválida não deve executar serviços")
        ) as execute:
            page = self.run_page("pages/12_Visao_Computacional.py")
        self.assertEqual(list(page.exception), [])
        self.assertTrue(list(page.warning))
        evaluate = next(button for button in page.button if button.label == "Avaliar YOLO customizada")
        self.assertTrue(evaluate.disabled)
        execute.assert_not_called()

    def test_fase6_rejects_excessive_pixel_dimensions_before_inference(self):
        import streamlit as st
        from farmtech_integracao import fase6

        def png_chunk(kind, data):
            return (struct.pack(">I", len(data)) + kind + data
                    + struct.pack(">I", zlib.crc32(kind + data)))

        # Cabeçalho pequeno: o Pillow deve rejeitar 400 milhões de pixels
        # antes de decodificar ou alocar memória para a imagem.
        blob = (bytes.fromhex("89504e470d0a1a0a")
                + png_chunk(b"IHDR", struct.pack(">IIBBBBB", 20000, 20000, 8, 0, 0, 0, 0))
                + png_chunk(b"IDAT", zlib.compress(b""))
                + png_chunk(b"IEND", b""))
        upload = SimpleNamespace(name="dimensoes_excessivas.png", getvalue=lambda: blob)
        with patch.object(st, "file_uploader", return_value=upload), patch.object(
            fase6, "inferir_imagem", side_effect=AssertionError("Imagem excessiva não deve executar inferência")
        ) as infer:
            page = self.run_page("pages/12_Visao_Computacional.py")
        self.assertEqual(list(page.exception), [])
        self.assertTrue(any("dimensões excessivas" in error.value for error in page.error))
        infer.assert_not_called()


if __name__ == "__main__":
    unittest.main()
