"""Verifica exportação meteorológica sem rede e sem alterar evidências."""

import csv
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from unittest.mock import patch

from scripts import weather_forecast


class WeatherForecastTests(unittest.TestCase):
    def forecast_fixture(self):
        return {
            "timezone": "GMT", "utc_offset_seconds": 0,
            "hourly_units": {"windspeed_10m": "m/s"},
            "hourly": {"time": ["2026-11-01T00:00", "2026-11-01T01:00"],
                       "temperature_2m": [25, 24], "relativehumidity_2m": [60, 65],
                       "precipitation": [0, 1], "windspeed_10m": [2.5, 3], "weathercode": [0, 1]},
        }

    def test_new_rows_identify_utc_and_keep_wind_in_meters_per_second(self):
        forecast = self.forecast_fixture()
        rows = weather_forecast.normalize_forecast({"name": "Fixture"}, forecast)
        self.assertEqual(rows[0]["ts_iso"], "2026-11-01T00:00:00Z")
        self.assertEqual(rows[0]["wind_ms"], 2.5)
        self.assertEqual(forecast["hourly"]["time"][0], "2026-11-01T00:00")

    def test_rejects_mismatched_or_missing_wind_units_without_conversion(self):
        for unit in ("km/h", "mph", None):
            forecast = self.forecast_fixture()
            forecast["hourly_units"]["windspeed_10m"] = unit
            with self.subTest(unit=unit), self.assertRaisesRegex(ValueError, "m/s"):
                weather_forecast.normalize_forecast({}, forecast)
            self.assertEqual(forecast["hourly"]["windspeed_10m"][0], 2.5)

    def test_rejects_non_utc_metadata(self):
        forecast = self.forecast_fixture()
        forecast.update(timezone="America/Bahia", utc_offset_seconds=-10800)
        with self.assertRaisesRegex(ValueError, "UTC"):
            weather_forecast.normalize_forecast({}, forecast)

    def test_invalid_response_does_not_overwrite_existing_outputs(self):
        forecast = self.forecast_fixture()
        forecast["hourly_units"]["windspeed_10m"] = "km/h"
        with tempfile.TemporaryDirectory(prefix=".tmp_weather_", dir=Path(__file__).parent) as temporary:
            json_path, csv_path = Path(temporary) / "forecast.json", Path(temporary) / "forecast.csv"
            json_path.write_text('{"historical": true}', encoding="utf-8")
            csv_path.write_text("historical,evidence\n", encoding="utf-8")
            location = {"latitude": 0, "longitude": 0, "name": "Fixture"}
            with patch.object(sys, "argv", ["weather_forecast.py", "--out-json", str(json_path), "--out-csv", str(csv_path)]):
                with patch.object(weather_forecast, "fetch_json", side_effect=[{"results": [location]}, forecast]):
                    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                        self.assertEqual(weather_forecast.main(), 4)
            self.assertEqual(json.loads(json_path.read_text()), {"historical": True})
            self.assertEqual(csv_path.read_text(), "historical,evidence\n")

    def test_full_forecast_flow_uses_mocked_service_and_temporary_outputs(self):
        forecast = self.forecast_fixture()
        with tempfile.TemporaryDirectory(prefix=".tmp_weather_", dir=Path(__file__).parent) as temporary:
            json_path, csv_path = Path(temporary) / "forecast.json", Path(temporary) / "forecast.csv"
            location = {"latitude": 0, "longitude": 0, "name": "Fixture"}
            with patch.object(sys, "argv", ["weather_forecast.py", "--out-json", str(json_path), "--out-csv", str(csv_path)]):
                with patch.object(weather_forecast, "fetch_json", side_effect=[{"results": [location]}, forecast]):
                    with contextlib.redirect_stdout(io.StringIO()):
                        self.assertEqual(weather_forecast.main(), 0)
            self.assertEqual(json.loads(json_path.read_text())["forecast"], forecast)
            with csv_path.open(encoding="utf-8", newline="") as source:
                rows = list(csv.DictReader(source))
            self.assertEqual(rows[0]["ts_iso"], "2026-11-01T00:00:00Z")
            self.assertEqual(rows[0]["wind_ms"], "2.5")

    def test_forecast_requests_wind_in_meters_per_second_and_utc(self):
        query = parse_qs(urlparse(weather_forecast.build_forecast_url(-11, -42)).query)
        self.assertEqual(query["wind_speed_unit"], ["ms"])
        self.assertEqual(query["timezone"], ["UTC"])
        self.assertEqual(query["latitude"], ["-11"])
        self.assertEqual(query["longitude"], ["-42"])

    def test_city_is_encoded_as_one_query_value(self):
        city = 'Cidade, "A&B"?country=XX\nCentro'
        query = parse_qs(urlparse(weather_forecast.build_geocode_url(city)).query)
        self.assertEqual(query["name"], [city])
        self.assertNotIn("country", query)

    def test_csv_round_trip_preserves_commas_quotes_and_newlines(self):
        row = {
            "city": 'Cidade, "Centro"\nDistrito',
            "country": "País",
            "latitude": -11.2,
            "longitude": -41.8,
            "ts_iso": "2026-11-01T12:00",
            "temp_c": 27.5,
            "umidade": 65,
            "rain_mm": 0,
            "wind_ms": 4.2,
            "weathercode": 1,
        }
        with tempfile.TemporaryDirectory(prefix=".tmp_weather_", dir=Path(__file__).parent) as temporary:
            path = Path(temporary) / "previsao.csv"
            weather_forecast.save_csv([row], path)
            with path.open(encoding="utf-8", newline="") as source:
                rows = list(csv.DictReader(source))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0], {key: str(value) for key, value in row.items()})

    def test_empty_forecast_keeps_csv_header(self):
        with tempfile.TemporaryDirectory(prefix=".tmp_weather_", dir=Path(__file__).parent) as temporary:
            path = Path(temporary) / "previsao.csv"
            weather_forecast.save_csv([], path)
            with path.open(encoding="utf-8", newline="") as source:
                reader = csv.DictReader(source)
                self.assertIn("wind_ms", reader.fieldnames)
                self.assertEqual(list(reader), [])


if __name__ == "__main__":
    unittest.main()
