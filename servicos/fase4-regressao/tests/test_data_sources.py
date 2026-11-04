import json
import tempfile
import unittest
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pandas as pd

from src.data_sources import (
    NOAA_COLUMNS,
    SIDRA_CROPS,
    SIDRA_OUTPUT_COLUMNS,
    carregar_inmet,
    carregar_noaa,
    parse_noaa_text,
    parse_inmet_csv,
    parse_sidra_json,
    importar_inmet,
    importar_noaa,
    preparar_historico_sidra,
    preparar_serie_inmet_diaria,
    preparar_serie_noaa_diaria,
    importar_sidra,
)


def _noaa_line(soil_moisture: str = "0.179") -> str:
    fields = ["0"] * len(NOAA_COLUMNS)
    values = {
        "WBANNO": "63829",
        "UTC_DATE": "20250101",
        "UTC_TIME": "0100",
        "LST_DATE": "20241231",
        "LST_TIME": "2000",
        "CRX_VN": "2.622",
        "LONGITUDE": "-84.45",
        "LATITUDE": "31.19",
        "T_HR_AVG": "19.9",
        "P_CALC": "0.0",
        "RH_HR_AVG": "69",
        "SOIL_MOISTURE_5": soil_moisture,
        "SOIL_MOISTURE_10": "0.168",
        "SOIL_MOISTURE_20": "0.214",
        "SOIL_MOISTURE_50": "0.244",
        "SOIL_MOISTURE_100": "0.374",
        "SOIL_TEMP_5": "16.4",
        "SOIL_TEMP_10": "16.6",
        "SOIL_TEMP_20": "16.4",
        "SOIL_TEMP_50": "15.8",
        "SOIL_TEMP_100": "18.7",
    }
    for column, value in values.items():
        fields[NOAA_COLUMNS.index(column)] = value
    return " ".join(fields)


def _sidra_payload() -> bytes:
    header = {
        "D1C": "Município (Código)",
        "D1N": "Município",
        "D2C": "112",
        "D2N": "Rendimento médio da produção",
        "D3C": "Ano (Código)",
        "D3N": "Ano",
        "D4C": "Produto (Código)",
        "D4N": "Produto",
        "V": "Valor",
        "MN": "Quilogramas por Hectare",
    }
    row = {
        "D1C": "3106200",
        "D1N": "Belo Horizonte - MG",
        "D2C": "112",
        "D2N": "Rendimento médio da produção",
        "D3C": "2023",
        "D3N": "2023",
        "D4C": "2692",
        "D4N": "Arroz (em casca)",
        "V": "4000",
        "MN": "Quilogramas por Hectare",
    }
    return json.dumps([header, row]).encode("utf-8")


def _inmet_csv() -> bytes:
    lines = [
        "REGIAO:;SE",
        "UF:;SP",
        "ESTACAO:;SAO PAULO - MIRANTE",
        "CODIGO (WMO):;A701",
        "LATITUDE:;-23,4962888",
        "LONGITUDE:;-46,6200666",
        "ALTITUDE:;785,64",
        "DATA DE FUNDACAO:;25/07/06",
        "Data;Hora UTC;PRECIPITAÇÃO TOTAL, HORÁRIO (mm);TEMPERATURA DO AR - BULBO SECO, HORARIA (°C);UMIDADE RELATIVA DO AR, HORARIA (%)",
    ]
    for hour in range(100):
        day, day_hour = divmod(hour, 24)
        lines.append(
            f"2025/01/{day + 1:02d};{day_hour:02d}00 UTC;0,1;21,2;76"
        )
    return "\n".join(lines).encode("latin-1")


def _sidra_complete_payload(level: str, year: int = 2023) -> bytes:
    """Resposta coerente com o contrato real da requisição, sem downloads."""
    header, row = json.loads(_sidra_payload())
    records = [header]
    years = range(1990, 2026) if level == "brasil" else [year]
    for observation_year in years:
        for code, crop in SIDRA_CROPS.items():
            record = {**row, "D3C": str(observation_year), "D3N": str(observation_year),
                      "D4C": code, "D4N": crop}
            if level == "brasil":
                record.update(D1C="1", D1N="Brasil")
            records.append(record)
    return json.dumps(records).encode("utf-8")


