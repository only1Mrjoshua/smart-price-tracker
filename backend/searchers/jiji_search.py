# backend/searchers/jiji_search.py

import re
from typing import List, Dict, Optional
from urllib.parse import quote_plus, urljoin, urlparse
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)

# Jiji category mapping
JIJI_CATEGORIES = {
    "mobile_phones": 710,
    "tablets": 720,
    "laptops": 500,
}

def _normalize_price(text: str) -> Optional[float]:
    if not text:
        return None
    # Remove currency symbols and spaces, then extract numbers
    cleaned = re.sub(r'[₦NGN\s]', '', text)
    m = re.search(r"([\d][\d,]*)", cleaned)
    if not m:
        return None
    return float(m.group(1).replace(",", ""))

def _extract_price_from_card(card) -> Optional[float]:
    """Extract price from anywhere in the card"""
    # Try specific price elements first
    price_el = card.select_one('.price, .qa-advert-price, [data-testid="ad-price"]')
    if price_el:
        price = _normalize_price(price_el.get_text())
        if price:
            return price
    
    # Check all elements that might contain price
    for el in card.find_all(['span', 'div', 'p', 'h3', 'h4', 'strong']):
        text = el.get_text(" ", strip=True)
        if '₦' in text or 'NGN' in text:
            price = _normalize_price(text)
            if price:
                return price
        
        # Also check for standalone numbers that might be prices
        if re.search(r'^[\d,]+$', text.strip()):  # Only digits and commas
            price = _normalize_price(text)
            if price and price > 100:  # Likely a price if > 100
                return price
    return None

def _extract_title_from_card(card) -> Optional[str]:
    """Extract title from a product card"""
    # Try title elements
    title_el = card.select_one('h3, h2, .qa-advert-title, [data-testid="ad-title"]')
    if title_el:
        title = title_el.get_text(" ", strip=True)
        if title and len(title) >= 5:
            return title
    
    # Try finding a link with substantial text
    for a in card.find_all('a', href=True):
        text = a.get_text(" ", strip=True)
        if text and len(text) >= 10 and not text.isdigit():
            return text
    return None

def _extract_image_from_card(card) -> Optional[str]:
    """Extract image URL from a product card"""
    img = card.select_one('img')
    if img:
        return img.get('src') or img.get('data-src') or img.get('data-original')
    return None

def _find_product_cards(soup: BeautifulSoup) -> List:
    """Find all actual product cards using specific Jiji selectors"""
    cards = []
    
    # Jiji specific selectors (from your earlier successful logs)
    selectors = [
        '.qa-advert-list-item',  # This was in your logs
        '.b-list-advert-base',   # This was in your logs
        'a[href*="/mobile-phones/"]',  # Any link to mobile phones
        'div[class*="advert"]',  # Any div with "advert" in class
        'div[class*="listing"]', # Any div with "listing" in class
    ]
    
    for selector in selectors:
        found = soup.select(selector)
        if found:
            logger.info(f"Selector '{selector}' found {len(found)} elements")
            cards.extend(found)
    
    # If still no cards, try a more aggressive approach
    if not cards:
        # Look for any div that contains both an image and a price-looking element
        for div in soup.find_all('div'):
            if div.find('img') and ('₦' in div.get_text() or 'NGN' in div.get_text()):
                cards.append(div)
    
    # Remove duplicates while preserving order
    unique_cards = []
    seen = set()
    for card in cards:
        # Use the card's approximate position in the DOM as a unique identifier
        card_id = str(card)[:200]  # First 200 chars as simple fingerprint
        if card_id not in seen:
            seen.add(card_id)
            unique_cards.append(card)
    
    logger.info(f"Total unique cards found: {len(unique_cards)}")
    return unique_cards

def parse_jiji_search_results(html: str, base_url: str = "https://jiji.ng") -> List[Dict]:
    """
    Parse Jiji search results - return ALL potential products.
    """
    soup = BeautifulSoup(html, "html.parser")
    candidates = []
    seen_urls = set()
    
    # Find all potential product cards
    cards = _find_product_cards(soup)
    
    for card in cards:
        try:
            # Find the main product link
            link = None
            if card.name == 'a' and card.get('href'):
                link = card
            else:
                link = card.find('a', href=True)
            
            if not link or not link.get('href'):
                continue
            
            href = link.get('href')
            # Make sure it's a full URL
            url = href if href.startswith('http') else urljoin(base_url, href)
            
            # Skip duplicates and non-product URLs
            if url in seen_urls:
                continue
            
            # Skip obvious non-product URLs
            if any(x in url.lower() for x in ['login', 'signup', 'register', 'privacy', 'terms', 'cart']):
                continue
            
            # Extract data
            title = _extract_title_from_card(card)
            price = _extract_price_from_card(card)
            image = _extract_image_from_card(card)
            
            # Need at least a title to consider it a product
            if not title or len(title) < 5:
                continue
            
            # Skip if it looks like a service/ad rather than a product
            if any(x in title.lower() for x in ['value my phone', 'sell your', 'buy', 'offer', 'service']):
                continue
            
            candidates.append({
                "title": title,
                "price": price,
                "currency": "NGN",
                "url": url,
                "image": image,
            })
            
            seen_urls.add(url)
            logger.info(f"✅ Found product: '{title}' - ₦{price if price else 'N/A'}")
            
            if len(candidates) >= 100:
                break
                
        except Exception as e:
            logger.error(f"Error parsing card: {e}")
            continue
    
    logger.info(f"Total valid products found: {len(candidates)}")
    return candidates

def build_jiji_search_url(query: str, location: Optional[str] = None, page: int = 1, category_id: Optional[int] = None) -> str:
    """
    Build a Jiji search URL.
    """
    q = quote_plus((query or "").strip())
    page = max(1, int(page or 1))
    loc = (location or "").strip().lower()
    
    # Map category_id to slug
    category_slugs = {
        710: "mobile-phones",
        720: "tablets",
        500: "laptops",
    }
    
    # Build URL with category if provided
    if category_id and category_id in category_slugs:
        category_path = category_slugs[category_id]
        if loc:
            return f"https://jiji.ng/{quote_plus(loc)}/{category_path}?query={q}&page={page}"
        return f"https://jiji.ng/{category_path}?query={q}&page={page}"
    
    # Default to mobile-phones for phone-related queries
    if 'iphone' in q.lower() or 'phone' in q.lower():
        if loc:
            return f"https://jiji.ng/{quote_plus(loc)}/mobile-phones?query={q}&page={page}"
        return f"https://jiji.ng/mobile-phones?query={q}&page={page}"
    
    # Generic search
    if loc:
        return f"https://jiji.ng/{quote_plus(loc)}/search?query={q}&page={page}"
    return f"https://jiji.ng/search?query={q}&page={page}"