# backend/searchers/jiji_search.py

import re
from typing import List, Dict, Optional
from urllib.parse import quote_plus, urljoin, urlparse

from bs4 import BeautifulSoup


def _normalize_price(text: str) -> Optional[float]:
    if not text:
        return None
    # Handles: "₦ 120,000", "NGN 120,000", "120000"
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

    # skip obvious non-listing routes
    bad = ("login", "signup", "register", "privacy", "terms", "about", "help", "contact", "search")
    if any(x in path for x in bad):
        return False

    # common listing patterns
    if "/ad/" in path:
        return True
    if path.endswith(".html"):
        return True

    # heuristic: long slug-like paths
    if len(path) >= 20 and path.count("/") >= 2:
        return True

    return False


def _extract_title_from_card(a_tag) -> Optional[str]:
    # Try strong title candidates around the link
    # 1) aria-label / title attribute
    t = a_tag.get("aria-label") or a_tag.get("title")
    if t and t.strip():
        return t.strip()

    # 2) element text
    txt = a_tag.get_text(" ", strip=True)
    if txt and len(txt) >= 8:
        return txt

    return None


def _extract_price_near(a_tag) -> Optional[float]:
    # search for ₦... close to the link (parent/grandparent text)
    for node in [a_tag, a_tag.parent, getattr(a_tag.parent, "parent", None)]:
        if not node:
            continue
        txt = node.get_text(" ", strip=True)
        m = re.search(r"(₦\s?[\d,]+)", txt)
        if m:
            return _normalize_price(m.group(1))

    return None


def parse_jiji_search_results(html: str, base_url: str = "https://jiji.ng") -> List[Dict]:
    """
    Returns candidates:
      {title, price, currency, url, image}

    Best-effort: Jiji changes often. This parser tries to reduce noise by:
    - only keeping "listing-like" URLs
    - requiring at least a decent title and/or a real ₦ price nearby
    """
    soup = BeautifulSoup(html, "html.parser")
    candidates: List[Dict] = []

    anchors = soup.select('a[href]')
    seen = set()

    for a in anchors:
        href = a.get("href")
        if not href:
            continue

        url = href if href.startswith("http") else urljoin(base_url, href)

        # de-dupe
        if url in seen:
            continue
        seen.add(url)

        # must look like a listing link
        if not _is_probably_listing_url(url):
            continue

        title = _extract_title_from_card(a)
        price = _extract_price_near(a)

        # image (optional)
        image = None
        img = a.select_one("img")
        if img:
            image = img.get("src") or img.get("data-src")

        # reduce junk: require either price or a meaningful title
        if (price is None) and (not title):
            continue

        # avoid super-short titles (often “Open” / “View”)
        if title and len(title) < 8:
            title = None

        candidates.append({
            "title": title,
            "price": price,
            "currency": "NGN",
            "url": url,
            "image": image,
        })

        if len(candidates) >= 40:  # parse more then filter later by relevance
            break

    return candidates


def build_jiji_search_url(query: str) -> str:
    q = quote_plus(query.strip())
    return f"https://jiji.ng/search?query={q}"
