from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class Location(BaseModel):
    id_location: int
    nm_city: str
    nm_country: str
    nr_latitude: float
    nr_longitude: float
    nm_timezone: str


class HourlyForecast(BaseModel):
    dt_forecast: datetime
    nr_temperature_2m: Optional[float] = None
    nr_apparent_temp: Optional[float] = None
    nr_humidity: Optional[float] = None
    nr_dewpoint: Optional[float] = None
    nr_precipitation: Optional[float] = None
    nr_rain: Optional[float] = None
    nr_precip_prob: Optional[float] = None
    nr_weathercode: Optional[int] = None
    nr_pressure_msl: Optional[float] = None
    nr_cloudcover: Optional[float] = None
    nr_visibility: Optional[float] = None
    nr_windspeed_10m: Optional[float] = None
    nr_winddir_10m: Optional[float] = None
    nr_windgusts: Optional[float] = None
    nr_uv_index: Optional[float] = None
    nr_shortwave_rad: Optional[float] = None


class DailyForecast(BaseModel):
    dt_forecast: date
    nr_temp_max: Optional[float] = None
    nr_temp_min: Optional[float] = None
    nr_apparent_max: Optional[float] = None
    nr_apparent_min: Optional[float] = None
    nr_sunrise: Optional[datetime] = None
    nr_sunset: Optional[datetime] = None
    nr_precip_sum: Optional[float] = None
    nr_rain_sum: Optional[float] = None
    nr_precip_hours: Optional[float] = None
    nr_precip_prob_max: Optional[float] = None
    nr_windspeed_max: Optional[float] = None
    nr_windgusts_max: Optional[float] = None
    nr_winddir_dom: Optional[float] = None
    nr_uv_max: Optional[float] = None
    nr_weathercode: Optional[int] = None


class CollectionLog(BaseModel):
    id_log: int
    id_location: Optional[int] = None
    dt_collection: datetime
    nm_status: str
    nr_records: Optional[int] = None
    ds_message: Optional[str] = None


class CollectResponse(BaseModel):
    status: str
    message: str
    locations_processed: int
    total_records: int


class HealthResponse(BaseModel):
    status: str
    scheduler_running: bool
    next_collection: Optional[str] = None
    db_ok: bool
