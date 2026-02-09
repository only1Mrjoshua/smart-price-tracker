from backend.scrapers.base import ProductData, parse_price_number, soup_from_html

def fetch_product_data_from_html(html: str) -> ProductData:
    soup = soup_from_html(html)

    title = ""
    h1 = soup.select_one("h1#itemTitle") or soup.select_one("h1")
    if h1:
        title = h1.get_text(" ", strip=True).replace("Details about  \xa0", "").strip()

    price_el = soup.select_one("#prcIsum") or soup.select_one(".x-price-primary span") or soup.select_one("[itemprop=price]")
    price = None
    currency = "USD"
    if price_el:
        price = parse_price_number(price_el.get_text(" ", strip=True))
        cur = price_el.get("content") or ""
        # ebay uses meta tags for currency often
    meta_cur = soup.select_one('meta[itemprop="priceCurrency"]')
    if meta_cur and meta_cur.get("content"):
        currency = meta_cur["content"].strip()

    img = None
    img_el = soup.select_one("#icImg") or soup.select_one("img")
    if img_el and img_el.get("src"):
        img = img_el["src"]

    availability = "unknown"
    if soup.find(string=lambda s: s and "out of stock" in s.lower()):
        availability = "unavailable"
    elif price is not None:
        availability = "available"

    ref_price = None
    old = soup.select_one(".notranslate.ms-2") or soup.select_one("del")
    if old:
        ref_price = parse_price_number(old.get_text(" ", strip=True))

    return ProductData(
        title=title or "eBay Product",
        price=price,
        currency=currency,
        image=img,
        availability=availability,
        reference_price=ref_price
    )
