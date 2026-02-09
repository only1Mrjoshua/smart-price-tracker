from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from backend.config import settings
from backend.db import ensure_indexes
from backend.services.scheduler_service import run_check_cycle
from backend.routers.auth import router as auth_router
from backend.routers.products import router as products_router
from backend.routers.alerts import router as alerts_router
from backend.routers.notifications import router as notifications_router
from backend.routers.admin import router as admin_router
from backend.services.logging_service import log_job

app = FastAPI(title=settings.APP_NAME)

# MVP CORS: frontend is static files opened in browser
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

scheduler = AsyncIOScheduler()

@app.on_event("startup")
async def startup():
    await ensure_indexes()

    # APScheduler job
    scheduler.add_job(
        func=_job_wrapper,
        trigger=IntervalTrigger(minutes=settings.CHECK_INTERVAL_MINUTES),
        id="price_check_cycle",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()

@app.on_event("shutdown")
async def shutdown():
    if scheduler.running:
        scheduler.shutdown(wait=False)

async def _job_wrapper():
    try:
        await run_check_cycle()
    except Exception as e:
        await log_job("check_cycle", None, None, "error", str(e))

app.include_router(auth_router, prefix=settings.API_PREFIX)
app.include_router(products_router, prefix=settings.API_PREFIX)
app.include_router(alerts_router, prefix=settings.API_PREFIX)
app.include_router(notifications_router, prefix=settings.API_PREFIX)
app.include_router(admin_router, prefix=settings.API_PREFIX)
