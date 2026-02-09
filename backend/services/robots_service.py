from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser
import httpx

# Simple, cached robots.txt fetcher.
# NOTE: robots.txt rules differ per user-agent; we use a generic UA for MVP.
_cache: dict[str, tuple[RobotFileParser, float]] = {}
TTL_SECONDS = 60 * 60  # 1 hour

UA = "SmartPriceTrackerBot/0.1 (+respect-robots)"

async def allowed_by_robots(url: str) -> bool:
    parsed = urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    robots_url = f"{base}/robots.txt"

    import time
    now = time.time()

    if base in _cache and (now - _cache[base][1]) < TTL_SECONDS:
        rp = _cache[base][0]
        return rp.can_fetch(UA, url)

    rp = RobotFileParser()
    try:
        async with httpx.AsyncClient(timeout=10.0, headers={"User-Agent": UA}) as client:
            r = await client.get(robots_url)
            if r.status_code >= 400:
                # If robots.txt not reachable, we do NOT assume permission; we proceed cautiously:
                # For MVP, treat as allowed to fetch public product pages, but do not crawl aggressively.
                rp.parse([])
            else:
                rp.parse(r.text.splitlines())
    except Exception:
        rp.parse([])

    _cache[base] = (rp, now)
    return rp.can_fetch(UA, url)
