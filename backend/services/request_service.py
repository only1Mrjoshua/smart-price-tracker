# backend/services/request_service.py

from typing import Dict, List, Optional, Tuple, Union
import re
import httpx
from bson import ObjectId

from backend.db import get_db
from backend.utils.time import utc_now, days_ago
from backend.services.robots_service import allowed_by_robots
from backend.services.logging_service import log_job

# Your searcher (we will update its signature to accept location + page)
from backend.searchers.jiji_search import build_jiji_search_url, parse_jiji_search_results

UA = "Mozilla/5.0 (compatible; SmartPriceTracker/0.1; +respect-robots)"


SEARCHERS = {
    "jiji": {
        "build_url": build_jiji_search_url,
        "parse": parse_jiji_search_results,
        "base_url": "https://jiji.ng",
    }
}

# -------------------------
# Relevance filtering (your original)
# -------------------------

_STOPWORDS = {
    "a", "an", "and", "or", "the", "for", "to", "of", "in", "on", "with",
    "buy", "sale", "used", "new", "brand", "original", "london", "lagos",
    "abuja", "nigeria", "naija"
}

def _normalize_text(s: str) -> str:
    s = (s or "").lower().strip()
    s = s.replace("₦", " ")
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s

def _tokenize_query(query: str) -> List[str]:
    q = _normalize_text(query)
    tokens = [t for t in q.split(" ") if t and t not in _STOPWORDS]
    return tokens[:12]

def _tokenize_title(title: str) -> List[str]:
    t = _normalize_text(title)
    return [x for x in t.split(" ") if x]

def _score_candidate(query_tokens: List[str], title: str) -> Tuple[int, int]:
    if not title:
        return (0, 0)

    title_norm = _normalize_text(title)
    title_tokens = set(_tokenize_title(title))
    qset = set(query_tokens)

    matches = 0
    score = 0

    for qt in qset:
        if qt in title_tokens:
            matches += 1
            score += 10

    q_phrase = " ".join(query_tokens).strip()
    if q_phrase and q_phrase in title_norm:
        score += 20

    q_nums = [t for t in query_tokens if t.isdigit()]
    for n in q_nums:
        if n in title_tokens:
            score += 8

    return (score, matches)

def _apply_filters_and_rank(
    candidates: List[Dict],
    query: str,
    max_price: Optional[float],
) -> List[Dict]:
    q_tokens = _tokenize_query(query)
    if not q_tokens:
        return []

    filtered: List[Dict] = []

    for c in candidates:
        title = c.get("title") or ""
        price = c.get("price")

        # Max price filter
        if max_price is not None:
            if price is None:
                continue
            try:
                if float(price) > float(max_price):
                    continue
            except Exception:
                continue

        score, matches = _score_candidate(q_tokens, title)

        required_matches = 2 if len(q_tokens) >= 2 else 1
        if matches < required_matches:
            continue

        c["_score"] = score
        c["_matches"] = matches
        filtered.append(c)

    filtered.sort(
        key=lambda x: (x.get("_score", 0), -(x.get("_matches", 0))),
        reverse=True
    )

    for c in filtered:
        c.pop("_score", None)
        c.pop("_matches", None)

    return filtered


# -------------------------
# Helpers (NEW)
# -------------------------

def _dedupe_by_url(items: List[Dict]) -> List[Dict]:
    seen = set()
    out = []
    for it in items:
        u = (it.get("url") or "").strip()
        if not u or u in seen:
            continue
        seen.add(u)
        out.append(it)
    return out


# -------------------------
# DB logic (UPDATED: store limit + location)
# -------------------------

async def create_request(
    user_id,
    platform: str,
    query: str,
    max_price: Optional[float],
    location: Optional[str] = None,
    limit: int = 50,
) -> Dict:
    db = get_db()
    now = utc_now()

    lim = int(limit or 50)
    if lim < 1:
        lim = 1
    if lim > 100:
        lim = 100

    loc = (location or "").strip() or None

    doc = {
        "user_id": user_id,
        "platform": platform,
        "query": query,
        "location": loc,         # ✅ NEW
        "limit": lim,            # ✅ NEW
        "max_price": float(max_price) if max_price is not None else None,
        "status": "pending",
        "results": [],
        "selected_url": None,
        "error_message": None,
        "blocked_reason": None,
        "next_retry_at": None,
        "created_at": now,
        "updated_at": now,
    }
    res = await db.track_requests.insert_one(doc)
    return await db.track_requests.find_one({"_id": res.inserted_id})


async def _fetch_html(url: str) -> str:
    async with httpx.AsyncClient(
        timeout=25.0,
        follow_redirects=True,
        headers={"User-Agent": UA},
    ) as client:
        r = await client.get(url)
        r.raise_for_status()
        return r.text


# ✅ NEW: run instantly and WAIT (used by POST /requests so it returns results immediately)
async def process_one_request_now(req_id: ObjectId) -> None:
    await process_one_request(req_id)


