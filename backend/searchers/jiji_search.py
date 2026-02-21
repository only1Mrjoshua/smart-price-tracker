# backend/searchers/jiji_search.py

import re
import os
import random
import asyncio
from typing import List, Dict, Optional
from urllib.parse import quote_plus, urljoin, urlparse
from bs4 import BeautifulSoup
import logging
import httpx

logger = logging.getLogger(__name__)

# Detect if running on Render
IS_RENDER = os.environ.get('RENDER', False) or os.environ.get('RENDER_EXTERNAL_URL', False)

# Jiji category mapping
JIJI_CATEGORIES = {
    "mobile_phones": 710,
    "tablets": 720,
    "laptops": 500,
}

# Rotating user agents for different platforms
USER_AGENTS = [
    # Windows Chrome
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    
    # Mac Chrome/Safari
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    
    # Firefox
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
    
    # Mobile
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 13; SM-S908B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
]

# Rotating accept languages
ACCEPT_LANGUAGES = [
    "en-US,en;q=0.9",
    "en-GB,en;q=0.9",
    "en-NG,en;q=0.9",
    "en-CA,en;q=0.8",
    "en-AU,en;q=0.8",
]

async def fetch_jiji_search(url: str, max_retries: int = 3) -> Optional[str]:
    """
    Fetch Jiji search results with Render-specific handling and anti-blocking measures.
    """
    # Log environment
    if IS_RENDER:
        logger.info("🔄 Running on Render - using enhanced anti-blocking measures")
    
    for attempt in range(max_retries):
        try:
            # Progressive delay based on environment and attempt
            if IS_RENDER:
                # Longer delays on Render
                base_delay = random.uniform(10, 20)
                delay = base_delay * (attempt + 1)
                logger.info(f"⏳ Render attempt {attempt + 1}/{max_retries} - Waiting {delay:.1f}s...")
            else:
                base_delay = random.uniform(3, 7)
                delay = base_delay * (attempt + 0.5)
                logger.info(f"⏳ Local attempt {attempt + 1}/{max_retries} - Waiting {delay:.1f}s...")
            
            await asyncio.sleep(delay)
            
            # Select random headers
            headers = {
                "User-Agent": random.choice(USER_AGENTS),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": random.choice(ACCEPT_LANGUAGES),
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
            
            # Add random viewport size
            headers["Viewport-Width"] = str(random.choice([1920, 1366, 1536, 1440, 1280]))
            headers["Viewport-Height"] = str(random.choice([1080, 768, 864, 900, 720]))
            
            # Add Chrome-specific headers sometimes
            if random.random() > 0.5:
                headers["Sec-Ch-Ua"] = '"Chromium";v="120", "Google Chrome";v="120", "Not?A_Brand";v="99"'
                headers["Sec-Ch-Ua-Mobile"] = "?0"
                headers["Sec-Ch-Ua-Platform"] = random.choice(['"Windows"', '"macOS"', '"Linux"'])
            
            # Add random X-Forwarded-For on Render (helps with some proxies)
            if IS_RENDER and random.random() > 0.7:
                headers["X-Forwarded-For"] = f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}"
            
            # Make request with timeout
            timeout = 30.0 if not IS_RENDER else 45.0  # Longer timeout on Render
            
            async with httpx.AsyncClient(
                headers=headers,
                timeout=timeout,
                follow_redirects=True,
                http2=random.choice([True, False]),  # Randomly use HTTP/2
            ) as client:
                response = await client.get(url)
                
                # Check for blocking
                if response.status_code == 403:
                    logger.warning(f"🚫 Jiji blocked request (attempt {attempt + 1})")
                    if attempt < max_retries - 1:
                        continue
                    return None
                
                response.raise_for_status()
                
                # Verify we got actual content (not a captcha or block page)
                content = response.text
                if len(content) < 1000 or "captcha" in content.lower() or "access denied" in content.lower():
                    logger.warning(f"⚠️ Suspicious response content (attempt {attempt + 1})")
                    if attempt < max_retries - 1:
                        continue
                    return None
                
                logger.info(f"✅ Successfully fetched {url}")
                return content
                
        except httpx.TimeoutException:
            logger.warning(f"⏰ Timeout on attempt {attempt + 1}")
            if attempt < max_retries - 1:
                continue
        except httpx.HTTPStatusError as e:
            logger.warning(f"⚠️ HTTP error {e.response.status_code} on attempt {attempt + 1}")
            if e.response.status_code == 429 and attempt < max_retries - 1:  # Rate limit
                wait_time = 60  # Wait a minute if rate limited
                logger.info(f"⏳ Rate limited, waiting {wait_time}s...")
                await asyncio.sleep(wait_time)
                continue
            elif attempt < max_retries - 1:
                continue
        except Exception as e:
            logger.error(f"❌ Error on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                continue
    
    logger.error(f"❌ All {max_retries} attempts failed for {url}")
    return None

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
    
    # Jiji specific selectors
    selectors = [
        '.qa-advert-list-item',
        '.b-list-advert-base',
        'a[href*="/mobile-phones/"]',
        'div[class*="advert"]',
        'div[class*="listing"]',
    ]
    
    for selector in selectors:
        found = soup.select(selector)
        if found:
            logger.info(f"Selector '{selector}' found {len(found)} elements")
            cards.extend(found)
    
    # If still no cards, try a more aggressive approach
    if not cards:
        for div in soup.find_all('div'):
            if div.find('img') and ('₦' in div.get_text() or 'NGN' in div.get_text()):
                cards.append(div)
    
    # Remove duplicates
    unique_cards = []
    seen = set()
    for card in cards:
        card_id = str(card)[:200]
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
    
    cards = _find_product_cards(soup)
    
    for card in cards:
        try:
            link = None
            if card.name == 'a' and card.get('href'):
                link = card
            else:
                link = card.find('a', href=True)
            
            if not link or not link.get('href'):
                continue
            
            href = link.get('href')
            url = href if href.startswith('http') else urljoin(base_url, href)
            
            if url in seen_urls:
                continue
            
            if any(x in url.lower() for x in ['login', 'signup', 'register', 'privacy', 'terms', 'cart']):
                continue
            
            title = _extract_title_from_card(card)
            price = _extract_price_from_card(card)
            image = _extract_image_from_card(card)
            
            if not title or len(title) < 5:
                continue
            
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
    
    category_slugs = {
        710: "mobile-phones",
        720: "tablets",
        500: "laptops",
    }
    
    if category_id and category_id in category_slugs:
        category_path = category_slugs[category_id]
        if loc:
            return f"https://jiji.ng/{quote_plus(loc)}/{category_path}?query={q}&page={page}"
        return f"https://jiji.ng/{category_path}?query={q}&page={page}"
    
    if 'iphone' in q.lower() or 'phone' in q.lower():
        if loc:
            return f"https://jiji.ng/{quote_plus(loc)}/mobile-phones?query={q}&page={page}"
        return f"https://jiji.ng/mobile-phones?query={q}&page={page}"
    
    if loc:
        return f"https://jiji.ng/{quote_plus(loc)}/search?query={q}&page={page}"
    return f"https://jiji.ng/search?query={q}&page={page}"