class OfficialDataIngestionTests(unittest.TestCase):
    def test_noaa_ingestion_and_local_read_validate_observations(self) -> None:
        content = "\n".join(
            _noaa_line().replace("20250101", "20250102").replace("0100", f"{hour:02d}00", 1)
            for hour in range(24)
        ).encode("ascii")
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "observations.csv"
            metadata_path = Path(temp_dir) / "metadata.json"
            frame, metadata = importar_noaa(content, output_path, metadata_path)

            self.assertEqual(len(frame), 24)
            self.assertEqual(frame["soil_moisture_5cm_m3_m3"].iloc[0], 0.179)
            self.assertEqual(metadata["frequencia"], "horária; período de 60 minutos encerrado no timestamp UTC")
            self.assertEqual(len(carregar_noaa(output_path)), 24)
            self.assertTrue(metadata_path.is_file())
            daily = preparar_serie_noaa_diaria(frame, "soil_moisture_5cm_m3_m3")
            self.assertEqual(len(daily), 1)
            self.assertEqual(daily["n_observacoes"].iloc[0], 24)

    def test_noaa_missing_sentinel_is_not_fabricated(self) -> None:
        frame = parse_noaa_text(_noaa_line("-99.000"))
        self.assertTrue(pd.isna(frame["soil_moisture_5cm_m3_m3"].iloc[0]))
        self.assertEqual(frame["soil_moisture_10cm_m3_m3"].iloc[0], 0.168)

    def test_noaa_invalid_humidity_is_not_treated_as_observed_weather(self) -> None:
        fields = _noaa_line().split()
        fields[NOAA_COLUMNS.index("RH_HR_AVG")] = "101"
        with self.assertRaisesRegex(ValueError, "fora do intervalo"):
            parse_noaa_text(" ".join(fields))

        fields[NOAA_COLUMNS.index("RH_HR_AVG")] = "80"
        fields[NOAA_COLUMNS.index("RH_HR_AVG_FLAG")] = "1"
        invalid_flag = parse_noaa_text(" ".join(fields))
        self.assertTrue(pd.isna(invalid_flag["relative_humidity_pct"].iloc[0]))

    def test_noaa_rejects_bad_schema_and_invalid_moisture(self) -> None:
        with self.assertRaisesRegex(ValueError, "esperadas 38 colunas"):
            parse_noaa_text("1 2 3")
        no_moisture = _noaa_line("1.2").split()
        for column in NOAA_COLUMNS:
            if column.startswith("SOIL_MOISTURE_"):
                no_moisture[NOAA_COLUMNS.index(column)] = "1.2"
        with self.assertRaisesRegex(ValueError, "fora do intervalo"):
            parse_noaa_text(" ".join(no_moisture))

    def test_sidra_schema_and_provenance_fields_are_normalized(self) -> None:
        frame = parse_sidra_json(_sidra_payload(), "municipio")
        self.assertEqual(list(frame.columns), SIDRA_OUTPUT_COLUMNS)
        self.assertEqual(frame.loc[0, "municipio"], "Belo Horizonte")
        self.assertEqual(frame.loc[0, "uf"], "MG")
        self.assertEqual(frame.loc[0, "rendimento_kg_ha"], 4000)
        self.assertEqual(frame.loc[0, "nivel_geografico"], "municipio")

    def test_sidra_history_view_filters_national_series_only(self) -> None:
        payload = json.loads(_sidra_payload())
        payload[1]["D1C"] = "1"
        payload[1]["D1N"] = "Brasil"
        national = parse_sidra_json(json.dumps(payload).encode("utf-8"), "brasil")
        history = preparar_historico_sidra(national, "2692")
        self.assertEqual(history.loc[0, "ano"], 2023)
        self.assertEqual(history.loc[0, "rendimento_kg_ha"], 4000)

    def test_sidra_rejects_wrong_variable_or_schema(self) -> None:
        payload = json.loads(_sidra_payload())
        payload[1]["D2C"] = "33"
        with self.assertRaisesRegex(ValueError, "não é a variável"):
            parse_sidra_json(json.dumps(payload).encode("utf-8"), "municipio")

    def test_sidra_import_records_each_municipal_snapshot_period(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            _, municipalities, metadata = importar_sidra(
                output_dir=output_dir,
                municipal_year=2023,
                national_content=_sidra_complete_payload("brasil"),
                municipal_content=_sidra_complete_payload("municipio", 2023),
            )
            self.assertEqual(len(municipalities), 5)
            self.assertEqual(metadata["periodo_municipal"], 2023)
            self.assertTrue(
                (output_dir / "sidra1612_rendimento_municipios_2023.csv").is_file()
            )
            snapshot_metadata = json.loads(
                (output_dir / "sidra1612_metadata_municipios_2023.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(snapshot_metadata["periodo_municipal"], 2023)

    def test_inmet_archive_import_and_daily_series_are_validated(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            archive_path = root / "inmet.zip"
            with ZipFile(archive_path, "w", ZIP_DEFLATED) as archive:
                archive.writestr(
                    "2025/INMET_SE_SP_A701_SAO PAULO - MIRANTE_01-01-2025_A_31-12-2025.CSV",
                    _inmet_csv(),
                )
            frame, metadata = importar_inmet(
                archive_path,
                root / "inmet.csv",
                root / "metadata.json",
            )
            self.assertEqual(len(frame), 100)
            self.assertEqual(len(carregar_inmet(root / "inmet.csv")), 100)
            self.assertEqual(metadata["station_code"], "A701")
            self.assertEqual(frame["air_temperature_c"].iloc[0], 21.2)
            daily = preparar_serie_inmet_diaria(frame, "precipitation_mm")
            self.assertAlmostEqual(daily["valor"].iloc[0], 2.4)

    def test_inmet_rejects_station_code_mismatch(self) -> None:
        bad_content = _inmet_csv().replace(b"CODIGO (WMO):;A701", b"CODIGO (WMO):;B827")
        with self.assertRaisesRegex(ValueError, "A701"):
            parse_inmet_csv(bad_content)


if __name__ == "__main__":
    unittest.main()
