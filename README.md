# FitFindr

FitFindr is an AI agent that helps users find secondhand clothing and style it with their existing wardrobe. A user describes what they are looking for in plain English; the agent searches a mock dataset of 40 thrifted listings, generates outfit ideas using their wardrobe, and produces a shareable social-media caption.

---

## Project Structure

```
ai201-project2-fitfindr-starter/
├── data/
│   ├── listings.json          # 40 mock secondhand listings
│   └── wardrobe_schema.json   # Wardrobe format + example wardrobe (10 items)
├── utils/
│   └── data_loader.py         # load_listings(), get_example_wardrobe(), get_empty_wardrobe()
├── tests/
│   ├── test_tools.py          # search_listings unit tests
│   ├── test_suggest_outfit.py # suggest_outfit tests 
│   └── test_fit_card.py       # create_fit_card tests 
├── tools.py                   # The three agent tools
├── agent.py                   # Planning loop and query parser
├── app.py                     # Gradio web interface
├── planning.md                # Design spec and implementation notes
└── requirements.txt           # groq, gradio, python-dotenv, pytest
```

---

## Setup

```bash
pip install -r requirements.txt
```

Create a `.env` file in the project root with your Groq API key (free at [console.groq.com](https://console.groq.com)):

```
GROQ_API_KEY=your_key_here
```

**Run the web app:**
```bash
python app.py
```
Then open the localhost URL shown in your terminal (usually `http://localhost:7860`).

**Run the CLI demo (happy path + failure case):**
```bash
python agent.py
```

**Run the test suite:**
```bash
pytest tests/                        # no-API tests only
pytest -s tests/test_fit_card.py     # live LLM tests with caption output
```

---

## Tool Inventory

### `search_listings`

**Purpose:** Searches the mock listings dataset for items matching the user's description, optionally filtered by size and price.

| Parameter | Type | Description |
|-----------|------|-------------|
| `description` | `str` | Keywords describing the clothing item (e.g., `"vintage graphic tee"`) |
| `size` | `str \| None` | Size to filter by; `None` skips size filtering. Case-insensitive substring match (`"M"` matches `"S/M"`) |
| `max_price` | `float \| None` | Inclusive price ceiling; `None` skips price filtering |

**Returns:** `list[dict]` — up to 3 matching listing dicts sorted by keyword relevance score (highest first). Returns `[]` if nothing matches; never raises an exception.

Each listing dict contains: `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, `platform`.

---

### `suggest_outfit`

**Purpose:** Given the thrifted item and the user's wardrobe, suggests 1–2 complete outfit combinations using an LLM.

| Parameter | Type | Description |
|-----------|------|-------------|
| `new_item` | `dict` | A listing dict returned by `search_listings` |
| `wardrobe` | `dict` | A wardrobe dict with an `'items'` key (may be empty) |

**Returns:** `str` — a non-empty string with outfit suggestions. If the wardrobe is empty, returns general styling advice (what pairs well, what vibe it suits) rather than wardrobe-specific combinations. Uses `llama-3.3-70b-versatile` via Groq.

---

### `create_fit_card`

**Purpose:** Generates a short, shareable social-media caption for the completed outfit.

| Parameter | Type | Description |
|-----------|------|-------------|
| `outfit` | `str` | The outfit suggestion string produced by `suggest_outfit` |
| `new_item` | `dict` | The listing dict for the thrifted item |

**Returns:** `str` — a 1–2 sentence Instagram-style caption mentioning the item name, price, and platform. Called at `temperature=1.0` so captions vary across runs. Returns a descriptive error message string (not an exception) if `outfit` is empty or whitespace.

---

## Complete Demo

Run `python agent.py` to see both paths. The `__main__` block in `agent.py` runs two queries: one happy path and one deliberate failure.

---

### Happy path — all 3 tools called in sequence

**Query:** `"looking for a vintage graphic tee under $30"`

**Step 1 — `search_listings` is called** because the agent has no item yet. It can't suggest an outfit or write a caption without a concrete listing dict to work from. The agent passes the parsed description, size (`None` — none specified in this query), and `max_price=30.0`:

```
============================================================
[search_listings] TOOL CALLED
  description : 'looking for a vintage graphic tee'
  size        : None
  max_price   : 30.0
[search_listings] Loaded 40 total listings from dataset
[search_listings] 24 listings remain after price/size filter
[search_listings] Scoring by keyword overlap: {'graphic', 'tee', 'for', 'looking', 'vintage', 'a'}
[search_listings] 24 listings scored > 0 for keyword overlap
[search_listings] RETURNING top 3 result(s):
  [0] Y2K Baby Tee - Butterfly Print - $18.0 (depop)
  [1] Graphic Tee - 2003 Tour Bootleg Style - $24.0 (depop)
  [2] Mesh Long-Sleeve Top - Black - $15.0 (depop)
```

The agent stores `results[0]` (the Y2K Baby Tee dict) in `session["selected_item"]`.

**Step 2 — `suggest_outfit` is called** because the agent now has a selected item and needs styling advice before it can write a caption. The Y2K Baby Tee dict flows directly from `session["selected_item"]` into `new_item` — the user does not re-enter it:

```
============================================================
[suggest_outfit] TOOL CALLED
  new_item : 'Y2K Baby Tee - Butterfly Print' - $18.0 (depop)
  wardrobe : 10 item(s)
  >> STATE PASSED IN: selected_item from search_listings -> new_item here
[suggest_outfit] Wardrobe has items — building wardrobe-specific prompt
[suggest_outfit] Calling LLM (llama-3.3-70b-versatile)...
[suggest_outfit] RETURNING outfit suggestion (607 chars)
```

The agent stores the LLM response in `session["outfit_suggestion"]`.

**Step 3 — `create_fit_card` is called** because the agent now has both a selected item and an outfit suggestion — everything needed to generate a caption. Both pass in from the session without user re-entry:

```
============================================================
[create_fit_card] TOOL CALLED
  new_item : 'Y2K Baby Tee - Butterfly Print'
  outfit   : 'You could wear the Y2K Baby Tee with your baggy straight-leg jeans and chunky wh...'
  >> STATE PASSED IN: outfit_suggestion from suggest_outfit -> outfit here
[create_fit_card] Calling LLM (llama-3.3-70b-versatile, temperature=1.0 for variety)...
[create_fit_card] RETURNING fit card (300 chars)
```

**Final output to user:**
```
Found: Y2K Baby Tee - Butterfly Print

Outfit: You could wear the Y2K Baby Tee with your baggy straight-leg jeans and chunky
white sneakers for a super chill, laid-back vibe — just tuck the tee into your jeans
to balance out the volume. The dark wash of the jeans will ground the playful butterfly
print, and the chunky sneakers will add a cool, streetwear touch.

Fit card: I'm loving the laid-back vibes of my Y2K Baby Tee from Depop, which I scored
for eighteen bucks, paired with baggy straight-leg jeans and chunky white sneakers for
a super chill look.
```

---

### Failure path — agent stops early, tools 2 and 3 never called

**Query:** `"designer ballgown size XXS under $5"` (a deliberately impossible query — no ballgowns in the dataset, price ceiling of $5 eliminates nearly everything)

The agent calls `search_listings` up to 3 times with progressively relaxed constraints. All 3 return empty. `suggest_outfit` and `create_fit_card` are never reached:

```
[search_listings] TOOL CALLED — description='designer ballgown', size='XXS', max_price=5.0
[search_listings] 0 listings remain after price/size filter
[search_listings] RETURNING top 0 result(s):

  → Empty. Retry: drop size constraint.

[search_listings] TOOL CALLED — description='designer ballgown', size=None, max_price=5.0
[search_listings] 0 listings remain after price/size filter
[search_listings] RETURNING top 0 result(s):

  → Still empty. Retry: drop price constraint too.

[search_listings] TOOL CALLED — description='designer ballgown', size=None, max_price=None
[search_listings] 40 listings remain after price/size filter
[search_listings] 0 listings scored > 0 for keyword overlap
[search_listings] RETURNING top 0 result(s):

  → Still empty. No match for "ballgown" anywhere in the dataset.
```

**Response to user (specific and actionable):**
```
No listings matched your search even after relaxing size and price constraints.
Try a different description or broader search terms.
```

**Key difference from happy path:** the happy path calls all 3 tools in sequence; the failure path calls only `search_listings` (3 times as part of the fallback) and then returns. `suggest_outfit` and `create_fit_card` are never invoked because `session["selected_item"]` is never set.

---

## Planning Loop

The agent entry point is `run_agent(query, wardrobe)` in `agent.py`. It follows these steps:

**1. Parse the query** — `_parse_query()` uses regex to extract three values from the natural-language query:
- `size`: looks for an explicit `"size XYZ"` pattern first, then falls back to bare size tokens (`XXS`, `XS`, `S/M`, `M/L`, `XL`, `XXL`, etc.) with a negative lookbehind to avoid matching `'m'` inside contractions like `"I'm"`.
- `max_price`: matches worded phrases (`under/max/less than/up to/below $X`) first, then a bare `$X` pattern.
- `description`: taken from the first sentence only (split on `.!?`) so wardrobe context in a longer query (`"I mostly wear baggy jeans..."`) does not pollute keyword scoring. Size tokens and price tokens are stripped from the description.

**2. Search with two-level fallback** — `search_listings` is called up to three times:
- Call 1: full constraints (`size`, `max_price`)
- Call 2 (if empty): drop `size`, keep `max_price`
- Call 3 (if still empty): drop both constraints

**3. Validate the top result** — checks that the selected listing contains `id`, `title`, and `price` before proceeding. Missing fields cause an early exit with an error message.

**4. Suggest outfit** — calls `suggest_outfit(selected_item, wardrobe)`. `suggest_outfit` handles empty wardrobes internally; the planning loop does not branch on wardrobe state.

**5. Generate fit card** — calls `create_fit_card(outfit_suggestion, selected_item)`.

**6. Return the session** — the function always returns the session dict. Check `session["error"]` first; if it is not `None`, the interaction ended early and `outfit_suggestion`/`fit_card` will be `None`.

---

## State Management

All state for a single interaction is stored in a session dict initialized by `_new_session()`:

```python
{
    "query":             str,   # original user input
    "parsed":            dict,  # {"description": ..., "size": ..., "max_price": ...}
    "search_results":    list,  # all results returned by search_listings
    "selected_item":     dict,  # results[0] — passed into suggest_outfit and create_fit_card
    "wardrobe":          dict,  # the wardrobe passed into run_agent
    "outfit_suggestion": str,   # returned by suggest_outfit, passed into create_fit_card
    "fit_card":          str,   # returned by create_fit_card
    "error":             str,   # non-None if the run ended early
}
```

State flows linearly through the tools:
- `search_listings` → `session["selected_item"]` → `suggest_outfit` (as `new_item`)
- `suggest_outfit` → `session["outfit_suggestion"]` → `create_fit_card` (as `outfit`)
- Both `selected_item` and `outfit_suggestion` → `create_fit_card`

The Gradio `handle_query()` in `app.py` maps session keys to the three output panels: `selected_item` is formatted into a readable label string, `outfit_suggestion` goes to the outfit panel, and `fit_card` goes to the caption panel.

---

## Error Handling

| Tool | Failure mode | Response |
|------|-------------|----------|
| `search_listings` | No listings match keyword scoring | Returns `[]`. Agent retries up to 2x (drop size, then price). After all three calls return empty, sets `session["error"]` and returns early — `suggest_outfit` is never called. |
| `search_listings` | Top result is missing required fields (`id`, `title`, `price`) | Agent sets `session["error"]` with a descriptive message and returns early. |
| `suggest_outfit` | `wardrobe['items']` is empty or key is missing | Switches to a general styling LLM prompt; never raises or returns an empty string. The planning loop continues normally. |
| `suggest_outfit` | LLM returns an empty response | Returns a fallback error string. Agent checks for this and sets `session["error"]`. |
| `create_fit_card` | `outfit` is empty or whitespace | Returns a descriptive error string **without calling the LLM**. Confirmed by `test_fit_card_empty_outfit_no_api_call`, which temporarily removes `GROQ_API_KEY` and asserts the function still returns the expected message — proving no network call is made. |
| `create_fit_card` | LLM returns an empty response | Returns a fallback error string prompting the user to start a new search. |

**Concrete failure example from testing (`test_search_empty_results` and the CLI demo):**

The deliberately impossible query `"designer ballgown size XXS under $5"` triggers the full fallback chain in `search_listings` across 3 calls (all returning `[]`), then the agent sets `session["error"]` and returns — `suggest_outfit` and `create_fit_card` are never called. The user-facing error message is specific and actionable:

> *"No listings matched your search even after relaxing size and price constraints. Try a different description or broader search terms."*

The full terminal output and a side-by-side comparison with the happy path are in the **Complete Demo** section above. The `test_search_empty_results` test in `tests/test_tools.py` also asserts this query returns `[]` without raising.

**Concrete `create_fit_card` guard test (`test_fit_card_empty_outfit_no_api_call`):**

This test temporarily removes `GROQ_API_KEY` from the environment and calls `create_fit_card("", item)`. The function must return its error string without attempting a network call — confirmed because without the key the Groq client would raise, but the test passes cleanly, proving the guard fires before the LLM is ever initialized.

---

## Spec Reflection

**What matched the spec:**
- The session dict structure matches exactly what was designed in `planning.md`: the eight keys, linear state flow, and `session["error"]` as the early-termination signal.
- The `suggest_outfit` empty-wardrobe branch works as specced: rather than failing, it calls the LLM with a general styling prompt and the planning loop continues to `create_fit_card`.
- The `create_fit_card` error guard returns a string message instead of raising an exception, matching the spec requirement.

**What diverged from the spec:**
- The original spec described a single fallback for `search_listings` (drop size *or* price on retry). The implementation uses two sequential retries — first drop size, then drop price — which is more thorough but means `search_listings` can be called up to 3 times instead of 2.
- The spec's "Selection Phase" error check mentioned validating against `title`, `price`, and `id`. The implementation checks exactly those three fields (`required_fields = {"id", "title", "price"}`), which is a direct match, but the spec also mentioned checking for "malformed" items more broadly. In practice, if any other field is missing (like `platform`), the agent proceeds and the missing data shows up as `"N/A"` in the output rather than triggering an error.
- The keyword scoring in `search_listings` tokenizes the description with `.split()` and uses a `set()` to deduplicate tokens. This was not in the original spec but prevents a word repeated in the query (e.g., `"tee tee"`) from artificially inflating a listing's score.

---

## AI Usage

### Instance 1 — Implementing `search_listings`

**What I gave the AI:** The Tool 1 spec from `planning.md` (inputs with types, return value description including the field list, and the failure mode: "return `[]`, do not raise"), plus the five-step TODO comment inside the function stub, and the note that `load_listings()` from `utils/data_loader.py` was the data source.

**What it produced:** A working implementation that loaded listings, filtered by price and size, scored by keyword overlap using a joined searchable string (title + description + category + style_tags + colors + brand), dropped zero-score listings, and sorted descending. The initial output returned all matching listings.

**What I changed before using it:** Added `[:3]` to cap results at 3. Changed the keyword tokenization to use `set(description.lower().split())` so repeated words in the query don't double-count a keyword match. Verified with `test_search_returns_at_most_3` (broad query `"vintage"` returns at most 3) and `test_search_size_filter_case_insensitive` (`"M"` and `"m"` return the same results).

---

### Instance 2 — Implementing `create_fit_card`

**What I gave the AI:** The Tool 3 spec from `planning.md` (inputs with types, the caption style rules — casual tone, mention item name/price/platform once each, no hashtags or emojis — and the failure mode: "return a descriptive error string if outfit is empty, do not raise an exception"), plus the architecture diagram showing `create_fit_card` receives `outfit_suggestion` from `suggest_outfit` and `selected_item` from the session.

**What it produced:** A function that checked for an empty outfit string, built a prompt embedding the item title, price, and platform alongside the outfit description, called the Groq LLM, and returned the stripped response. The initial output used the default `temperature` (0 or unset), and the prompt asked for a "2–4 sentence" caption.

**What I changed before using it:** Changed the LLM call to `temperature=1.0` so captions vary across runs for the same input — this was required by the spec ("sound different each time for different inputs") and confirmed by `test_fit_card_variety_same_item_differs`. Shortened the prompt's length instruction from "2–4 sentences" to "1–2 sentences" to match the spec and keep captions concise enough for a real social-media post. Also tightened the prompt rules to add "Return only the caption text, nothing else" after the AI's first draft occasionally prepended a label like `"Caption: ..."` before the actual text.

---

### Instance 3 — Implementing the `agent.py` planning loop

**What I gave the AI:** The Planning Loop and State Management sections from `planning.md` (the five-phase loop description, the session dict schema with all eight keys, and the architecture diagram), plus the `_new_session()` stub and the `run_agent()` TODO steps already written in the file.

**What it produced:** A working `run_agent()` that initialized the session, called `_parse_query()`, called `search_listings` once, selected `results[0]`, called `suggest_outfit`, called `create_fit_card`, and returned the session. It also produced `_parse_query()` using a single regex for size and a single regex for price.

**What I changed before using it:** Added the two-level fallback search (retry without `size`, then without `max_price`) because a single call with all constraints failed silently on common queries like `"vintage tee size M under $30"` when no M-sized items were under $30. The spec had described one fallback; the implementation ended up needing two to handle the dataset reliably. Also expanded `_parse_query()`'s size regex to include the negative lookbehind (`(?<!')`) so `"I'm looking for..."` would not incorrectly extract `"M"` as a size token — the AI's initial version matched bare `M` without this guard.

---

### Instance 4 — Generating the `test_fit_card.py` test suite

**What I gave the AI:** The Tool 3 spec from `planning.md` (the `create_fit_card` failure mode, the caption style rules, and the `temperature=1.0` requirement for variety), plus the AI Tool Plan entry that said the test should "assert that generated fit cards are non-identical for different inputs" and "log the text output so I can audit tone."

**What it produced:** Tests for non-empty output, platform mention, and caption variety across two different items. Tests were wrapped in a `@requires_api` marker that skips them when `GROQ_API_KEY` is not set, which was a pattern I kept as-is.

**What I changed before using it:** The price-check test originally used `assert str(item["price"]) in result`, which would fail whenever the LLM wrote out the number in words (e.g., `"thirty-eight dollars"`). I rewrote it to accept either the digit form (`"38"`) or the written-out form (`("thirty", "eight")`). I also added `test_fit_card_empty_outfit_no_api_call`, which temporarily pops `GROQ_API_KEY` from the environment to confirm the guard branch returns immediately without any network call — this was not in the AI's output and catches a class of bugs where the guard might call the LLM before checking its inputs.
