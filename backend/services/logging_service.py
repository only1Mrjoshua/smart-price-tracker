from backend.db import get_db
from backend.utils.time import utc_now

async def log_job(job_type: str, platform: str | None, tracked_product_id: str | None,
                  status: str, error_message: str | None = None):
    db = get_db()
    await db.jobs_log.insert_one({
        "job_type": job_type,
        "platform": platform,
        "tracked_product_id": tracked_product_id,
        "status": status,
        "error_message": error_message,
        "ran_at": utc_now(),
    })
