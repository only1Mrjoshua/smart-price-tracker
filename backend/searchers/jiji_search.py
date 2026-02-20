# backend/searchers/jiji_search.py

import re
import json
from typing import List, Dict, Optional
from urllib.parse import quote_plus, urljoin, urlparse

from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)

def _normalize_price(text: str) -> Optional[float]:
    if not text:
        return None
    # Handle "₦ 120,000", "NGN 120,000", "120,000", "₦120000"
    # First remove currency symbols and spaces
    cleaned = re.sub(r'[₦NGN\s]', '', text)
    m = re.search(r"([\d][\d,]*)", cleaned)
    if not m:
        return None
    return float(m.group(1).replace(",", ""))

def _extract_price_from_element(el) -> Optional[float]:
    """Extract price from any element, looking for common Jiji price patterns"""
    if not el:
        return None
    
    # Common Jiji price selectors
    price_selectors = [
        '[data-testid="ad-price"]',
        '.qa-advert-price',
        '.b-advert-price',
        '.price',
        'span:contains("₦")',
        'div:contains("₦")'
    ]
    
    # Try specific selectors first
    for selector in price_selectors:
        price_el = el.select_one(selector)
        if price_el:
            price_text = price_el.get_text(" ", strip=True)
            price = _normalize_price(price_text)
            if price:
                return price
    
    # If no specific selector found, search for any element containing ₦
    for child in el.find_all(['span', 'div', 'p', 'h3', 'h4']):
        text = child.get_text(" ", strip=True)
        if '₦' in text or 'NGN' in text:
            price = _normalize_price(text)
            if price:
                return price
    
    return None

def _extract_title_from_card(card) -> Optional[str]:
    """Extract title from a product card"""
    # Try common title selectors
    title_selectors = [
        'h3',
        'h2',
        '.qa-advert-title',
        '[data-testid="ad-title"]',
        'a[aria-label]',
        'a[title]'
    ]
    
    for selector in title_selectors:
        title_el = card.select_one(selector)
        if title_el:
            title = title_el.get_text(" ", strip=True)
            if title and len(title) >= 3:
                return title
    
    # If no specific selector, try to find a likely title (not too long, not just numbers)
    for a in card.find_all('a'):
        text = a.get_text(" ", strip=True)
        if text and len(text) >= 5 and len(text) <= 100 and not text.isdigit():
            return text
    
    return None

def _extract_image_from_card(card) -> Optional[str]:
    """Extract image URL from a product card"""
    # Try to find img tag
    img = card.select_one('img')
    if img:
        return img.get('src') or img.get('data-src') or img.get('data-original')
    
    # Sometimes Jiji uses background images
    style = card.get('style', '')
    if 'background-image' in style:
        match = re.search(r'url\([\'"]?(.*?)[\'"]?\)', style)
        if match:
            return match.group(1)
    
    return None

def _find_product_cards(soup: BeautifulSoup) -> List:
    """Find all product card containers in Jiji search results"""
    cards = []
    
    # Common Jiji card selectors
    card_selectors = [
        '.b-advert-card',
        '.qa-advert-list-item',
        '[data-testid="ad-card"]',
        '.listing-card',
        'article',
        '.col-md-3 .masonry-item',
        'div[class*="advert"]',
        'div[class*="listing"]'
    ]
    
    for selector in card_selectors:
        found = soup.select(selector)
        if found:
            logger.info(f"Found {len(found)} cards with selector: {selector}")
            cards.extend(found)
    
    # If no cards found with selectors, try to find likely product containers
    if not cards:
        # Look for divs containing both an image and a price-looking element
        for div in soup.find_all('div', recursive=True):
            if div.find('img') and ('₦' in div.get_text() or 'NGN' in div.get_text()):
                cards.append(div)
                if len(cards) > 50:  # Limit to avoid too many false positives
                    break
    
    return cards

