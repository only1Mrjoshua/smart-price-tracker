# backend/services/request_service.py

from typing import Dict, List, Optional, Tuple
import re
import httpx
from bson import ObjectId
from backend.db import get_db
from backend.utils.time import utc_now, days_ago
from backend.services.robots_service import allowed_by_robots
from backend.services.logging_service import log_job

# KEEP THIS if your file is in: backend/searchers/jiji_search.py
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
# Relevance filtering
# -------------------------

_STOPWORDS = {
    "a", "an", "and", "or", "the", "for", "to", "of", "in", "on", "with",
    "buy", "sale", "used", "new", "brand", "original", "london", "lagos",
    "abuja", "nigeria", "naija"
}

def _normalize_text(s: str) -> str:
    s = (s or "").lower().strip()
    s = s.replace("₦", " ")
    s = re.sub(r"[^\w\s]", " ", s)   # remove punctuation
    s = re.sub(r"\s+", " ", s)
    return s

def _tokenize_query(query: str) -> List[str]:
    q = _normalize_text(query)
    tokens = [t for t in q.split(" ") if t and t not in _STOPWORDS]
    return tokens[:12]  # cap to avoid noise

def _tokenize_title(title: str) -> List[str]:
    t = _normalize_text(title)
    return [x for x in t.split(" ") if x]

def _score_candidate(query_tokens: List[str], title: str) -> Tuple[int, int]:
    """
    Returns (score, matches).
    - score increases with token matches + exact phrase presence
    - matches is count of unique query tokens found in title
    """
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

    # phrase bonus (helps "iphone 15" stay above random accessories)
    q_phrase = " ".join(query_tokens).strip()
    if q_phrase and q_phrase in title_norm:
        score += 20

    # extra: numbers matter a lot (15, 128, etc.)
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
    """
    1) Filter by max_price
    2) Filter by relevance to query (prevents "power bank" for "iphone 15")
    3) Sort best matches first
    """
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
            if float(price) > float(max_price):
                continue

        # Relevance score
        score, matches = _score_candidate(q_tokens, title)

        # Strong minimum rule:
        # - If query has 2+ tokens: require at least 2 matches
        # - If query has 1 token: require 1 match
        required_matches = 2 if len(q_tokens) >= 2 else 1
        if matches < required_matches:
            continue

        c["_score"] = score
        c["_matches"] = matches
        filtered.append(c)

    # Sort by score desc, then price asc (nice UX)
    filtered.sort(key=lambda x: (x.get("_score", 0), -(x.get("_matches", 0))), reverse=True)

    # remove private fields
    for c in filtered:
        c.pop("_score", None)
        c.pop("_matches", None)

    return filtered


# -------------------------
# DB logic
# -------------------------

async def create_request(user_id, platform: str, query: str, max_price: Optional[float]) -> Dict:
    db = get_db()
    now = utc_now()
    doc = {
        "user_id": user_id,
        "platform": platform,
        "query": query,
        "max_price": float(max_price) if max_price is not None else None,
        "status": "pending",  # pending|searching|options_found|blocked|error|fulfilled
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


async def process_one_request(req) -> None:
    db = get_db()

    # ✅ allow req to be either ObjectId OR full request document
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

    await db.track_requests.update_one({"_id": rid}, {"$set": {"status": "searching", "updated_at": utc_now()}})

    build_url = SEARCHERS[platform]["build_url"]
    parse_fn = SEARCHERS[platform]["parse"]
    base_url = SEARCHERS[platform]["base_url"]

    query = (req.get("query") or "").strip()
    search_url = build_url(query)
    if not search_url:
        await db.track_requests.update_one(
            {"_id": rid},
            {"$set": {"status": "error", "error_message": "Empty query", "updated_at": utc_now()}}
        )
        return

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

    try:
        html = await _fetch_html(search_url)
        candidates = parse_fn(html, base_url=base_url)

        ranked = _apply_filters_and_rank(
            candidates=candidates,
            query=query,
            max_price=req.get("max_price"),
        )

        # If nothing survives relevance filter, show "options_found" but empty results
        await db.track_requests.update_one(
            {"_id": rid},
            {"$set": {
                "status": "options_found",
                "results": ranked[:20],
                "error_message": None,
                "blocked_reason": None,
                "updated_at": utc_now(),
                "next_retry_at": None,
            }}
        )
        await log_job("search_request", platform, str(rid), "ok", f"kept={len(ranked)}")

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
