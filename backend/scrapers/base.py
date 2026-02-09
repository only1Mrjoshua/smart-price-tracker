from dataclasses import dataclass
from typing import Optional
from bs4 import BeautifulSoup
import re

@dataclass
class ProductData:
    title: str
    price: Optional[float]
    currency: str
    image: Optional[str]
    availability: str  # "available" | "unavailable" | "unknown"
    reference_price: Optional[float] = None

def parse_price_number(text: str) -> Optional[float]:
    if not text:
        return None
    # remove currency symbols and keep digits/., then normalize
    cleaned = re.sub(r"[^\d.,]", "", text).strip()
    if not cleaned:
        return None
    # If both comma and dot exist, guess thousand separator
    if "," in cleaned and "." in cleaned:
        # assume commas are thousand separators
        cleaned = cleaned.replace(",", "")
    else:
        # if only comma exists, treat comma as decimal separator if it looks like decimals
        if cleaned.count(",") == 1 and cleaned.count(".") == 0:
            left, right = cleaned.split(",")
            if len(right) in (1, 2):
                cleaned = left + "." + right
            else:
                cleaned = cleaned.replace(",", "")
        else:
            cleaned = cleaned.replace(",", "")
    try:
        return float(cleaned)
    except ValueError:
        return None

def soup_from_html(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")
