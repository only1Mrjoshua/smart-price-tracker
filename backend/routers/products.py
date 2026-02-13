from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, HttpUrl
from backend.db import get_db
from backend.utils.time import utc_now, days_ago
from backend.utils.ids import oid_str, to_object_id
from backend.routers.auth import get_current_user
from backend.services.scheduler_service import check_one_product

router = APIRouter(prefix="/products", tags=["products"])

class TrackIn(BaseModel):
    url: HttpUrl
    platform: str  # jumia|konga|amazon|ebay|jiji

@router.post("/track")
async def track_product(data: TrackIn, user=Depends(get_current_user)):
    db = get_db()
    platform = data.platform.lower().strip()
    if platform not in ("jumia", "konga", "amazon", "ebay", "jiji"):
        raise HTTPException(status_code=400, detail="Unsupported platform")

    doc = {
        "user_id": user["_id"],
        "platform": platform,
        "url": str(data.url),
        "title": None,
        "image": None,
        "status": "ok",
        "current_price": None,
        "currency": None,
        "reference_price": None,
        "last_checked": None,
        "created_at": utc_now(),
    }

    try:
        res = await db.tracked_products.insert_one(doc)
    except Exception:
        raise HTTPException(status_code=409, detail="You are already tracking this URL")

    tracked = await db.tracked_products.find_one({"_id": res.inserted_id})
    # immediate check (best effort)
    await check_one_product(tracked)

    tracked = await db.tracked_products.find_one({"_id": res.inserted_id})
    return {
        "id": oid_str(tracked["_id"]),
        "platform": tracked["platform"],
        "url": tracked["url"],
        "title": tracked.get("title"),
        "image": tracked.get("image"),
        "status": tracked.get("status"),
        "current_price": tracked.get("current_price"),
        "currency": tracked.get("currency"),
        "last_checked": tracked.get("last_checked"),
    }

@router.get("")
async def list_products(user=Depends(get_current_user)):
    db = get_db()
    cursor = db.tracked_products.find({"user_id": user["_id"]}).sort("created_at", -1)
    out = []
    async for p in cursor:
        out.append({
            "id": oid_str(p["_id"]),
            "platform": p["platform"],
            "url": p["url"],
            "title": p.get("title"),
            "image": p.get("image"),
            "status": p.get("status"),
            "current_price": p.get("current_price"),
            "currency": p.get("currency"),
            "last_checked": p.get("last_checked"),
            "created_at": p.get("created_at"),
        })
    return out

@router.get("/{id}")
async def product_detail(id: str, user=Depends(get_current_user)):
    db = get_db()
    pid = to_object_id(id)
    p = await db.tracked_products.find_one({"_id": pid, "user_id": user["_id"]})
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")

    since = days_ago(180)
    hist_cursor = db.price_history.find({"tracked_product_id": pid, "timestamp": {"$gte": since}}).sort("timestamp", 1)
    history = []
    async for h in hist_cursor:
        history.append({
            "timestamp": h["timestamp"],
            "price": h["price"],
            "currency": h.get("currency", p.get("currency")),
        })

    return {
        "id": oid_str(p["_id"]),
        "platform": p["platform"],
        "url": p["url"],
        "title": p.get("title"),
        "image": p.get("image"),
        "status": p.get("status"),
        "current_price": p.get("current_price"),
        "currency": p.get("currency"),
        "reference_price": p.get("reference_price"),
        "blocked_reason": p.get("blocked_reason"),
        "last_checked": p.get("last_checked"),
        "created_at": p.get("created_at"),
        "history_6m": history,
    }

@router.delete("/{id}")
async def delete_product(id: str, user=Depends(get_current_user)):
    db = get_db()
    pid = to_object_id(id)
    p = await db.tracked_products.find_one({"_id": pid, "user_id": user["_id"]})
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")

    await db.tracked_products.delete_one({"_id": pid})
    await db.price_history.delete_many({"tracked_product_id": pid})
    await db.alerts.delete_many({"tracked_product_id": pid, "user_id": user["_id"]})
    await db.notifications.delete_many({"tracked_product_id": pid, "user_id": user["_id"]})
    return {"ok": True}
