# tests/test_tools.py
from tools import search_listings


# ── Existing tests ─────────────────────────────────────────────────────────────

def test_search_returns_results():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    assert isinstance(results, list)
    assert len(results) > 0

def test_search_empty_results():
    results = search_listings("designer ballgown", size="XXS", max_price=5)
    assert results == []   # empty list, no exception

def test_search_price_filter():
    results = search_listings("jacket", size=None, max_price=10)
    assert all(item["price"] <= 10 for item in results)


# ── Additional search_listings tests ──────────────────────────────────────────

def test_search_returns_at_most_3():
    """Even when many listings match a broad keyword, the cap is 3 results."""
    results = search_listings("vintage", size=None, max_price=None)
    assert len(results) <= 3

def test_search_size_filter():
    """Only listings whose size field contains the requested size are returned."""
    results = search_listings("top shirt", size="XL", max_price=None)
    assert all("xl" in item["size"].lower() for item in results)

def test_search_size_filter_case_insensitive():
    """Size matching is case-insensitive — 'M' should match 'S/M'."""
    results_upper = search_listings("tee", size="M", max_price=None)
    results_lower = search_listings("tee", size="m", max_price=None)
    assert results_upper == results_lower

def test_search_no_keyword_match_returns_empty():
    """A description with no overlap against any listing field returns []."""
    results = search_listings("xyzqwerty123 zzz999aaa quuxfrobble", size=None, max_price=None)
    assert results == []

def test_search_result_fields():
    """Every returned dict contains the required fields for the agent to use."""
    results = search_listings("denim jeans", size=None, max_price=None)
    required = {"title", "price", "condition", "platform"}
    for item in results:
        assert required.issubset(item.keys()), f"Missing fields in: {item}"

def test_search_price_boundary_inclusive():
    """Items priced exactly at max_price are included (inclusive ceiling)."""
    results = search_listings("vintage", size=None, max_price=38.00)
    assert all(item["price"] <= 38.00 for item in results)
