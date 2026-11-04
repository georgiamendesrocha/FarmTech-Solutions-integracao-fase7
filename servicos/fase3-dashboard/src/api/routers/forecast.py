from typing import List

from fastapi import APIRouter, HTTPException, Query
from fastapi.concurrency import run_in_threadpool

from src.api.db import execute_query
from src.api.schemas import DailyForecast, HourlyForecast, Location

router = APIRouter(prefix="/forecast", tags=["Previsão"])


@router.get("/locations", response_model=List[Location])
async def list_locations():
    return await run_in_threadpool(
        execute_query,
        "SELECT ID_LOCATION,NM_CITY,NM_COUNTRY,NR_LATITUDE,NR_LONGITUDE,NM_TIMEZONE "
        "FROM WTH_LOCATIONS ORDER BY NM_CITY",
    )


@router.get("/current", response_model=HourlyForecast)
async def current_conditions(id_location: int = Query(default=1)):
    rows = await run_in_threadpool(
        execute_query,
        """
        SELECT DT_FORECAST,NR_TEMPERATURE_2M,NR_APPARENT_TEMP,NR_HUMIDITY,NR_DEWPOINT,
               NR_PRECIPITATION,NR_RAIN,NR_PRECIP_PROB,NR_WEATHERCODE,NR_PRESSURE_MSL,
               NR_CLOUDCOVER,NR_VISIBILITY,NR_WINDSPEED_10M,NR_WINDDIR_10M,
               NR_WINDGUSTS,NR_UV_INDEX,NR_SHORTWAVE_RAD
        FROM WTH_HOURLY_FORECAST
        WHERE ID_LOCATION = :id_location
          AND DT_FORECAST = (
              SELECT MAX(DT_FORECAST) FROM WTH_HOURLY_FORECAST
              WHERE ID_LOCATION = :id_location AND DT_FORECAST <= SYSTIMESTAMP)
    """,
        {"id_location": id_location},
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Sem dados para esta localização.")
    return rows[0]


@router.get("/hourly", response_model=List[HourlyForecast])
async def hourly_forecast(id_location: int = Query(default=1), hours: int = Query(default=24, ge=1, le=168)):
    return await run_in_threadpool(
        execute_query,
        """
        SELECT DT_FORECAST,NR_TEMPERATURE_2M,NR_APPARENT_TEMP,NR_HUMIDITY,NR_DEWPOINT,
               NR_PRECIPITATION,NR_RAIN,NR_PRECIP_PROB,NR_WEATHERCODE,NR_PRESSURE_MSL,
               NR_CLOUDCOVER,NR_VISIBILITY,NR_WINDSPEED_10M,NR_WINDDIR_10M,
               NR_WINDGUSTS,NR_UV_INDEX,NR_SHORTWAVE_RAD
        FROM WTH_HOURLY_FORECAST
        WHERE ID_LOCATION = :id_location
          AND DT_FORECAST BETWEEN SYSTIMESTAMP
              AND SYSTIMESTAMP + NUMTODSINTERVAL(:hours, 'HOUR')
        ORDER BY DT_FORECAST
    """,
        {"id_location": id_location, "hours": hours},
    )


@router.get("/daily", response_model=List[DailyForecast])
async def daily_forecast(id_location: int = Query(default=1)):
    return await run_in_threadpool(
        execute_query,
        """
        SELECT DT_FORECAST,NR_TEMP_MAX,NR_TEMP_MIN,NR_APPARENT_MAX,NR_APPARENT_MIN,
               NR_SUNRISE,NR_SUNSET,NR_PRECIP_SUM,NR_RAIN_SUM,NR_PRECIP_HOURS,
               NR_PRECIP_PROB_MAX,NR_WINDSPEED_MAX,NR_WINDGUSTS_MAX,NR_WINDDIR_DOM,
               NR_UV_MAX,NR_WEATHERCODE
        FROM WTH_DAILY_FORECAST
        WHERE ID_LOCATION = :id_location AND DT_FORECAST >= TRUNC(SYSDATE)
        ORDER BY DT_FORECAST
    """,
        {"id_location": id_location},
    )
