# backend/routers/requests.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from backend.db import get_db
from backend.utils.ids import oid_str, to_object_id
from backend.routers.auth import get_current_user

from backend.services.request_service import (
    create_request,
    mark_request_fulfilled,
    process_one_request_now,  # ✅ synchronous (await) search
)

from backend.routers.products import TrackIn, track_product

router = APIRouter(prefix="/requests", tags=["requests"])


class RequestIn(BaseModel):
    platform: str
    query: str
    max_price: Optional[float] = None

    # ✅ NEW
    location: Optional[str] = None   # e.g. "lagos", "abuja", etc (slug)
    limit: Optional[int] = 50        # how many results you want back (max 100)


class SelectIn(BaseModel):
    url: str


@router.post("")
async def create_track_request(data: RequestIn, user=Depends(get_current_user)):
    platform = (data.platform or "").lower().strip()
    if platform not in ("jiji",):
        raise HTTPException(status_code=400, detail="Unsupported platform (MVP: jiji only)")

    q = (data.query or "").strip()
    if len(q) < 3:
        raise HTTPException(status_code=400, detail="Query too short")

    limit = int(data.limit or 50)
    if limit < 1:
        limit = 1
    if limit > 100:
        limit = 100

    location = (data.location or "").strip() or None

    # 1) Create request doc
    req = await create_request(
        user_id=user["_id"],
        platform=platform,
        query=q,
        max_price=data.max_price,
        location=location,  # ✅ new
        limit=limit,        # ✅ new
    )

    await process_one_request_now(req["_id"])


    # 3) Return updated doc
    db = get_db()
    updated = await db.track_requests.find_one({"_id": req["_id"], "user_id": user["_id"]})
    if not updated:
        raise HTTPException(status_code=500, detail="Failed to load request after search")

    return {
        "id": oid_str(updated["_id"]),
        "platform": updated.get("platform"),
        "query": updated.get("query"),
        "location": updated.get("location"),
        "max_price": updated.get("max_price"),
        "limit": updated.get("limit"),
        "status": updated.get("status"),
        "results": updated.get("results", []),
        "error_message": updated.get("error_message"),
        "blocked_reason": updated.get("blocked_reason"),
        "created_at": updated.get("created_at"),
        "updated_at": updated.get("updated_at"),
    }


@router.get("")
async def list_my_requests(user=Depends(get_current_user)):
    db = get_db()
    cursor = db.track_requests.find({"user_id": user["_id"]}).sort("created_at", -1).limit(50)

    out = []
    async for r in cursor:
        out.append({
            "id": oid_str(r["_id"]),
            "platform": r.get("platform"),
            "query": r.get("query"),
            "location": r.get("location"),
            "max_price": r.get("max_price"),
            "limit": r.get("limit"),
            "status": r.get("status"),
            "result_count": len(r.get("results", [])),
            "created_at": r.get("created_at"),
            "updated_at": r.get("updated_at"),
            "error_message": r.get("error_message"),
            "blocked_reason": r.get("blocked_reason"),
        })
    return out


@router.get("/{id}")
async def request_detail(id: str, user=Depends(get_current_user)):
    db = get_db()
    rid = to_object_id(id)
    r = await db.track_requests.find_one({"_id": rid, "user_id": user["_id"]})
    if not r:
        raise HTTPException(status_code=404, detail="Request not found")

    return {
        "id": oid_str(r["_id"]),
        "platform": r.get("platform"),
        "query": r.get("query"),
        "location": r.get("location"),
        "max_price": r.get("max_price"),
        "limit": r.get("limit"),
        "status": r.get("status"),
        "results": r.get("results", []),
        "selected_url": r.get("selected_url"),
        "error_message": r.get("error_message"),
        "blocked_reason": r.get("blocked_reason"),
        "created_at": r.get("created_at"),
        "updated_at": r.get("updated_at"),
    }


@router.post("/{id}/select")
async def select_candidate(id: str, body: SelectIn, user=Depends(get_current_user)):
    db = get_db()
    rid = to_object_id(id)
    r = await db.track_requests.find_one({"_id": rid, "user_id": user["_id"]})
    if not r:
        raise HTTPException(status_code=404, detail="Request not found")

    url = (body.url or "").strip()
    if not url.startswith("http"):
        raise HTTPException(status_code=400, detail="Invalid URL")

    await mark_request_fulfilled(rid, url)
    tracked = await track_product(TrackIn(url=url, platform=r["platform"]), user=user)
    return {"ok": True, "tracked": tracked}


@router.delete("/{id}")
async def delete_request(id: str, user=Depends(get_current_user)):
    db = get_db()
    rid = to_object_id(id)
    res = await db.track_requests.delete_one({"_id": rid, "user_id": user["_id"]})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Request not found")
    return {"ok": True}
