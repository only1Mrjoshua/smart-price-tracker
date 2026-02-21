import asyncio
import httpx
import random
import os
from typing import Optional
import time

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


# API Keys from environment variables
SCRAPINGBEE_API_KEY = os.getenv("SCRAPINGBEE_API_KEY", None)
SCRAPINGDOG_API_KEY = os.getenv("SCRAPINGDOG_API_KEY", None)
PROXY_URL = os.getenv("PROXY_URL", None)

# Expanded list of user agents with more variety
USER_AGENTS = [
    # Chrome Windows (different versions)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
    
    # Chrome Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    
    # Firefox Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:115.0) Gecko/20100101 Firefox/115.0",
    
    # Firefox Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0",
    
    # Safari Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.6 Safari/605.1.15",
    
    # Edge
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
    
    # Opera
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 OPR/106.0.0.0",
    
    # Mobile - iPhone
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
    
    # Mobile - Android
    "Mozilla/5.0 (Linux; Android 13; SM-S908B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 12; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Mobile Safari/537.36",
]

# Different accept languages to rotate
ACCEPT_LANGUAGES = [
    "en-US,en;q=0.9",
    "en-GB,en;q=0.9",
    "en-CA,en;q=0.9",
    "en-NG,en;q=0.9",
    "en,fr;q=0.8",
]

SCRAPER_MAP = {
    "jumia": jumia_from_html,
    "konga": konga_from_html,
    "amazon": amazon_from_html,
    "ebay": ebay_from_html,
    "jiji": jiji_from_html,
}

def _platform_from_doc(doc: dict) -> str:
    return (doc.get("platform") or "").lower().strip()

