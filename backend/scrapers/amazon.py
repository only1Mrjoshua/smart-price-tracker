from backend.scrapers.base import ProductData, parse_price_number, soup_from_html

def fetch_product_data_from_html(html: str) -> ProductData:
    soup = soup_from_html(html)

    title = ""
    t = soup.select_one("#productTitle")
    if t:
        title = t.get_text(strip=True)

    # price can be in various places
    price_el = (soup.select_one("#priceblock_ourprice")
                or soup.select_one("#priceblock_dealprice")
                or soup.select_one(".a-price .a-offscreen"))
    price = parse_price_number(price_el.get_text(" ", strip=True)) if price_el else None

    currency = "USD"
    img = None
    img_el = soup.select_one("#imgTagWrapperId img") or soup.select_one("img")
    if img_el and img_el.get("src"):
        img = img_el["src"]

    availability = "unknown"
    avail = soup.select_one("#availability")
    if avail:
        text = avail.get_text(" ", strip=True).lower()
        if "in stock" in text:
            availability = "available"
        elif "out of stock" in text or "unavailable" in text:
            availability = "unavailable"

    # reference price
    ref_price = None
    old = soup.select_one(".a-text-price .a-offscreen")
    if old:
        ref_price = parse_price_number(old.get_text(" ", strip=True))

    return ProductData(
        title=title or "Amazon Product",
        price=price,
        currency=currency,
        image=img,
        availability=availability,
        reference_price=ref_price
    )
