"""
agent.py

The FitFindr planning loop. Orchestrates the three tools in response to a
natural language user query, passing state between them via a session dict.

Complete tools.py and test each tool in isolation before implementing this file.

Usage (once implemented):
    from agent import run_agent
    from utils.data_loader import get_example_wardrobe

    result = run_agent(
        query="vintage graphic tee under $30, size M",
        wardrobe=get_example_wardrobe(),
    )
    print(result["fit_card"])
    print(result["error"])   # None on success
"""

import re

from tools import search_listings, suggest_outfit, create_fit_card


# ── query parser ──────────────────────────────────────────────────────────────

def _parse_query(query: str) -> dict:
    """
    Extract description, size, and max_price from a natural-language query using
    regex. Everything that isn't a size token or price token becomes the description.

    Examples:
        "vintage graphic tee under $30, size M"
        → {"description": "vintage graphic tee", "size": "M", "max_price": 30.0}

        "designer ballgown size XXS under $5"
        → {"description": "designer ballgown", "size": "XXS", "max_price": 5.0}
    """
    # --- size: "size XYZ" first, then bare size tokens ---
    # Note: bare token uses (?<!') to avoid matching 'm' inside contractions like "I'm"
    size = None
    explicit = re.search(r'\bsize\s+([A-Z0-9]{1,5}(?:/[A-Z0-9]{1,5})?)\b', query, re.IGNORECASE)
    if explicit:
        size = explicit.group(1).upper()
    else:
        bare = re.search(r"(?<!')\b(XXS|XS|S/M|M/L|XL/XXL|XXL|XL|SM|ML|[SML])\b", query, re.IGNORECASE)
        if bare:
            size = bare.group(1).upper()

    # --- max_price: "under/max/less than $X" first, then bare "$X" ---
    max_price = None
    worded = re.search(
        r'(?:under|max(?:imum)?|less\s+than|up\s+to|below)\s+\$?(\d+(?:\.\d+)?)',
        query, re.IGNORECASE,
    )
    if worded:
        max_price = float(worded.group(1))
    else:
        dollar = re.search(r'\$(\d+(?:\.\d+)?)', query)
        if dollar:
            max_price = float(dollar.group(1))

    # --- description: use only the first sentence to avoid wardrobe/style context
    #     polluting the search keywords (e.g. "I mostly wear baggy jeans...")
    first_sentence = re.split(r'[.!?]', query)[0]
    desc = first_sentence
    desc = re.sub(r'\bsize\s+\S+', '', desc, flags=re.IGNORECASE)
    desc = re.sub(
        r'(?:under|max(?:imum)?|less\s+than|up\s+to|below)\s+\$?\d+(?:\.\d+)?',
        '', desc, flags=re.IGNORECASE,
    )
    desc = re.sub(r'\$\d+(?:\.\d+)?', '', desc)
    desc = re.sub(r"(?<!')\b(XXS|XS|S/M|M/L|XL/XXL|XXL|XL|SM|ML|[SML])\b", '', desc, flags=re.IGNORECASE)
    desc = re.sub(r'[\s,]+', ' ', desc).strip().strip(',').strip()

    return {
        "description": desc if desc else query,
        "size": size,
        "max_price": max_price,
    }


# ── session state ─────────────────────────────────────────────────────────────

