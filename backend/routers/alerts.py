from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from backend.db import get_db
from backend.utils.time import utc_now
from backend.utils.ids import oid_str, to_object_id
from backend.routers.auth import get_current_user

router = APIRouter(prefix="/alerts", tags=["alerts"])

class AlertCreateIn(BaseModel):
    tracked_product_id: str
    target_price: float | None = Field(default=None, ge=0)
    discount_threshold: float | None = Field(default=None, ge=0, le=100)
    notify_once: bool = True
    is_active: bool = True

class AlertPatchIn(BaseModel):
    target_price: float | None = Field(default=None, ge=0)
    discount_threshold: float | None = Field(default=None, ge=0, le=100)
    notify_once: bool | None = None
    is_active: bool | None = None

@router.post("")
async def create_alert(data: AlertCreateIn, user=Depends(get_current_user)):
    if data.target_price is None and data.discount_threshold is None:
        raise HTTPException(status_code=400, detail="Provide target_price and/or discount_threshold")

    db = get_db()
    pid = to_object_id(data.tracked_product_id)

    product = await db.tracked_products.find_one({"_id": pid, "user_id": user["_id"]})
    if not product:
        raise HTTPException(status_code=404, detail="Tracked product not found")

    doc = {
        "user_id": user["_id"],
        "tracked_product_id": pid,
        "target_price": data.target_price,
        "discount_threshold": data.discount_threshold,
        "notify_once": data.notify_once,
        "has_notified_once": False,
        "is_active": data.is_active,
        "created_at": utc_now(),
    }
    res = await db.alerts.insert_one(doc)
    doc["_id"] = res.inserted_id
    return {
    "id": oid_str(doc["_id"]),
    "user_id": oid_str(doc["user_id"]),
    "tracked_product_id": oid_str(doc["tracked_product_id"]),
    "target_price": doc.get("target_price"),
    "discount_threshold": doc.get("discount_threshold"),
    "notify_once": doc.get("notify_once", True),
    "has_notified_once": doc.get("has_notified_once", False),
    "is_active": doc.get("is_active", True),
    "created_at": doc.get("created_at"),
}


@router.get("")
async def list_alerts(user=Depends(get_current_user)):
    db = get_db()
    cursor = db.alerts.find({"user_id": user["_id"]}).sort("created_at", -1)
    out = []
    async for a in cursor:
        out.append({
            "id": oid_str(a["_id"]),
            "tracked_product_id": oid_str(a["tracked_product_id"]),
            "target_price": a.get("target_price"),
            "discount_threshold": a.get("discount_threshold"),
            "notify_once": a.get("notify_once", True),
            "has_notified_once": a.get("has_notified_once", False),
            "is_active": a.get("is_active", True),
            "created_at": a.get("created_at"),
        })
    return out

@router.patch("/{id}")
async def patch_alert(id: str, data: AlertPatchIn, user=Depends(get_current_user)):
    db = get_db()
    aid = to_object_id(id)
    alert = await db.alerts.find_one({"_id": aid, "user_id": user["_id"]})
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    update = {k: v for k, v in data.model_dump().items() if v is not None}
    if not update:
        return {"ok": True}

    await db.alerts.update_one({"_id": aid}, {"$set": update})
    return {"ok": True}

@router.delete("/{id}")
async def delete_alert(id: str, user=Depends(get_current_user)):
    db = get_db()
    aid = to_object_id(id)
    res = await db.alerts.delete_one({"_id": aid, "user_id": user["_id"]})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"ok": True}
