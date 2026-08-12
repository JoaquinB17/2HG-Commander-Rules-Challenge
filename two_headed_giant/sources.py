"""Fetching and caching the two upstream data sources.

MTGJSON supplies precon decklists; Scryfall supplies the `is:commander`
universe, which is both the eligibility authority and the card-data source.
Everything is cached under ./data so re-runs are offline.
"""

from __future__ import annotations

import json
import sys
import time
import urllib.parse

import requests

from . import CACHE_DIR

SCRYFALL = "https://api.scryfall.com"
MTGJSON = "https://mtgjson.com/api/v5"
HEADERS = {"User-Agent": "two-headed-giant-builder/4.0", "Accept": "application/json"}
REQUEST_DELAY = 0.1  # Scryfall asks for 50-100ms between requests.


def _request(session: requests.Session, method: str, url: str, tries: int = 5, **kwargs) -> dict:
    for attempt in range(tries):
        response = session.request(method, url, headers=HEADERS, timeout=60, **kwargs)
        if response.status_code in (429, 500, 502, 503, 504):
            wait = 2**attempt
            print(f"  HTTP {response.status_code}, retrying in {wait}s", file=sys.stderr)
            time.sleep(wait)
            continue
        response.raise_for_status()
        return response.json()
    raise RuntimeError(f"gave up on {url}")


def fetch_commander_decks(session: requests.Session) -> list[dict]:
    listing = [d for d in _request(session, "GET", f"{MTGJSON}/DeckList.json")["data"]
               if d["type"] == "Commander Deck"]
    decks = []
    for i, entry in enumerate(listing, 1):
        decks.append(_request(session, "GET", f"{MTGJSON}/decks/{entry['fileName']}.json")["data"])
        if i % 40 == 0 or i == len(listing):
            print(f"  {i}/{len(listing)} decklists")
        time.sleep(0.05)
    return decks


def fetch_is_commander_cards(session: requests.Session) -> dict[str, dict]:
    """Every paper card Scryfall considers a legal commander, keyed by oracle id.

    This single fetch is both the eligibility authority and the source of card
    data, so there is no separate /cards/collection stage to drift out of sync.
    """
    url = f"{SCRYFALL}/cards/search?" + urllib.parse.urlencode(
        {"q": "is:commander game:paper", "unique": "cards"})
    cards: dict[str, dict] = {}
    page = 0
    while url:
        payload = _request(session, "GET", url)
        page += 1
        for card in payload["data"]:
            if card.get("oracle_id"):
                cards[card["oracle_id"]] = card
        if page % 5 == 0 or not payload.get("has_more"):
            print(f"  {len(cards)}/{payload.get('total_cards', '?')} commander-legal cards")
        url = payload.get("next_page") if payload.get("has_more") else None
        time.sleep(REQUEST_DELAY)
    return cards


def load_data(refresh: bool) -> tuple[list[dict], dict[str, dict], dict[str, dict]]:
    """Load decklists, the set index and card data, fetching only what is missing."""
    CACHE_DIR.mkdir(exist_ok=True)
    decks_path = CACHE_DIR / "mtgjson_commander_decks.json"
    sets_path = CACHE_DIR / "scryfall_sets.json"
    cards_path = CACHE_DIR / "scryfall_is_commander.json"

    with requests.Session() as session:
        if refresh or not decks_path.exists():
            print("Downloading precon Commander decklists from MTGJSON...")
            decks = fetch_commander_decks(session)
            decks_path.write_text(json.dumps(decks), "utf-8")
        else:
            decks = json.loads(decks_path.read_text("utf-8"))

        if refresh or not sets_path.exists():
            print("Downloading set index from Scryfall...")
            sets = {s["code"].lower(): s
                    for s in _request(session, "GET", f"{SCRYFALL}/sets")["data"]}
            sets_path.write_text(json.dumps(sets), "utf-8")
        else:
            sets = json.loads(sets_path.read_text("utf-8"))

        if refresh or not cards_path.exists():
            print("Downloading commander-legal cards from Scryfall (is:commander)...")
            cards = fetch_is_commander_cards(session)
            cards_path.write_text(json.dumps(cards), "utf-8")
        else:
            cards = json.loads(cards_path.read_text("utf-8"))
            print(f"Using cached data in {CACHE_DIR} (pass --refresh to re-download)")

    return decks, sets, cards