def _is_valid_product_url(url: str) -> bool:
    """Check if URL is likely a valid product page"""
    try:
        p = urlparse(url)
        path = (p.path or "").lower()
    except Exception:
        return False
    
    # Must have a path
    if not path or path == "/":
        return False
    
    # Filter out non-product pages
    bad_patterns = [
        'login', 'signup', 'register', 'privacy', 'terms', 
        'about', 'help', 'contact', 'search', 'category',
        'categories', 'wishlist', 'cart', 'checkout'
    ]
    
    if any(pattern in path for pattern in bad_patterns):
        return False
    
    # Jiji product URLs typically contain identifiers
    # They often look like: /port-harcourt/mobile-phones/samsung-galaxy-123.html
    # or contain /ad/ or have .html extension
    
    if '/ad/' in path:
        return True
    
    if path.endswith('.html'):
        # Make sure it's not just a category page ending in .html
        path_parts = path.split('/')
        if len(path_parts) >= 3:  # Should have at least category/subcategory/slug
            return True
    
    # Check for typical Jiji pattern: /location/category/product-name-id
    path_parts = path.split('/')
    if len(path_parts) >= 4 and len(path_parts[-1]) > 10:
        return True
    
    return False

def parse_jiji_search_results(html: str, base_url: str = "https://jiji.ng") -> List[Dict]:
    """
    Returns candidates:
      {title, price, currency, url, image}
    Improved parser with better card detection and price extraction.
    """
    soup = BeautifulSoup(html, "html.parser")
    candidates: List[Dict] = []
    seen_urls = set()
    
    # Try to find product cards first
    cards = _find_product_cards(soup)
    logger.info(f"Found {len(cards)} potential product cards")
    
    for card in cards:
        try:
            # Find the main link
            link = card.find('a', href=True)
            if not link:
                continue
            
            href = link.get('href')
            if not href:
                continue
            
            url = href if href.startswith('http') else urljoin(base_url, href)
            
            # Skip if already seen or invalid
            if url in seen_urls:
                continue
            
            if not _is_valid_product_url(url):
                continue
            
            # Extract data
            title = _extract_title_from_card(card)
            price = _extract_price_from_element(card)
            image = _extract_image_from_card(card)
            
            # Skip if no title and no price (likely not a real product)
            if not title and not price:
                continue
            
            # If we have either title or price, add as candidate
            candidates.append({
                "title": title or "Unknown Product",
                "price": price,
                "currency": "NGN",
                "url": url,
                "image": image,
            })
            
            seen_urls.add(url)
            
            # Limit candidates
            if len(candidates) >= 50:
                break
                
        except Exception as e:
            logger.error(f"Error parsing card: {e}")
            continue
    
    # If no cards found with the above method, try the original anchor-based method as fallback
    if not candidates:
        logger.info("No cards found, falling back to anchor-based parsing")
        candidates = _fallback_anchor_parse(soup, base_url, seen_urls)
    
    # Remove duplicates (by URL)
    unique_candidates = []
    seen = set()
    for c in candidates:
        if c['url'] not in seen:
            seen.add(c['url'])
            unique_candidates.append(c)
    
    logger.info(f"Final candidates: {len(unique_candidates)}")
    return unique_candidates

def _fallback_anchor_parse(soup: BeautifulSoup, base_url: str, seen_urls: set) -> List[Dict]:
    """Fallback method using the original anchor-based parsing"""
    candidates = []
    anchors = soup.select("a[href]")
    
    for a in anchors:
        href = a.get("href")
        if not href:
            continue
        
        url = href if href.startswith("http") else urljoin(base_url, href)
        
        if url in seen_urls:
            continue
        seen_urls.add(url)
        
        # More lenient URL checking
        if not _is_valid_product_url(url):
            continue
        
        title = _extract_title_from_card(a)
        price = _extract_price_from_element(a)
        
        image = None
        img = a.select_one("img")
        if img:
            image = img.get("src") or img.get("data-src")
        
        if price is None and not title:
            continue
        
        candidates.append({
            "title": title or "Unknown Product",
            "price": price,
            "currency": "NGN",
            "url": url,
            "image": image,
        })
        
        if len(candidates) >= 50:
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
    page = max(1, int(page or 1))
    
    loc = (location or "").strip().lower()
    
    # Jiji uses different URL patterns
    if loc:
        # Try the most common pattern first
        return f"https://jiji.ng/{quote_plus(loc)}/search?query={q}&page={page}"
    
    return f"https://jiji.ng/search?query={q}&page={page}"