from fastapi import APIRouter, HTTPException, Depends
from backend.db import get_db
from backend.utils.ids import oid_str, to_object_id
from backend.routers.auth import get_current_user
from backend.services.scheduler_service import force_recheck

router = APIRouter(prefix="/admin", tags=["admin"])

def require_admin(user):
    if user.get("role") != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

@router.get("/users")
async def admin_users(user=Depends(get_current_user)):
    require_admin(user)
    db = get_db()
    cursor = db.users.find({}).sort("created_at", -1)
    out = []
    async for u in cursor:
        out.append({
            "id": oid_str(u["_id"]),
            "name": u.get("name"),
            "email": u.get("email"),
            "role": u.get("role"),
            "created_at": u.get("created_at"),
        })
    return out

@router.get("/products")
async def admin_products(user=Depends(get_current_user)):
    require_admin(user)
    db = get_db()
    cursor = db.tracked_products.find({}).sort("created_at", -1).limit(500)
    out = []
    async for p in cursor:
        out.append({
            "id": oid_str(p["_id"]),
            "user_id": oid_str(p["user_id"]),
            "platform": p.get("platform"),
            "url": p.get("url"),
            "title": p.get("title"),
            "status": p.get("status"),
            "current_price": p.get("current_price"),
            "currency": p.get("currency"),
            "last_checked": p.get("last_checked"),
            "blocked_reason": p.get("blocked_reason"),
        })
    return out

@router.get("/jobs")
async def admin_jobs(user=Depends(get_current_user)):
    require_admin(user)
    db = get_db()
    cursor = db.jobs_log.find({}).sort("ran_at", -1).limit(200)
    out = []
    async for j in cursor:
        out.append({
            "id": oid_str(j["_id"]),
            "job_type": j.get("job_type"),
            "platform": j.get("platform"),
            "tracked_product_id": j.get("tracked_product_id"),
            "status": j.get("status"),
            "error_message": j.get("error_message"),
            "ran_at": j.get("ran_at"),
        })
    return out

@router.post("/recheck/{product_id}")
async def admin_recheck(product_id: str, user=Depends(get_current_user)):
    require_admin(user)
    pid = to_object_id(product_id)
    await force_recheck(pid)
    return {"ok": True}
