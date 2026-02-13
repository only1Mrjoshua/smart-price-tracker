from dataclasses import dataclass
from typing import Optional
from bs4 import BeautifulSoup
import re


@dataclass
class ProductData:
    title: Optional[str]
    price: Optional[float]
    currency: str
    image: Optional[str]
    availability: str  # "available" | "unavailable"
    reference_price: Optional[float] = None  # Jiji usually doesn't have this


def _normalize_price(text: str) -> Optional[float]:
    if not text:
        return None
    # Handles: "₦ 120,000", "NGN 120,000", "120000"
    m = re.search(r"([\d][\d,]*)", text.replace(" ", ""))
    if not m:
        return None
    return float(m.group(1).replace(",", ""))


def _extract_title(soup: BeautifulSoup) -> Optional[str]:
    # Most Jiji listing pages have a main <h1>
    h1 = soup.select_one("h1")
    if h1:
        t = h1.get_text(strip=True)
        if t:
            return t

    # Fallback: og:title
    ogt = soup.select_one('meta[property="og:title"]')
    if ogt and ogt.get("content"):
        return ogt["content"].strip()

    return None


def _extract_image(soup: BeautifulSoup) -> Optional[str]:
    og = soup.select_one('meta[property="og:image"]')
    if og and og.get("content"):
        return og["content"].strip()

    # fallback: first reasonable img
    for img in soup.select("img"):
        src = img.get("src") or img.get("data-src")
        if src and src.startswith("http"):
            return src
    return None


def _extract_price(soup: BeautifulSoup) -> Optional[float]:
    # Best-effort selectors (Jiji can change)
    selectors = [
        '[data-testid="ad-price"]',
        ".qa-advert-price",
        ".b-advert-title__price",
        ".b-advert-price",
        ".price",
    ]

    for sel in selectors:
        el = soup.select_one(sel)
        if el:
            txt = el.get_text(" ", strip=True)
            p = _normalize_price(txt)
            if p is not None:
                return p

    # Fallback: scan text for ₦xxx
    text = soup.get_text(" ", strip=True)
    m = re.search(r"(₦\s?[\d,]+)", text)
    if m:
        return _normalize_price(m.group(1))

    return None


def fetch_product_data_from_html(html: str) -> ProductData:
    """
    Pure HTML parser (no HTTP). Scheduler fetches HTML then calls this.
    Jiji is best-effort and may fail if layout is JS-heavy / changed.
    """
    soup = BeautifulSoup(html, "html.parser")

    title = _extract_title(soup)
    price = _extract_price(soup)
    image = _extract_image(soup)

    # Currency assumption for Nigeria listing pages; adjust later if needed
    currency = "NGN"

    availability = "available"
    page_text = (title or "").lower()
    if "not found" in page_text or "404" in page_text:
        availability = "unavailable"

    return ProductData(
        title=title,
        price=price,
        currency=currency,
        image=image,
        availability=availability,
        reference_price=None,
    )