async def fetch_via_scrapingbee(url: str) -> Optional[str]:
    """Fetch URL using ScrapingBee API"""
    if not SCRAPINGBEE_API_KEY:
        return None
    
    api_url = "https://app.scrapingbee.com/api/v1/"
    params = {
        "api_key": SCRAPINGBEE_API_KEY,
        "url": url,
        "render_js": "false",
        "premium_proxy": "true",  # Use residential proxies
        "country_code": "ng",      # Use Nigerian IPs for Jiji
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.get(api_url, params=params)
            if r.status_code == 200:
                print(f"✅ ScrapingBee success: {url}")
                return r.text
            else:
                print(f"⚠️ ScrapingBee error: {r.status_code}")
                return None
    except Exception as e:
        print(f"⚠️ ScrapingBee exception: {e}")
        return None

async def fetch_via_scrapingdog(url: str) -> Optional[str]:
    """Fetch URL using ScrapingDog API"""
    if not SCRAPINGDOG_API_KEY:
        return None
    
    api_url = "https://api.scrapingdog.com/scrape"
    params = {
        "api_key": SCRAPINGDOG_API_KEY,
        "url": url,
        "dynamic": "false",
        "country": "ng",
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.get(api_url, params=params)
            if r.status_code == 200:
                print(f"✅ ScrapingDog success: {url}")
                return r.text
            else:
                print(f"⚠️ ScrapingDog error: {r.status_code}")
                return None
    except Exception as e:
        print(f"⚠️ ScrapingDog exception: {e}")
        return None

async def fetch_via_proxy(url: str) -> Optional[str]:
    """Fetch URL using a proxy server"""
    if not PROXY_URL:
        return None
    
    user_agent = random.choice(USER_AGENTS)
    headers = {
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": random.choice(ACCEPT_LANGUAGES),
    }
    
    try:
        async with httpx.AsyncClient(
            proxies=PROXY_URL,
            headers=headers,
            timeout=30.0,
            follow_redirects=True
        ) as client:
            r = await client.get(url)
            r.raise_for_status()
            print(f"✅ Proxy success: {url}")
            return r.text
    except Exception as e:
        print(f"⚠️ Proxy failed: {e}")
        return None

async def fetch_html_with_retry(url: str, max_retries: int = 3) -> str:
    """Fetch HTML with retry logic and multiple fallback methods"""
    
    # Try different methods in sequence
    fetch_methods = []
    
    # Add API methods first if keys are available
    if SCRAPINGBEE_API_KEY:
        fetch_methods.append(("ScrapingBee", fetch_via_scrapingbee))
    if SCRAPINGDOG_API_KEY:
        fetch_methods.append(("ScrapingDog", fetch_via_scrapingdog))
    if PROXY_URL:
        fetch_methods.append(("Proxy", fetch_via_proxy))
    
    # Add direct request as last resort
    fetch_methods.append(("Direct", fetch_via_direct))
    
    for method_name, method_func in fetch_methods:
        print(f"🔄 Trying {method_name} for {url}")
        
        for attempt in range(max_retries):
            try:
                result = await method_func(url)
                if result:
                    return result
                
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) * 3
                    print(f"⏳ {method_name} failed, retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    
            except Exception as e:
                print(f"⚠️ {method_name} error: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
        
        print(f"❌ {method_name} failed for {url}, trying next method...")
    
    raise Exception(f"All fetch methods failed for {url}")

async def fetch_via_direct(url: str) -> Optional[str]:
    """Direct HTTP request with browser emulation"""
    
    # Random delay before request
    delay = random.uniform(3, 8)
    await asyncio.sleep(delay)
    
    # Pick random user agent
    user_agent = random.choice(USER_AGENTS)
    accept_lang = random.choice(ACCEPT_LANGUAGES)
    
    # Randomize viewport size
    viewport_width = random.choice([1920, 1366, 1536, 1440, 1280])
    viewport_height = random.choice([1080, 768, 864, 900, 720])
    
    headers = {
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": accept_lang,
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
        "Viewport-Width": str(viewport_width),
        "Viewport-Height": str(viewport_height),
    }
    
    # Add random X-Forwarded-For sometimes
    if random.random() > 0.5:
        headers["X-Forwarded-For"] = f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}"
    
    async with httpx.AsyncClient(
        timeout=30.0,
        follow_redirects=True,
        headers=headers,
        http2=random.choice([True, False]),
    ) as client:
        r = await client.get(url)
        if r.status_code == 403:
            print(f"🚫 Direct request got 403 for {url}")
            return None
        r.raise_for_status()
        return r.text

async def fetch_html(url: str) -> str:
    """Wrapper for fetch_html_with_retry"""
    return await fetch_html_with_retry(url)

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

        # Skip robots.txt check for blocked sites
        if random.random() > 0.9:  # Only 10% of the time
            try:
                robots_ok = await allowed_by_robots(url)
                if not robots_ok:
                    await db.tracked_products.update_one(
                        {"_id": product_id}, 
                        {"$set": {"status": "blocked", "last_checked": utc_now(), "blocked_reason": "robots.txt disallow"}}
                    )
                    await log_job("check_product", platform, str(product_id), "blocked", "robots.txt disallow")
                    return
            except:
                pass  # Ignore robots.txt errors

        html = await fetch_html(url)
        data = SCRAPER_MAP[platform](html)

        # If we can't parse price, treat as blocked
        if data.price is None:
            await db.tracked_products.update_one(
                {"_id": product_id},
                {"$set": {
                    "status": "blocked",
                    "last_checked": utc_now(),
                    "title": data.title,
                    "image": data.image,
                    "currency": data.currency,
                    "blocked_reason": "price not detected (possible anti-bot)",
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
        print(f"✅ Successfully checked {url}")

    except httpx.HTTPStatusError as e:
        status_code = e.response.status_code
        error_msg = f"HTTP error: {status_code}"
        
        # Special handling for 403
        if status_code == 403:
            blocked_reason = "Site is blocking our requests"
            # Check if we have any API keys for better message
            if SCRAPINGBEE_API_KEY or SCRAPINGDOG_API_KEY or PROXY_URL:
                blocked_reason = "Site blocking - proxy/API may be needed"
            else:
                blocked_reason = "Site blocking - configure ScrapingBee or proxy"
            
            await db.tracked_products.update_one(
                {"_id": product_id}, 
                {"$set": {
                    "status": "blocked", 
                    "last_checked": utc_now(),
                    "blocked_reason": blocked_reason
                }}
            )
        else:
            await db.tracked_products.update_one(
                {"_id": product_id}, 
                {"$set": {"status": "error", "last_checked": utc_now()}}
            )
        
        await log_job("check_product", platform, str(product_id), "error", error_msg)
        print(f"❌ Failed to check {url}: {error_msg}")
    
    except Exception as e:
        await db.tracked_products.update_one(
            {"_id": product_id}, 
            {"$set": {"status": "error", "last_checked": utc_now()}}
        )
        await log_job("check_product", platform, str(product_id), "error", str(e))
        print(f"❌ Failed to check {url}: {str(e)}")

async def run_check_cycle():
    db = get_db()

    print(f"\n🔍 Starting check cycle at {utc_now()}")
    print(f"📊 Configured: ScrapingBee={bool(SCRAPINGBEE_API_KEY)}, ScrapingDog={bool(SCRAPINGDOG_API_KEY)}, Proxy={bool(PROXY_URL)}")
    
    cursor = db.tracked_products.find({})
    product_count = 0
    blocked_count = 0
    
    async for tracked in cursor:
        product_count += 1
        status = tracked.get("status", "ok")
        last_checked = tracked.get("last_checked")
        
        # Debug: Check what's coming from database
        print(f"📦 Product {product_count}: status={status}, last_checked={last_checked}")
        if last_checked:
            print(f"   last_checked type: {type(last_checked)}, tzinfo: {last_checked.tzinfo}")
        
        # Skip recently checked blocked products
        if status == "blocked" and last_checked:
            # Debug before conversion
            print(f"   Before ensure_aware: tzinfo={last_checked.tzinfo}")
            
            last_checked_aware = ensure_aware(last_checked)
            cutoff = days_ago(1)
            
            # Debug after conversion
            print(f"   After ensure_aware: tzinfo={last_checked_aware.tzinfo}")
            print(f"   Cutoff: tzinfo={cutoff.tzinfo}")
            
            # This comparison should now work
            if last_checked_aware > cutoff:
                print(f"⏭️ Skipping blocked product: {tracked.get('url')}")
                blocked_count += 1
                continue
        
        # Random longer delay between products
        if product_count > 1:
            delay = random.uniform(8, 15)
            print(f"⏳ Waiting {delay:.1f}s before next product...")
            await asyncio.sleep(delay)
        
        await check_one_product(tracked)
        await process_pending_requests()
    
    print(f"\n📊 Check cycle completed at {utc_now()}")
    print(f"   Total products: {product_count}")
    print(f"   Processed: {product_count - blocked_count}")
    print(f"   Skipped (blocked): {blocked_count}")

async def force_recheck(product_id):
    db = get_db()
    tracked = await db.tracked_products.find_one({"_id": product_id})
    if tracked:
        print(f"⚡ Force rechecking product: {tracked.get('url')}")
        await check_one_product(tracked)