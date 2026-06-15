# tests/test_suggest_outfit.py
#
# Tests for suggest_outfit().
#
# Tests marked @requires_api call the real Groq LLM and are skipped
# automatically when GROQ_API_KEY is not set (e.g. in CI without secrets).
# Run locally with a valid key to exercise the full LLM path.

import os
import pytest

from tools import suggest_outfit
from utils.data_loader import get_empty_wardrobe, get_example_wardrobe, load_listings

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

requires_api = pytest.mark.skipif(
    not os.environ.get("GROQ_API_KEY"),
    reason="GROQ_API_KEY not set — skipping live LLM test",
)

# A real listing dict to use as new_item across tests
LISTINGS = load_listings()
DENIM_JACKET = next(item for item in LISTINGS if "jacket" in item["title"].lower())
Y2K_TEE = next(item for item in LISTINGS if "y2k" in item["title"].lower())


# ---------------------------------------------------------------------------
# No-API tests (guard logic only)
# ---------------------------------------------------------------------------

def test_empty_wardrobe_returns_string():
    """Empty wardrobe never raises — always returns a non-empty string."""
    result = suggest_outfit(DENIM_JACKET, get_empty_wardrobe())
    assert isinstance(result, str)
    assert len(result.strip()) > 0

# ---------------------------------------------------------------------------
# Live LLM tests (require GROQ_API_KEY)
# ---------------------------------------------------------------------------

@requires_api
def test_empty_wardrobe_returns_general_styling_advice():
    """Empty wardrobe triggers LLM general styling advice, not an error message."""
    result = suggest_outfit(DENIM_JACKET, get_empty_wardrobe())
    assert len(result.strip()) > 80, "Expected substantive styling advice, got too short a response"
    assert "add some items" not in result.lower()
    assert "wardrobe is currently empty" not in result.lower()

@requires_api
def test_wardrobe_missing_items_key_treated_as_empty():
    """A wardrobe dict without an 'items' key is handled gracefully via LLM advice."""
    result = suggest_outfit(DENIM_JACKET, {})
    assert isinstance(result, str)
    assert len(result.strip()) > 0

@requires_api
def test_suggest_outfit_with_example_wardrobe_returns_string():
    """With a populated wardrobe the function returns real styling advice."""
    result = suggest_outfit(DENIM_JACKET, get_example_wardrobe())
    assert isinstance(result, str)
    assert len(result.strip()) > 0

@requires_api
def test_suggest_outfit_not_the_empty_wardrobe_message():
    """The LLM response should not echo back the empty-wardrobe error message."""
    result = suggest_outfit(DENIM_JACKET, get_example_wardrobe())
    assert "add some items" not in result.lower()

@requires_api
def test_suggest_outfit_substantial_response():
    """The LLM should return more than a one-liner — real advice takes sentences."""
    result = suggest_outfit(Y2K_TEE, get_example_wardrobe())
    assert len(result) > 80, f"Response seems too short: {result!r}"

@requires_api
def test_suggest_outfit_different_items_differ():
    """Two distinct items should produce different outfit suggestions."""
    result_jacket = suggest_outfit(DENIM_JACKET, get_example_wardrobe())
    result_tee = suggest_outfit(Y2K_TEE, get_example_wardrobe())
    assert result_jacket != result_tee
