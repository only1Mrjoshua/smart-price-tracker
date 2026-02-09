from pathlib import Path

from backend.scrapers.jumia import fetch_product_data_from_html as jumia
from backend.scrapers.konga import fetch_product_data_from_html as konga
from backend.scrapers.ebay import fetch_product_data_from_html as ebay

SAMPLES = Path(__file__).parent / "samples"

def test_jumia_sample():
    html = (SAMPLES / "jumia_product.html").read_text(encoding="utf-8")
    data = jumia(html)
    assert data.title
    # sample may not contain a real price; just ensure no crash
    assert data.currency

def test_konga_sample():
    html = (SAMPLES / "konga_product.html").read_text(encoding="utf-8")
    data = konga(html)
    assert data.title
    assert data.currency

def test_ebay_sample():
    html = (SAMPLES / "ebay_product.html").read_text(encoding="utf-8")
    data = ebay(html)
    assert data.title
