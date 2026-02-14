# backend/searchers/jiji_search.py

import re
from typing import List, Dict, Optional
from urllib.parse import quote_plus, urljoin, urlparse

from bs4 import BeautifulSoup


def _normalize_price(text: str) -> Optional[float]:
    if not text:
        return None
    m = re.search(r"([\d][\d,]*)", text.replace(" ", ""))
    if not m:
        return None
    return float(m.group(1).replace(",", ""))


def _is_probably_listing_url(url: str) -> bool:
    """
    Jiji URLs vary, but listing pages tend to have longer paths and often contain /ad/ or end with .html.
    This prevents picking menu/footer links.
    """
    try:
        p = urlparse(url)
        path = (p.path or "").lower()
    except Exception:
        return False

    if not path or path == "/":
        return False

    bad = ("login", "signup", "register", "privacy", "terms", "about", "help", "contact", "search")
    if any(x in path for x in bad):
        return False

    if "/ad/" in path:
        return True
    if path.endswith(".html"):
        return True

    if len(path) >= 20 and path.count("/") >= 2:
        return True

    return False


def _extract_title_from_card(a_tag) -> Optional[str]:
    t = a_tag.get("aria-label") or a_tag.get("title")
    if t and t.strip():
        return t.strip()

    txt = a_tag.get_text(" ", strip=True)
    if txt and len(txt) >= 8:
        return txt

    return None


def _extract_price_near(a_tag) -> Optional[float]:
    for node in [a_tag, a_tag.parent, getattr(a_tag.parent, "parent", None)]:
        if not node:
            continue
        txt = node.get_text(" ", strip=True)

        # common ₦ pattern
        m = re.search(r"(₦\s?[\d,]+)", txt)
        if m:
            return _normalize_price(m.group(1))

        # fallback: sometimes NGN appears
        m2 = re.search(r"(NGN\s?[\d,]+)", txt, re.IGNORECASE)
        if m2:
            return _normalize_price(m2.group(1))

    return None


def parse_jiji_search_results(html: str, base_url: str = "https://jiji.ng") -> List[Dict]:
    """
    Returns candidates:
      {title, price, currency, url, image}
    Best-effort: Jiji changes often.

    This parser reduces noise by:
    - only keeping "listing-like" URLs
    - requiring either a meaningful title or a detectable price
    """
    soup = BeautifulSoup(html, "html.parser")
    candidates: List[Dict] = []

    anchors = soup.select("a[href]")
    seen = set()

    for a in anchors:
        href = a.get("href")
        if not href:
            continue

        url = href if href.startswith("http") else urljoin(base_url, href)

        if url in seen:
            continue
        seen.add(url)

        if not _is_probably_listing_url(url):
            continue

        title = _extract_title_from_card(a)
        price = _extract_price_near(a)

        image = None
        img = a.select_one("img")
        if img:
            image = img.get("src") or img.get("data-src")

        if (price is None) and (not title):
            continue

        if title and len(title) < 8:
            title = None

        candidates.append({
            "title": title,
            "price": price,
            "currency": "NGN",
            "url": url,
            "image": image,
        })

        # ✅ increase candidate cap per page to allow better relevance filtering later
        # If you plan to fetch up to ~8 pages, 100 per page is fine.
        if len(candidates) >= 120:
            break

    return candidates


def build_jiji_search_url(query: str, location: Optional[str] = None, page: int = 1) -> str:
    """
    Build a Jiji search URL.

    - query: what user typed
    - location: optional (e.g. "lagos", "abuja"). Jiji commonly supports /{location}/search
    - page: page number starting at 1
    """
    q = quote_plus((query or "").strip())
    page = int(page or 1)
    if page < 1:
        page = 1

    loc = (location or "").strip().lower()
    if loc:
        # Jiji commonly supports: https://jiji.ng/lagos/search?query=iphone&page=2
        return f"https://jiji.ng/{quote_plus(loc)}/search?query={q}&page={page}"

    return f"https://jiji.ng/search?query={q}&page={page}"
