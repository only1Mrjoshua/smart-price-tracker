# backend/routers/requests.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
import asyncio

from backend.db import get_db
from backend.utils.ids import oid_str, to_object_id
from backend.utils.time import utc_now
from backend.routers.auth import get_current_user

from backend.services.request_service import (
    create_request,
    mark_request_fulfilled,
    process_one_request,  # expects a FULL request dict
)

from backend.routers.products import TrackIn, track_product


router = APIRouter(prefix="/requests", tags=["requests"])


class RequestIn(BaseModel):
    platform: str
    query: str
    max_price: Optional[float] = None


class SelectIn(BaseModel):
    url: str


async def _run_request_search_now(request_id):
    """
    Fetch the request doc, then call process_one_request(doc).
    (Fixes: passing ObjectId directly caused: 'ObjectId' object is not subscriptable)
    """
    db = get_db()
    req = await db.track_requests.find_one({"_id": request_id})
    if not req:
        return
    await process_one_request(req)


@router.post("")
async def create_track_request(data: RequestIn, user=Depends(get_current_user)):
    platform = (data.platform or "").lower().strip()
    if platform not in ("jiji",):
        raise HTTPException(
            status_code=400,
            detail="Unsupported platform for request search (MVP: jiji only)",
        )

    q = (data.query or "").strip()
    if len(q) < 3:
        raise HTTPException(status_code=400, detail="Query too short")

    # 1) Create request doc
    req = await create_request(user["_id"], platform, q, data.max_price)

    db = get_db()

    # 2) Mark as searching immediately (UX)
    await db.track_requests.update_one(
        {"_id": req["_id"], "user_id": user["_id"]},
        {"$set": {"status": "searching", "updated_at": utc_now()}},
    )

    # 3) Run search immediately (fire-and-forget)
    asyncio.create_task(_run_request_search_now(req["_id"]))

    # 4) Return immediately
    return {
        "id": oid_str(req["_id"]),
        "platform": req["platform"],
        "query": req["query"],
        "max_price": req.get("max_price"),
        "status": "searching",
        "results": [],
        "created_at": req.get("created_at"),
        "updated_at": utc_now(),
    }


@router.get("")
async def list_my_requests(user=Depends(get_current_user)):
    db = get_db()
    cursor = (
        db.track_requests.find({"user_id": user["_id"]})
        .sort("created_at", -1)
        .limit(50)
    )

    out = []
    async for r in cursor:
        out.append(
            {
                "id": oid_str(r["_id"]),
                "platform": r.get("platform"),
                "query": r.get("query"),
                "max_price": r.get("max_price"),
                "status": r.get("status"),
                "result_count": len(r.get("results", [])),
                "created_at": r.get("created_at"),
                "updated_at": r.get("updated_at"),
                "error_message": r.get("error_message"),
                "blocked_reason": r.get("blocked_reason"),
            }
        )
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
        "max_price": r.get("max_price"),
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

    # Mark fulfilled
    await mark_request_fulfilled(rid, url)

    # Convert to normal tracking using existing /products/track logic
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
