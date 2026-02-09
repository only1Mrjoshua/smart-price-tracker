from backend.scrapers.base import ProductData, parse_price_number, soup_from_html

def fetch_product_data_from_html(html: str) -> ProductData:
    soup = soup_from_html(html)

    title = ""
    h1 = soup.select_one("h1")
    if h1:
        title = h1.get_text(strip=True)

    price_el = soup.select_one('[data-testid="price"]') or soup.select_one(".f6") or soup.select_one("span")
    price = parse_price_number(price_el.get_text(" ", strip=True)) if price_el else None

    currency = "NGN"
    img = None
    img_el = soup.select_one("img")
    if img_el and img_el.get("src"):
        img = img_el["src"]

    availability = "unknown"
    if soup.find(string=lambda s: s and "out of stock" in s.lower()):
        availability = "unavailable"
    elif price is not None:
        availability = "available"

    ref_price = None
    old = soup.select_one("del") or soup.select_one(".old")
    if old:
        ref_price = parse_price_number(old.get_text(" ", strip=True))

    return ProductData(
        title=title or "Konga Product",
        price=price,
        currency=currency,
        image=img,
        availability=availability,
        reference_price=ref_price
    )
