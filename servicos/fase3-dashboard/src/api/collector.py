from datetime import datetime

import requests

from src.api.db import execute_many, execute_query, get_conn

HOURLY_VARS = [
    "temperature_2m",
    "apparent_temperature",
    "relative_humidity_2m",
    "dewpoint_2m",
    "precipitation_probability",
    "precipitation",
    "rain",
    "snowfall",
    "weather_code",
    "pressure_msl",
    "surface_pressure",
    "cloud_cover",
    "visibility",
    "wind_speed_10m",
    "wind_direction_10m",
    "wind_gusts_10m",
    "uv_index",
    "shortwave_radiation",
]

DAILY_VARS = [
    "temperature_2m_max",
    "temperature_2m_min",
    "apparent_temperature_max",
    "apparent_temperature_min",
    "sunrise",
    "sunset",
    "precipitation_sum",
    "rain_sum",
    "precipitation_hours",
    "precipitation_probability_max",
    "wind_speed_10m_max",
    "wind_gusts_10m_max",
    "wind_direction_10m_dominant",
    "shortwave_radiation_sum",
    "uv_index_max",
    "weather_code",
]


def fetch_openmeteo(lat: float, lon: float, timezone: str) -> dict:
    r = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": lat,
            "longitude": lon,
            "timezone": timezone,
            "hourly": ",".join(HOURLY_VARS),
            "daily": ",".join(DAILY_VARS),
            "forecast_days": 7,
        },
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def _ts(val):
    return datetime.fromisoformat(val) if val else None


def save_hourly(id_location: int, data: dict) -> int:
    h = data["hourly"]
    n = len(h["time"])
    get = lambda k: h.get(k, [None] * n)
    records = [
        {
            "id_location": id_location,
            "dt_forecast": _ts(h["time"][i]),
            "nr_temperature_2m": get("temperature_2m")[i],
            "nr_apparent_temp": get("apparent_temperature")[i],
            "nr_humidity": get("relative_humidity_2m")[i],
            "nr_dewpoint": get("dewpoint_2m")[i],
            "nr_precipitation": get("precipitation")[i],
            "nr_rain": get("rain")[i],
            "nr_snowfall": get("snowfall")[i],
            "nr_precip_prob": get("precipitation_probability")[i],
            "nr_weathercode": get("weather_code")[i],
            "nr_pressure_msl": get("pressure_msl")[i],
            "nr_surface_press": get("surface_pressure")[i],
            "nr_cloudcover": get("cloud_cover")[i],
            "nr_visibility": get("visibility")[i],
            "nr_windspeed_10m": get("wind_speed_10m")[i],
            "nr_winddir_10m": get("wind_direction_10m")[i],
            "nr_windgusts": get("wind_gusts_10m")[i],
            "nr_uv_index": get("uv_index")[i],
            "nr_shortwave_rad": get("shortwave_radiation")[i],
        }
        for i in range(n)
    ]
    execute_many(
        """
        MERGE INTO WTH_HOURLY_FORECAST t USING DUAL
        ON (t.ID_LOCATION = :id_location AND t.DT_FORECAST = :dt_forecast)
        WHEN MATCHED THEN UPDATE SET
            NR_TEMPERATURE_2M=:nr_temperature_2m, NR_APPARENT_TEMP=:nr_apparent_temp,
            NR_HUMIDITY=:nr_humidity, NR_DEWPOINT=:nr_dewpoint,
            NR_PRECIPITATION=:nr_precipitation, NR_RAIN=:nr_rain,
            NR_SNOWFALL=:nr_snowfall, NR_PRECIP_PROB=:nr_precip_prob,
            NR_WEATHERCODE=:nr_weathercode, NR_PRESSURE_MSL=:nr_pressure_msl,
            NR_SURFACE_PRESS=:nr_surface_press, NR_CLOUDCOVER=:nr_cloudcover,
            NR_VISIBILITY=:nr_visibility, NR_WINDSPEED_10M=:nr_windspeed_10m,
            NR_WINDDIR_10M=:nr_winddir_10m, NR_WINDGUSTS=:nr_windgusts,
            NR_UV_INDEX=:nr_uv_index, NR_SHORTWAVE_RAD=:nr_shortwave_rad,
            DT_COLLECTED=SYSTIMESTAMP
        WHEN NOT MATCHED THEN INSERT (
            ID_LOCATION,DT_FORECAST,NR_TEMPERATURE_2M,NR_APPARENT_TEMP,NR_HUMIDITY,
            NR_DEWPOINT,NR_PRECIPITATION,NR_RAIN,NR_SNOWFALL,NR_PRECIP_PROB,
            NR_WEATHERCODE,NR_PRESSURE_MSL,NR_SURFACE_PRESS,NR_CLOUDCOVER,
            NR_VISIBILITY,NR_WINDSPEED_10M,NR_WINDDIR_10M,NR_WINDGUSTS,
            NR_UV_INDEX,NR_SHORTWAVE_RAD
        ) VALUES (
            :id_location,:dt_forecast,:nr_temperature_2m,:nr_apparent_temp,:nr_humidity,
            :nr_dewpoint,:nr_precipitation,:nr_rain,:nr_snowfall,:nr_precip_prob,
            :nr_weathercode,:nr_pressure_msl,:nr_surface_press,:nr_cloudcover,
            :nr_visibility,:nr_windspeed_10m,:nr_winddir_10m,:nr_windgusts,
            :nr_uv_index,:nr_shortwave_rad
        )
    """,
        records,
    )
    return n