# -------------------------
# Search worker (UPDATED: paging + location + limit)
# -------------------------

async def process_one_request(req: Union[ObjectId, Dict]) -> None:
    db = get_db()

    # allow req to be either ObjectId OR full request document
    if isinstance(req, ObjectId):
        rid = req
        req = await db.track_requests.find_one({"_id": rid})
        if not req:
            return
    else:
        rid = req.get("_id")
        if not rid:
            return

    platform = (req.get("platform") or "").lower().strip()

    if platform not in SEARCHERS:
        await db.track_requests.update_one(
            {"_id": rid},
            {"$set": {
                "status": "error",
                "error_message": "Unsupported platform for request search",
                "updated_at": utc_now()
            }}
        )
        await log_job("search_request", platform, str(rid), "error", "Unsupported platform")
        return

    next_retry_at = req.get("next_retry_at")
    if next_retry_at and next_retry_at > utc_now():
        return

    await db.track_requests.update_one(
        {"_id": rid},
        {"$set": {"status": "searching", "updated_at": utc_now()}}
    )

    build_url = SEARCHERS[platform]["build_url"]
    parse_fn = SEARCHERS[platform]["parse"]
    base_url = SEARCHERS[platform]["base_url"]

    query = (req.get("query") or "").strip()
    if not query:
        await db.track_requests.update_one(
            {"_id": rid},
            {"$set": {"status": "error", "error_message": "Empty query", "updated_at": utc_now()}}
        )
        return

    max_price = req.get("max_price")
    limit = int(req.get("limit") or 50)
    if limit < 1:
        limit = 1
    if limit > 100:
        limit = 100

    location = (req.get("location") or "").strip() or None

    # ✅ MULTI-PAGE: keep fetching until we collect enough ranked results
    # Tune these values as needed
    max_pages = 8                # usually enough to get 50+ candidates
    hard_candidate_cap = 400     # prevent runaway memory

    try:
        all_candidates: List[Dict] = []

        for page in range(1, max_pages + 1):
            # ✅ build URL WITH location + page
            # Your build_jiji_search_url MUST accept: (query, location=None, page=1)
            search_url = build_url(query, location=location, page=page)

            if not search_url:
                break

            robots_ok = await allowed_by_robots(search_url)
            if not robots_ok:
                await db.track_requests.update_one(
                    {"_id": rid},
                    {"$set": {
                        "status": "blocked",
                        "blocked_reason": "robots.txt disallow",
                        "updated_at": utc_now(),
                        "next_retry_at": days_ago(-1),
                    }}
                )
                await log_job("search_request", platform, str(rid), "blocked", "robots.txt disallow")
                return

            html = await _fetch_html(search_url)
            page_candidates = parse_fn(html, base_url=base_url)

            if not page_candidates:
                break

            all_candidates.extend(page_candidates)
            all_candidates = _dedupe_by_url(all_candidates)

            if len(all_candidates) >= hard_candidate_cap:
                break

            # We don’t stop based on “limit” yet, because ranking happens after filters.
            # But if we already have a lot, we can stop early.
            if len(all_candidates) >= max(120, limit * 4):
                break

        ranked = _apply_filters_and_rank(
            candidates=all_candidates,
            query=query,
            max_price=max_price,
        )

        # ✅ return/store ALL matches up to `limit` (e.g. 50)
        final_results = ranked[:limit]

        await db.track_requests.update_one(
            {"_id": rid},
            {"$set": {
                "status": "options_found",
                "results": final_results,
                "error_message": None,
                "blocked_reason": None,
                "updated_at": utc_now(),
                "next_retry_at": None,
            }}
        )
        await log_job("search_request", platform, str(rid), "ok", f"kept={len(final_results)} pages={max_pages}")

    except httpx.HTTPStatusError as e:
        code = e.response.status_code
        await db.track_requests.update_one(
            {"_id": rid},
            {"$set": {
                "status": "blocked" if code in (401, 403, 429) else "error",
                "error_message": f"HTTP error: {code}",
                "updated_at": utc_now(),
                "next_retry_at": days_ago(-1),
            }}
        )
        await log_job("search_request", platform, str(rid), "error", f"HTTP {code}")

    except Exception as e:
        await db.track_requests.update_one(
            {"_id": rid},
            {"$set": {
                "status": "error",
                "error_message": str(e),
                "updated_at": utc_now(),
                "next_retry_at": days_ago(-1),
            }}
        )
        await log_job("search_request", platform, str(rid), "error", str(e))


async def process_pending_requests() -> None:
    db = get_db()
    cursor = db.track_requests.find({"status": {"$in": ["pending", "blocked"]}}).sort("updated_at", 1).limit(10)
    async for req in cursor:
        await process_one_request(req)


async def mark_request_fulfilled(request_id, selected_url: str) -> None:
    db = get_db()
    await db.track_requests.update_one(
        {"_id": request_id},
        {"$set": {"status": "fulfilled", "selected_url": selected_url, "updated_at": utc_now()}}
    )
