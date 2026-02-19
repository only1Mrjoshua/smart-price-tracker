from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
import asyncio
import logging

from backend.config import settings
from backend.db import ensure_indexes
from backend.services.scheduler_service import run_check_cycle
from backend.routers.auth import router as auth_router
from backend.routers.products import router as products_router
from backend.routers.alerts import router as alerts_router
from backend.routers.notifications import router as notifications_router
from backend.routers.admin import router as admin_router
from backend.services.logging_service import log_job
from backend.routers.requests import router as requests_router

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.APP_NAME)

# MVP CORS: frontend is static files opened in browser
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables
scheduler = None
background_task = None

@app.on_event("startup")
async def startup():
    global scheduler, background_task
    
    await ensure_indexes()
    
    print("\n" + "="*60)
    print(f"🚀 SERVER STARTING AT {datetime.now()}")
    print(f"📊 CHECK_INTERVAL_MINUTES = {settings.CHECK_INTERVAL_MINUTES}")
    print("="*60)
    
    # OPTION 1: Use APScheduler (working now)
    try:
        scheduler = AsyncIOScheduler()
        
        # Add the job
        scheduler.add_job(
            func=_job_wrapper,
            trigger=IntervalTrigger(minutes=settings.CHECK_INTERVAL_MINUTES),
            id="price_check_cycle",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        
        # Start scheduler
        scheduler.start()
        print("✅ APScheduler started")
        
        # List jobs
        jobs = scheduler.get_jobs()
        if jobs:
            print(f"📋 Scheduled job: {jobs[0].id}")
            print(f"⏰ Next run: {jobs[0].next_run_time}")
        else:
            print("⚠️ No jobs scheduled in APScheduler")
            
    except Exception as e:
        print(f"❌ APScheduler failed to start: {e}")
        scheduler = None
    
    # OPTION 2: COMMENT OUT the backup task since APScheduler is working
    # print("🔄 Starting backup background task...")
    # background_task = asyncio.create_task(background_check_cycle())
    # print("✅ Backup background task started")
    
    # OPTION 3: Run once immediately on startup
    print("⚡ Running immediate price check on startup...")
    asyncio.create_task(_job_wrapper())
    
    print("="*60 + "\n")

@app.on_event("shutdown")
async def shutdown():
    global background_task
    
    print("\n" + "="*60)
    print(f"🛑 SERVER SHUTTING DOWN AT {datetime.now()}")
    
    # Shutdown APScheduler
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=False)
        print("✅ APScheduler shutdown")
    
    # Cancel background task
    if background_task and not background_task.done():
        background_task.cancel()
        print("✅ Background task cancelled")
    
    print("="*60 + "\n")

async def _job_wrapper():
    """Wrapper for the price check job with logging"""
    try:
        print(f"\n🔄 Running price check cycle at {datetime.now()}")
        await run_check_cycle()
        print(f"✅ Price check cycle completed at {datetime.now()}\n")
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Error in price check cycle: {error_msg}")
        await log_job("check_cycle", None, None, "error", error_msg)

async def background_check_cycle():
    """Simple background task that runs every X minutes (backup for APScheduler)"""
    while True:
        try:
            # Wait for the interval
            await asyncio.sleep(settings.CHECK_INTERVAL_MINUTES * 60)
            
            # Run the check cycle
            print(f"\n🔄 [BACKGROUND] Running price check at {datetime.now()}")
            await run_check_cycle()
            print(f"✅ [BACKGROUND] Check completed at {datetime.now()}\n")
            
        except asyncio.CancelledError:
            print("🛑 Background task cancelled")
            break
        except Exception as e:
            print(f"❌ [BACKGROUND] Error: {e}")
            # Continue running despite errors
            continue

# Debug endpoint to check scheduler status
@app.get("/debug/scheduler")
async def debug_scheduler():
    status = {
        "apscheduler_running": scheduler.running if scheduler else False,
        "background_task_running": background_task is not None and not background_task.done() if background_task else False,
        "check_interval_minutes": settings.CHECK_INTERVAL_MINUTES,
        "current_time": str(datetime.now()),
    }
    
    if scheduler and scheduler.running:
        jobs = scheduler.get_jobs()
        status["apscheduler_jobs"] = [{"id": job.id, "next_run": str(job.next_run_time)} for job in jobs]
    else:
        status["apscheduler_jobs"] = []
    
    return status

# Manual trigger endpoint (useful for testing)
@app.post("/debug/force-check")
async def force_check():
    """Manually trigger a price check cycle"""
    print(f"\n⚡ Manual force check triggered at {datetime.now()}")
    asyncio.create_task(_job_wrapper())
    return {"message": "Check cycle started", "time": str(datetime.now())}

# Include all routers
app.include_router(auth_router, prefix=settings.API_PREFIX)
app.include_router(products_router, prefix=settings.API_PREFIX)
app.include_router(alerts_router, prefix=settings.API_PREFIX)
app.include_router(notifications_router, prefix=settings.API_PREFIX)
app.include_router(admin_router, prefix=settings.API_PREFIX)
app.include_router(requests_router, prefix=settings.API_PREFIX)