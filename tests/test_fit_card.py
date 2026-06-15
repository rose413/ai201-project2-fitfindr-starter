# tests/test_fit_card.py
#
# Automated evaluation tests for create_fit_card().
#
# Tests marked @requires_api call the real Groq LLM and are skipped
# automatically when GROQ_API_KEY is not set (e.g. in CI without secrets).
# Run locally with a valid key to exercise the full LLM path.
#
# All @requires_api tests print the generated captions so you can visually
# audit tone — run with `pytest -s tests/test_fit_card.py` to see them.

import os
import pytest

from tools import create_fit_card
from utils.data_loader import load_listings

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

requires_api = pytest.mark.skipif(
    not os.environ.get("GROQ_API_KEY"),
    reason="GROQ_API_KEY not set — skipping live LLM test",
)

LISTINGS = load_listings()
LEVI_JEANS = next(item for item in LISTINGS if "levi" in item["title"].lower())
Y2K_TEE = next(item for item in LISTINGS if "y2k" in item["title"].lower())
FLANNEL = next(item for item in LISTINGS if "flannel" in item["title"].lower())

OUTFIT_JEANS = (
    "Vintage Levi's 501s paired with a white ribbed tank and chunky white sneakers — "
    "effortless off-duty denim energy."
)
OUTFIT_TEE = (
    "Y2K baby tee tucked into wide-leg khaki trousers with black combat boots — "
    "early-2000s meets modern editorial."
)
OUTFIT_FLANNEL = (
    "Oversized flannel worn open over a black cropped zip hoodie with baggy dark-wash "
    "jeans and combat boots — full grunge-streetwear layering."
)


# ---------------------------------------------------------------------------
# No-API tests (guard logic only)
# ---------------------------------------------------------------------------

def test_fit_card_empty_string_returns_error():
    """An empty outfit string triggers the error message without raising."""
    result = create_fit_card("", LEVI_JEANS)
    assert isinstance(result, str)
    assert len(result.strip()) > 0
    assert "couldn't generate" in result.lower()

def test_fit_card_whitespace_only_returns_error():
    """A whitespace-only outfit string is treated the same as empty."""
    result = create_fit_card("   \t\n  ", LEVI_JEANS)
    assert "couldn't generate" in result.lower()

def test_fit_card_error_message_suggests_start_over():
    """The error message should prompt the user to start over."""
    result = create_fit_card("", LEVI_JEANS)
    assert "start over" in result.lower()

def test_fit_card_empty_outfit_no_api_call():
    """Empty outfit returns immediately — no API key needed confirms no network call."""
    original_key = os.environ.pop("GROQ_API_KEY", None)
    try:
        result = create_fit_card("", LEVI_JEANS)
        assert "couldn't generate" in result.lower()
    finally:
        if original_key:
            os.environ["GROQ_API_KEY"] = original_key


# ---------------------------------------------------------------------------
# Live LLM tests (require GROQ_API_KEY)
# ---------------------------------------------------------------------------

@requires_api
def test_fit_card_returns_nonempty_string():
    """Valid inputs produce a non-empty caption string."""
    result = create_fit_card(OUTFIT_JEANS, LEVI_JEANS)
    print(f"\n--- Fit Card (jeans) ---\n{result}")
    assert isinstance(result, str)
    assert len(result.strip()) > 0

@requires_api
def test_fit_card_mentions_platform():
    """Caption should include the platform name (depop, thredUp, poshmark)."""
    result = create_fit_card(OUTFIT_JEANS, LEVI_JEANS)
    print(f"\n--- Fit Card (platform check) ---\n{result}")
    assert LEVI_JEANS["platform"].lower() in result.lower()

@requires_api
def test_fit_card_mentions_price():
    """Caption should reference the item price — accepts digits ('38') or words ('thirty-eight')."""
    result = create_fit_card(OUTFIT_JEANS, LEVI_JEANS)
    price_digits = str(int(LEVI_JEANS["price"]))       # "38"
    price_words = ("thirty", "eight")                   # written-out form the LLM might use
    mentions_digits = price_digits in result
    mentions_words = all(w in result.lower() for w in price_words)
    assert mentions_digits or mentions_words, (
        f"Expected price to appear as digits ({price_digits!r}) or words {price_words} in:\n{result}"
    )

@requires_api
def test_fit_card_variety_different_items():
    """Two distinct item+outfit pairs produce different captions (output varies)."""
    result_a = create_fit_card(OUTFIT_JEANS, LEVI_JEANS)
    result_b = create_fit_card(OUTFIT_TEE, Y2K_TEE)

    print(f"\n--- Fit Card A (jeans) ---\n{result_a}")
    print(f"\n--- Fit Card B (y2k tee) ---\n{result_b}")

    assert result_a != result_b, "Two different inputs produced identical captions"

@requires_api
def test_fit_card_variety_same_item_differs():
    """The same item called twice should produce different captions (temperature > 0)."""
    result_1 = create_fit_card(OUTFIT_FLANNEL, FLANNEL)
    result_2 = create_fit_card(OUTFIT_FLANNEL, FLANNEL)

    print(f"\n--- Fit Card run 1 ---\n{result_1}")
    print(f"\n--- Fit Card run 2 ---\n{result_2}")

    # At temperature=1.0 outputs are rarely identical; flag if they are
    assert result_1 != result_2, (
        "Both runs produced the exact same caption — check that temperature=1.0 is set"
    )

@requires_api
def test_fit_card_audit_log_three_captions():
    """Generate and print three captions for manual tone review."""
    items_outfits = [
        (LEVI_JEANS, OUTFIT_JEANS),
        (Y2K_TEE, OUTFIT_TEE),
        (FLANNEL, OUTFIT_FLANNEL),
    ]
    captions = []
    for item, outfit in items_outfits:
        result = create_fit_card(outfit, item)
        captions.append(result)
        print(f"\n--- {item['title']} ---\n{result}")

    # All three should be non-empty and distinct
    assert all(len(c.strip()) > 0 for c in captions)
    assert len(set(captions)) == len(captions), "Duplicate captions detected across different inputs"
