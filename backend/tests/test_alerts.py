from backend.services.pricing_service import compute_discount_percent

def test_discount_percent():
    assert compute_discount_percent(100, 80) == 20.0
    assert compute_discount_percent(100, 100) == 0.0
    assert compute_discount_percent(0, 50) == 0.0