def _new_session(query: str, wardrobe: dict) -> dict:
    """
    Initialize and return a fresh session dict for one user interaction.

    The session dict is the single source of truth for everything that happens
    during a run — it stores the original query, parsed parameters, tool results,
    and any error that caused early termination.

    You may add fields to this dict as needed for your implementation.
    """
    return {
        "query": query,              # original user query
        "parsed": {},                # extracted description / size / max_price
        "search_results": [],        # list of matching listing dicts
        "selected_item": None,       # top result, passed into suggest_outfit
        "wardrobe": wardrobe,        # user's wardrobe dict
        "outfit_suggestion": None,   # string returned by suggest_outfit
        "fit_card": None,            # string returned by create_fit_card
        "error": None,               # set if the interaction ended early
    }


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Main agent entry point. Runs the FitFindr planning loop for a single
    user interaction and returns the completed session dict.

    Args:
        query:    Natural language user request
                  (e.g., "vintage graphic tee under $30, size M")
        wardrobe: User's wardrobe dict — use get_example_wardrobe() or
                  get_empty_wardrobe() from utils/data_loader.py

    Returns:
        The session dict after the interaction completes. Check session["error"]
        first — if it is not None, the interaction ended early and the other
        output fields (outfit_suggestion, fit_card) will be None.

    TODO — implement this function using the planning loop you designed in planning.md:

        Step 1: Initialize the session with _new_session().

        Step 2: Parse the user's query to extract a description, size, and
                max_price. You can use regex, string splitting, or ask the LLM
                to parse it — document your choice in planning.md.
                Store the result in session["parsed"].

        Step 3: Call search_listings() with the parsed parameters.
                Store results in session["search_results"].
                If no results: set session["error"] to a helpful message and
                return the session early. Do NOT proceed to suggest_outfit
                with empty input.

        Step 4: Select the item to use (e.g., the top result).
                Store it in session["selected_item"].

        Step 5: Call suggest_outfit() with the selected item and wardrobe.
                Store the result in session["outfit_suggestion"].

        Step 6: Call create_fit_card() with the outfit suggestion and selected item.
                Store the result in session["fit_card"].

        Step 7: Return the session.

    Before writing code, complete the Planning Loop and State Management sections
    of planning.md — your implementation should match what you described there.
    """
    # Step 1: Initialize session
    session = _new_session(query, wardrobe)

    # Step 2: Parse the query into structured parameters
    parsed = _parse_query(query)
    session["parsed"] = parsed
    description = parsed["description"]
    size = parsed["size"]
    max_price = parsed["max_price"]

    # Step 3: Search phase — two fallback levels before giving up
    results = search_listings(description, size=size, max_price=max_price)

    if not results:
        # Fallback 1: drop the size constraint
        results = search_listings(description, size=None, max_price=max_price)

    if not results:
        # Fallback 2: drop the price constraint as well
        results = search_listings(description, size=None, max_price=None)

    session["search_results"] = results

    if not results:
        session["error"] = (
            "No listings matched your search even after relaxing size and price "
            "constraints. Try a different description or broader search terms."
        )
        return session

    # Step 4: Selection phase — validate the top result has required fields
    selected_item = results[0]
    required_fields = {"id", "title", "price"}
    missing = required_fields - selected_item.keys()
    if missing:
        session["error"] = (
            f"The top search result is missing required fields: {', '.join(missing)}. "
            "This is a data issue — please try a different search."
        )
        return session

    session["selected_item"] = selected_item

    # Step 5: Styling phase — suggest_outfit handles empty wardrobes gracefully
    outfit_suggestion = suggest_outfit(selected_item, wardrobe)
    session["outfit_suggestion"] = outfit_suggestion

    if not outfit_suggestion or not outfit_suggestion.strip():
        session["error"] = (
            "Outfit suggestion failed to generate. Please try again with a "
            "different item."
        )
        return session

    # Step 6: Card generation phase
    fit_card = create_fit_card(outfit_suggestion, selected_item)
    session["fit_card"] = fit_card

    if not fit_card or not fit_card.strip():
        session["error"] = (
            "Fit card generation failed. Would you like to search for a new item "
            "to start over?"
        )
        return session

    # Step 7: Return the completed session
    return session


# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe, get_empty_wardrobe

    print("=== Happy path: graphic tee ===\n")
    session = run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    )
    if session["error"]:
        print(f"Error: {session['error']}")
    else:
        print(f"Found: {session['selected_item']['title']}")
        print(f"\nOutfit: {session['outfit_suggestion']}")
        print(f"\nFit card: {session['fit_card']}")

    print("\n\n=== No-results path ===\n")
    session2 = run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    )
    print(f"Error message: {session2['error']}")
