"""Meteorologia com respostas simuladas; nenhuma chamada externa ou persistência."""

import contextlib
import io
import json
import unittest
from unittest.mock import patch
from urllib.error import URLError

from farmtech_integracao import fase2
from farmtech_integracao.workers import fase2_worker


class Fase2Tests(unittest.TestCase):
    def setUp(self):
        self.original = fase2_worker.load_weather_module()
        self.location = {"name": "Irecê", "admin1": "Bahia", "country": "Brazil", "latitude": -11.3, "longitude": -41.8}
        self.response = {
            "timezone": "UTC", "utc_offset_seconds": 0,
            "hourly_units": {"windspeed_10m": "m/s"},
            "hourly": {"time": ["2026-11-03T12:00", "2026-11-03T13:00"],
                       "temperature_2m": [27, 28], "relativehumidity_2m": [60, 58],
                       "precipitation": [0.2, 0], "windspeed_10m": [3.5, 4], "weathercode": [3, 1]},
        }

    def request(self, response=None):
        with patch.object(fase2_worker, "load_weather_module", return_value=self.original):
            with patch.object(self.original, "fetch_json", side_effect=[{"results": [self.location]}, response or self.response]) as fetch:
                with patch.object(self.original, "save_json") as save_json, patch.object(self.original, "save_csv") as save_csv:
                    result = fase2_worker.forecast({"operation": "forecast", "city": "Irecê"})
                    save_json.assert_not_called()
                    save_csv.assert_not_called()
        return result, fetch

    def test_real_normalization_uses_mocked_network_without_saving(self):
        result, fetch = self.request()
        self.assertTrue(result.ok, result.message)
        self.assertEqual(result.data["hourly"][0]["ts_iso"], "2026-11-03T12:00:00Z")
        self.assertEqual(result.data["hourly"][0]["wind_ms"], 3.5)
        self.assertEqual(result.data["units"]["wind_ms"], "m/s")
        self.assertFalse(result.data["persistence"])
        self.assertIn("timezone=UTC", fetch.call_args_list[1].args[0])
        self.assertIn("wind_speed_unit=ms", fetch.call_args_list[1].args[0])
        self.assertTrue(all(call.kwargs.get("max_bytes") == fase2_worker.MAX_HTTP_BYTES
                            for call in fetch.call_args_list))

    def test_timestamps_without_measurements_do_not_report_success(self):
        for hourly in ({"time": self.response["hourly"]["time"]},
                       {"time": self.response["hourly"]["time"], "weathercode": [3, 1]}):
            with self.subTest(hourly=hourly):
                result, _ = self.request({**self.response, "hourly": hourly})
                self.assertEqual(result.status, "unavailable")
                self.assertFalse(result.ok)

    def test_partial_series_with_a_real_measurement_remains_usable(self):
        response = {**self.response, "hourly": {"time": self.response["hourly"]["time"],
                                                "temperature_2m": [27]}}
        result, _ = self.request(response)
        self.assertTrue(result.ok)
        self.assertEqual(result.data["hourly"][0]["temp_c"], 27)
        self.assertIsNone(result.data["hourly"][1]["temp_c"])

    def test_http_body_limit_rejects_before_json_parsing(self):
        class Response(io.BytesIO):
            status = 200

            def read(self, size=-1):
                self.requested_size = size
                return super().read(size)

        response = Response(b'{"value":"' + b"x" * 100 + b'"}')
        with patch.object(self.original.urllib.request, "urlopen", return_value=response) as open_url:
            with patch.object(self.original.json, "loads") as parse:
                with self.assertRaises(ValueError):
                    self.original.fetch_json("https://fixture.invalid", max_bytes=32)
                parse.assert_not_called()
        self.assertEqual(response.requested_size, 33)
        open_url.assert_called_once_with("https://fixture.invalid", timeout=15)

    def test_http_body_limit_accepts_small_json_and_legacy_call(self):
        class Response(io.BytesIO):
            status = 200

        body = b'{"value":27}'
        for kwargs in ({"max_bytes": len(body)}, {}):
            with self.subTest(kwargs=kwargs):
                with patch.object(self.original.urllib.request, "urlopen", return_value=Response(body)):
                    self.assertEqual(self.original.fetch_json("https://fixture.invalid", **kwargs), {"value": 27})

    def test_rejects_wrong_timezone_or_wind_units(self):
        for key, value in (("timezone", "America/Bahia"), ("hourly_units", {"windspeed_10m": "km/h"})):
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.request({**self.response, key: value})

    def test_invalid_city_does_not_load_or_contact_source(self):
        for city in ("", "x", "a" * 121, "Irecê\n", 123):
            with self.subTest(city=city), patch.object(fase2_worker, "load_weather_module") as load:
                with self.assertRaises(ValueError):
                    fase2_worker.forecast({"operation": "forecast", "city": city})
                load.assert_not_called()

    def test_no_geocoding_match_returns_a_useful_state(self):
        with patch.object(fase2_worker, "load_weather_module", return_value=self.original):
            with patch.object(self.original, "fetch_json", return_value={"results": []}):
                result = fase2_worker.forecast({"operation": "forecast", "city": "Irecê"})
        self.assertEqual(result.status, "unavailable")

    def test_worker_returns_json_without_network_exception_details(self):
        output = io.StringIO()
        with patch.object(fase2_worker.sys, "stdin", io.StringIO('{"operation":"forecast","city":"Irecê"}')):
            with patch.object(fase2_worker, "forecast", side_effect=URLError("private_fixture_detail")):
                with contextlib.redirect_stdout(output):
                    fase2_worker.main()
        result = json.loads(output.getvalue())
        self.assertEqual(result["status"], "unavailable")
        self.assertNotIn("private_fixture_detail", output.getvalue())

    def test_availability_never_starts_hardware_r_or_weather(self):
        with patch.object(fase2, "run_json_worker") as run:
            result = fase2.availability()
        run.assert_not_called()
        self.assertFalse(result.data["serial_execution_enabled"])
        self.assertFalse(result.data["r_execution_enabled"])


if __name__ == "__main__":
    unittest.main()