def save_daily(id_location: int, data: dict) -> int:
    d = data["daily"]
    n = len(d["time"])
    get = lambda k: d.get(k, [None] * n)
    records = [{"id_location": id_location, "dt_forecast": datetime.strptime(d["time"][i], "%Y-%m-%d").date(), "nr_temp_max": get("temperature_2m_max")[i], "nr_temp_min": get("temperature_2m_min")[i], "nr_apparent_max": get("apparent_temperature_max")[i], "nr_apparent_min": get("apparent_temperature_min")[i], "nr_sunrise": _ts(get("sunrise")[i]), "nr_sunset": _ts(get("sunset")[i]), "nr_precip_sum": get("precipitation_sum")[i], "nr_rain_sum": get("rain_sum")[i], "nr_precip_hours": get("precipitation_hours")[i], "nr_precip_prob_max": get("precipitation_probability_max")[i], "nr_windspeed_max": get("wind_speed_10m_max")[i], "nr_windgusts_max": get("wind_gusts_10m_max")[i], "nr_winddir_dom": get("wind_direction_10m_dominant")[i], "nr_shortwave_sum": get("shortwave_radiation_sum")[i], "nr_uv_max": get("uv_index_max")[i], "nr_weathercode": get("weather_code")[i]} for i in range(n)]
    execute_many("""MERGE INTO WTH_DAILY_FORECAST t USING DUAL ON (t.ID_LOCATION = :id_location AND t.DT_FORECAST = :dt_forecast) WHEN MATCHED THEN UPDATE SET NR_TEMP_MAX=:nr_temp_max,NR_TEMP_MIN=:nr_temp_min, NR_APPARENT_MAX=:nr_apparent_max,NR_APPARENT_MIN=:nr_apparent_min, NR_SUNRISE=:nr_sunrise,NR_SUNSET=:nr_sunset, NR_PRECIP_SUM=:nr_precip_sum,NR_RAIN_SUM=:nr_rain_sum, NR_PRECIP_HOURS=:nr_precip_hours,NR_PRECIP_PROB_MAX=:nr_precip_prob_max, NR_WINDSPEED_MAX=:nr_windspeed_max,NR_WINDGUSTS_MAX=:nr_windgusts_max, NR_WINDDIR_DOM=:nr_winddir_dom,NR_SHORTWAVE_SUM=:nr_shortwave_sum, NR_UV_MAX=:nr_uv_max,NR_WEATHERCODE=:nr_weathercode, DT_COLLECTED=SYSTIMESTAMP WHEN NOT MATCHED THEN INSERT (ID_LOCATION,DT_FORECAST,NR_TEMP_MAX,NR_TEMP_MIN,NR_APPARENT_MAX, NR_APPARENT_MIN,NR_SUNRISE,NR_SUNSET,NR_PRECIP_SUM,NR_RAIN_SUM, NR_PRECIP_HOURS,NR_PRECIP_PROB_MAX,NR_WINDSPEED_MAX,NR_WINDGUSTS_MAX, NR_WINDDIR_DOM,NR_SHORTWAVE_SUM,NR_UV_MAX,NR_WEATHERCODE) VALUES (:id_location,:dt_forecast,:nr_temp_max,:nr_temp_min,:nr_apparent_max, :nr_apparent_min,:nr_sunrise,:nr_sunset,:nr_precip_sum,:nr_rain_sum, :nr_precip_hours,:nr_precip_prob_max,:nr_windspeed_max,:nr_windgusts_max, :nr_winddir_dom,:nr_shortwave_sum,:nr_uv_max,:nr_weathercode)""", records)
    return n


def _log(id_location: int, status: str, records: int, message: str = None):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO WTH_COLLECTION_LOG (ID_LOCATION,NM_STATUS,NR_RECORDS,DS_MESSAGE) VALUES (:a,:b,:c,:d)", {"a": id_location, "b": status, "c": records, "d": message})


def collect_all() -> list[dict]:
    locations = execute_query("SELECT ID_LOCATION,NR_LATITUDE,NR_LONGITUDE,NM_TIMEZONE,NM_CITY FROM WTH_LOCATIONS")
    results = []
    for loc in locations:
        try:
            data = fetch_openmeteo(loc["nr_latitude"], loc["nr_longitude"], loc["nm_timezone"])
            h = save_hourly(loc["id_location"], data)
            d = save_daily(loc["id_location"], data)
            _log(loc["id_location"], "SUCCESS", h + d)
            results.append({"id_location": loc["id_location"], "city": loc["nm_city"], "status": "success", "records": h + d})
        except Exception as e:
            _log(loc["id_location"], "ERROR", 0, str(e)[:500])
            results.append({"id_location": loc["id_location"], "city": loc["nm_city"], "status": "error", "records": 0})
    return results
