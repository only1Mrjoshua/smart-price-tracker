from fastapi import APIRouter, Depends
from backend.db import get_db
from backend.utils.ids import oid_str
from backend.routers.auth import get_current_user

router = APIRouter(prefix="/notifications", tags=["notifications"])

@router.get("")
async def list_notifications(user=Depends(get_current_user)):
    db = get_db()
    cursor = db.notifications.find({"user_id": user["_id"]}).sort("sent_at", -1).limit(100)
    out = []
    async for n in cursor:
        out.append({
            "id": oid_str(n["_id"]),
            "tracked_product_id": oid_str(n["tracked_product_id"]) if n.get("tracked_product_id") else None,
            "message": n.get("message"),
            "channel": n.get("channel"),
            "sent_at": n.get("sent_at"),
            "status": n.get("status"),
        })
    return out
