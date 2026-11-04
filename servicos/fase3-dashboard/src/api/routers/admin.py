from typing import TYPE_CHECKING, List

from fastapi import APIRouter, Query
from fastapi.concurrency import run_in_threadpool

from src.api.db import execute_query, ping
from src.api.schemas import CollectResponse, CollectionLog, HealthResponse

if TYPE_CHECKING:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler

router = APIRouter(prefix="/admin", tags=["Administração"])
_scheduler = None


def set_scheduler(s):
    global _scheduler
    _scheduler = s


@router.post("/collect", response_model=CollectResponse)
async def trigger_collect():
    from src.api.collector import collect_all

    results = await run_in_threadpool(collect_all)
    total = sum(r.get("records", 0) for r in results)
    return CollectResponse(status="success", message="Coleta manual concluída.", locations_processed=len(results), total_records=total)


@router.get("/logs", response_model=List[CollectionLog])
async def collection_logs(limit: int = Query(default=50, ge=1, le=500)):
    return await run_in_threadpool(
        execute_query,
        """
        SELECT ID_LOG,ID_LOCATION,DT_COLLECTION,NM_STATUS,NR_RECORDS,DS_MESSAGE
        FROM WTH_COLLECTION_LOG
        ORDER BY DT_COLLECTION DESC
        FETCH FIRST :limit ROWS ONLY
    """,
        {"limit": limit},
    )


@router.get("/health", response_model=HealthResponse)
async def health():
    db_ok = await run_in_threadpool(ping)
    next_run = None
    if _scheduler:
        job = _scheduler.get_job("weather_collect")
        if job and job.next_run_time:
            next_run = job.next_run_time.strftime("%Y-%m-%d %H:%M:%S %Z")
    return HealthResponse(status="ok" if db_ok else "degraded", scheduler_running=bool(_scheduler and _scheduler.running), next_collection=next_run, db_ok=db_ok)
