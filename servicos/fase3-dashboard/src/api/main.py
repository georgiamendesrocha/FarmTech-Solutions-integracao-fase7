import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.db import execute_query, get_conn
from src.api.routers import admin, forecast

load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

PATO_BRANCO = {"nm_city": "Pato Branco", "nm_country": "Brasil", "nr_latitude": -26.2312, "nr_longitude": -52.6711, "nm_timezone": "America/Sao_Paulo"}
scheduler = AsyncIOScheduler(timezone="America/Sao_Paulo")


def ensure_pato_branco():
    rows = execute_query("SELECT ID_LOCATION FROM WTH_LOCATIONS WHERE NM_CITY=:c AND NM_COUNTRY=:co", {"c": PATO_BRANCO["nm_city"], "co": PATO_BRANCO["nm_country"]})
    if rows:
        return
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO WTH_LOCATIONS (NM_CITY,NM_COUNTRY,NR_LATITUDE,NR_LONGITUDE,NM_TIMEZONE) VALUES (:nm_city,:nm_country,:nr_latitude,:nr_longitude,:nm_timezone)", PATO_BRANCO)


async def scheduled_collect():
    from src.api.collector import collect_all

    await asyncio.get_event_loop().run_in_executor(None, collect_all)


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_pato_branco()
    await scheduled_collect()
    scheduler.add_job(scheduled_collect, trigger=IntervalTrigger(minutes=5), id="weather_collect", replace_existing=True)
    scheduler.start()
    admin.set_scheduler(scheduler)
    yield
    scheduler.shutdown()


app = FastAPI(title="Weather Analytics API", description="API de previsão do tempo — Open-Meteo + Oracle DB", version="2.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(forecast.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")


@app.get("/", tags=["Root"])
async def root():
    return {"message": "Weather Analytics API v2", "docs": "/docs"}
