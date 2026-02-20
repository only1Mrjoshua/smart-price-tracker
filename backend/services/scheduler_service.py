import asyncio
import httpx
import random  # Added for random user agent selection

from backend.db import get_db
from backend.utils.time import utc_now, days_ago, ensure_aware
from backend.services.robots_service import allowed_by_robots
from backend.services.logging_service import log_job
from backend.services.email_service import send_email, smtp_configured
from backend.services.pricing_service import insert_price_point, evaluate_alerts_and_notify

from backend.scrapers.jumia import fetch_product_data_from_html as jumia_from_html
from backend.scrapers.konga import fetch_product_data_from_html as konga_from_html
from backend.scrapers.amazon import fetch_product_data_from_html as amazon_from_html
from backend.scrapers.ebay import fetch_product_data_from_html as ebay_from_html
from backend.scrapers.jiji import fetch_product_data_from_html as jiji_from_html

from backend.services.request_service import process_pending_requests


# Expanded list of user agents to avoid blocking
USER_AGENTS = [
    # Chrome Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    
    # Chrome Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    
    # Chrome Linux
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    
    # Firefox Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    
    # Firefox Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0",
    
    # Safari Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
    
    # Edge Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    
    # Mobile user agents
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPad; CPU OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 13; SM-S908B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
]

# Keep a fallback UA (not used directly but available if needed)
FALLBACK_UA = "Mozilla/5.0 (compatible; SmartPriceTracker/0.1; +respect-robots)"

SCRAPER_MAP = {
    "jumia": jumia_from_html,
    "konga": konga_from_html,
    "amazon": amazon_from_html,
    "ebay": ebay_from_html,
    "jiji": jiji_from_html,
}

def _platform_from_doc(doc: dict) -> str:
    return (doc.get("platform") or "").lower().strip()

async def fetch_html(url: str) -> str:
    """Fetch HTML with random user agent to avoid blocking"""
    # Pick a random user agent for each request
    user_agent = random.choice(USER_AGENTS)
    
    # Add additional headers to look more like a real browser
    headers = {
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
    }
    
    async with httpx.AsyncClient(
        timeout=30.0,  # Increased timeout
        follow_redirects=True,
        headers=headers
    ) as client:
        r = await client.get(url)
        r.raise_for_status()
        return r.text

async def check_one_product(tracked: dict):
    db = get_db()
    product_id = tracked["_id"]
    platform = _platform_from_doc(tracked)
    url = tracked.get("url")

    try:
        if not url or platform not in SCRAPER_MAP:
            await db.tracked_products.update_one(
                {"_id": product_id}, 
                {"$set": {"status": "error", "last_checked": utc_now()}}
            )
            await log_job("check_product", platform, str(product_id), "error", "Missing URL or unsupported platform")
            return

        robots_ok = await allowed_by_robots(url)
        if not robots_ok:
            await db.tracked_products.update_one(
                {"_id": product_id}, 
                {"$set": {"status": "blocked", "last_checked": utc_now(), "blocked_reason": "robots.txt disallow"}}
            )
            await log_job("check_product", platform, str(product_id), "blocked", "robots.txt disallow")
            return

        html = await fetch_html(url)
        data = SCRAPER_MAP[platform](html)

        # If we can't parse price, treat as blocked-ish (often anti-bot) but label "error" for clarity
        if data.price is None:
            await db.tracked_products.update_one(
                {"_id": product_id},
                {"$set": {
                    "status": "blocked",
                    "last_checked": utc_now(),
                    "title": data.title,
                    "image": data.image,
                    "currency": data.currency,
                    "blocked_reason": "price not detected (possible anti-bot or layout change)",
                }}
            )
            await log_job("check_product", platform, str(product_id), "blocked", "Price not detected")
            return

        status = "ok"
        if data.availability == "unavailable":
            status = "unavailable"

        update_doc = {
            "title": data.title,
            "image": data.image,
            "current_price": float(data.price),
            "currency": data.currency,
            "reference_price": float(data.reference_price) if data.reference_price else None,
            "status": status,
            "last_checked": utc_now(),
            "blocked_reason": None,
        }

        await db.tracked_products.update_one({"_id": product_id}, {"$set": update_doc})
        await insert_price_point(product_id, float(data.price), data.currency)

        # Evaluate alerts + notify
        await evaluate_alerts_and_notify(
            tracked_product={**tracked, **update_doc},
            latest_price=float(data.price),
            currency=data.currency,
            send_email_fn=send_email if smtp_configured() else (lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("SMTP not configured")))
        )

        await log_job("check_product", platform, str(product_id), "ok", None)

    except httpx.HTTPStatusError as e:
        await db.tracked_products.update_one(
            {"_id": product_id}, 
            {"$set": {"status": "error", "last_checked": utc_now()}}
        )
        await log_job("check_product", platform, str(product_id), "error", f"HTTP error: {e.response.status_code}")
    
    except httpx.TimeoutException as e:
        await db.tracked_products.update_one(
            {"_id": product_id}, 
            {"$set": {"status": "error", "last_checked": utc_now()}}
        )
        await log_job("check_product", platform, str(product_id), "error", f"Timeout: {str(e)}")
    
    except Exception as e:
        await db.tracked_products.update_one(
            {"_id": product_id}, 
            {"$set": {"status": "error", "last_checked": utc_now()}}
        )
        await log_job("check_product", platform, str(product_id), "error", str(e))

async def run_check_cycle():
    db = get_db()

    print(f"\n🔍 Starting check cycle at {utc_now()}")
    
    # Basic backoff: if blocked, check less often by skipping if checked recently
    # ok/error/unavailable: normal frequency
    cursor = db.tracked_products.find({})
    product_count = 0
    
    async for tracked in cursor:
        product_count += 1
        status = tracked.get("status", "ok")
        last_checked = tracked.get("last_checked")
        
        # FIX: Ensure both datetimes are timezone-aware for comparison
        if status == "blocked" and last_checked:
            # Make sure last_checked is timezone-aware
            last_checked_aware = ensure_aware(last_checked)
            cutoff = days_ago(1)  # This is already aware from our fixed time.py
            
            if last_checked_aware > cutoff:
                print(f"⏭️ Skipping blocked product (checked recently): {tracked.get('url')}")
                continue  # wait ~1 day for blocked in MVP
                
        await check_one_product(tracked)
        await process_pending_requests()
        
        # Small delay between requests to avoid rate limiting
        await asyncio.sleep(1)
    
    print(f"✅ Check cycle completed. Processed {product_count} products at {utc_now()}")

async def force_recheck(product_id):
    db = get_db()
    tracked = await db.tracked_products.find_one({"_id": product_id})
    if tracked:
        print(f"⚡ Force rechecking product: {tracked.get('url')}")
        await check_one_product(tracked)