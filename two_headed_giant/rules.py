"""The tournament rules, expressed as data transformations.

Eligibility, partner mechanics, commander configurations ("heads") and the
legal two-seat teams built from them.
"""

from __future__ import annotations

import itertools
import re
from datetime import date

# Products that carry a Commander-deck label but are not a "precon set" here:
#   SLD - seven unrelated Secret Lair drops sharing one set code.
#   CMA / CM2 - Commander Anthology I & II, reprint compilations of older decks.
EXCLUDED_SET_CODES = {"SLD", "CMA", "CM2"}

WUBRG = "WUBRG"

COLOR_COMBO_NAMES = {
    "": "Colorless",
    "W": "Mono-White", "U": "Mono-Blue", "B": "Mono-Black",
    "R": "Mono-Red", "G": "Mono-Green",
    "WU": "Azorius", "WB": "Orzhov", "WR": "Boros", "WG": "Selesnya",
    "UB": "Dimir", "UR": "Izzet", "UG": "Simic",
    "BR": "Rakdos", "BG": "Golgari", "RG": "Gruul",
    "WUB": "Esper", "WUR": "Jeskai", "WUG": "Bant", "WBR": "Mardu",
    "WBG": "Abzan", "WRG": "Naya", "UBR": "Grixis", "UBG": "Sultai",
    "URG": "Temur", "BRG": "Jund",
    "WUBR": "Yore-Tiller (non-Green)", "WUBG": "Witch-Maw (non-Red)",
    "WURG": "Ink-Treader (non-Black)", "WBRG": "Dune-Brood (non-Blue)",
    "UBRG": "Glint-Eye (non-White)", "WUBRG": "Five-Color",
}


def deck_cards(deck: dict) -> list[dict]:
    """Every physical card in a precon: the commander(s) plus the 99."""
    return deck.get("commander", []) + deck.get("mainBoard", []) + deck.get("sideBoard", [])


def oracle_id_of(card: dict) -> str | None:
    """The Scryfall oracle id recorded on an MTGJSON deck entry."""
    return card.get("identifiers", {}).get("scryfallOracleId")


def oracle_text(card: dict) -> str:
    """Full oracle text, joining both halves of a double-faced card."""
    if card.get("oracle_text"):
        return card["oracle_text"]
    return "\n".join(f.get("oracle_text", "") for f in card.get("card_faces") or [])


def type_line(card: dict) -> str:
    if card.get("type_line"):
        return card["type_line"]
    faces = card.get("card_faces") or []
    return faces[0].get("type_line", "") if faces else ""


def front_name(card: dict) -> str:
    return card["name"].split(" // ")[0]


# Partner mechanics are read from oracle text, not Scryfall's `keywords` field.
# `keywords` reports plain "Partner" for cards that actually have a restricted
# variant -- Donatello's "Partner-Character select" is tagged just "Partner", and
# every "Partner with [name]" card is tagged "Partner" too. Both would be wrong.
PARTNER_WITH_RE = re.compile(r"^Partner with (.+?)(?:\s*\(|$)", re.MULTILINE)
PLAIN_PARTNER_RE = re.compile(r"^Partner(?:\s*\(|\s*$)", re.MULTILINE)
RESTRICTED_PARTNER_RE = re.compile(r"^Partner\s*[—-]\s*(.+?)(?:\s*\(|$)", re.MULTILINE)


def partner_traits(card: dict) -> dict:
    """Which partner mechanics this card has."""
    text = oracle_text(card)
    types = type_line(card)
    return {
        "partner": bool(PLAIN_PARTNER_RE.search(text)),
        "partner_with": [m.group(1).strip().rstrip(".")
                         for m in PARTNER_WITH_RE.finditer(text)],
        "restricted": [m.group(1).strip().rstrip(".")
                       for m in RESTRICTED_PARTNER_RE.finditer(text)],
        "companion": "Doctor's companion" in text,
        "doctor": "Time Lord Doctor" in types,
        "choose_background": "Choose a Background" in text,
        "background": "Background" in types.split("—")[-1] if "—" in types else False,
    }


def can_be_sole_commander(card: dict) -> bool:
    """Everything Scryfall calls a commander can lead a deck, except Backgrounds.

    Backgrounds match `is:commander` but are only ever a second commander, so
    they are the one case that still needs a local rule.
    """
    return "Background" not in type_line(card)


def partner_reason(a: dict, b: dict) -> str | None:
    """Why these two cards may be commanders together, or None."""
    ta, tb = a["traits"], b["traits"]
    if ta["partner"] and tb["partner"] and not ta["restricted"] and not tb["restricted"] \
            and not ta["partner_with"] and not tb["partner_with"]:
        return "Partner"
    names_a = {a["name"], front_name(a["card"])}
    names_b = {b["name"], front_name(b["card"])}
    if names_b & set(ta["partner_with"]) or names_a & set(tb["partner_with"]):
        return "Partner with"
    shared = set(ta["restricted"]) & set(tb["restricted"])
    if shared:
        return f"Partner—{sorted(shared)[0]}"
    if (ta["companion"] and tb["doctor"]) or (tb["companion"] and ta["doctor"]):
        return "Doctor's companion"
    if (ta["choose_background"] and tb["background"]) or \
            (tb["choose_background"] and ta["background"]):
        return "Choose a Background"
    return None


# --------------------------------------------------------------------------- #
# Shaping
# --------------------------------------------------------------------------- #
def color_key(identity) -> str:
    return "".join(c for c in WUBRG if c in identity)


def identity_name(key: str) -> str:
    return COLOR_COMBO_NAMES.get(key, key)


def dedupe_decks(decks: list[dict]) -> list[dict]:
    """Collapse identical decklists (e.g. a deck and its Collector's Edition).

    Basic lands are ignored when comparing: MTGJSON records some Collector's
    Editions with a few basics missing, which is not a real decklist difference
    and never affects which commanders are available. The shortest name wins, so
    the base deck is kept over its "... Collector's Edition" twin.
    """
    seen: dict[tuple, dict] = {}
    for deck in sorted(decks, key=lambda d: (len(d["name"]), d["name"])):
        key = (deck["code"], frozenset(
            (c["name"], c["count"]) for c in deck_cards(deck)
            if "Basic" not in c.get("supertypes", [])))
        seen.setdefault(key, deck)
    return sorted(seen.values(), key=lambda d: (d["releaseDate"], d["code"], d["name"]))


def select_decks(decks: list[dict], include_unreleased: bool) -> list[dict]:
    today = date.today().isoformat()
    chosen = [d for d in decks
              if d["code"] not in EXCLUDED_SET_CODES
              and (include_unreleased or d["releaseDate"] <= today)]
    return dedupe_decks(chosen)


def build_commanders(decks: list[dict], cards: dict[str, dict],
                     sets: dict[str, dict]) -> tuple[dict[str, dict], dict[str, dict]]:
    """One record per unique eligible card, tracking the sets and decks it appears in.

    Eligibility is membership in `cards`, i.e. Scryfall's `is:commander`. Anything
    legendary in a precon that fails that test is returned separately so the
    exclusion can be shown rather than silently dropped.
    """
    commanders: dict[str, dict] = {}
    rejected: dict[str, dict] = {}
    for deck in decks:
        code = deck["code"]
        set_name = sets.get(code.lower(), {}).get("name", code)
        for entry in deck_cards(deck):
            oracle_id = oracle_id_of(entry)
            if oracle_id is None:
                continue
            card = cards.get(oracle_id)
            if card is None:
                if "Legendary" in entry.get("supertypes", []):
                    note = rejected.setdefault(oracle_id, {
                        "name": entry["name"],
                        "type_line": entry.get("type", ""),
                        "reason": "Not a legal commander (Scryfall is:commander)",
                        "sets": {},
                    })
                    note["sets"][code] = set_name
                continue
            traits = partner_traits(card)
            solo = can_be_sole_commander(card)
            record = commanders.get(oracle_id)
            if record is None:
                identity = color_key(card["color_identity"])
                record = commanders[oracle_id] = {
                    "oracle_id": oracle_id,
                    "name": card["name"],
                    "card": card,
                    "traits": traits,
                    "solo": solo,
                    "color_identity": identity,
                    "colors_count": len(identity),
                    "type_line": type_line(card),
                    "mana_cost": card.get("mana_cost") or "",
                    "cmc": card.get("cmc"),
                    "scryfall_uri": card["scryfall_uri"].split("?")[0],
                    "sets": {},
                    "decks": {},
                }
            record["sets"][code] = set_name
            record["decks"].setdefault(code, set()).add(deck["name"])
    return commanders, rejected


def build_heads(commanders: dict[str, dict]) -> tuple[dict, list[dict]]:
    """Build every legal commander configuration, per precon set.

    A head is one commander, or two cards forming a legal partner pair. Both
    cards of a pair must appear in the same precon set.
    """
    by_set: dict[str, list[dict]] = {}
    for record in commanders.values():
        for code in record["sets"]:
            by_set.setdefault(code, []).append(record)

    heads: dict[tuple, dict] = {}
    units: list[dict] = []
    for code, members in by_set.items():
        for record in members:
            if not record["solo"]:
                continue
            key = (record["oracle_id"],)
            head = heads.setdefault(key, {
                "cards": [record], "mode": "Single", "mechanic": "",
                "color_identity": record["color_identity"], "sets": {},
            })
            head["sets"][code] = record["sets"][code]

        for a, b in itertools.combinations(sorted(members, key=lambda r: r["name"]), 2):
            reason = partner_reason(a, b)
            if reason is None:
                continue
            first, second = (a, b) if a["name"] <= b["name"] else (b, a)
            key = tuple(sorted((a["oracle_id"], b["oracle_id"])))
            head = heads.get(key)
            if head is None:
                combined = color_key(first["color_identity"] + second["color_identity"])
                head = heads[key] = {
                    "cards": [first, second], "mode": "Partner", "mechanic": reason,
                    "color_identity": combined, "sets": {},
                }
                units.append(head)
            head["sets"][code] = a["sets"][code]

    for head in heads.values():
        head["label"] = " + ".join(c["name"] for c in head["cards"])
        head["colors"] = head["color_identity"] or "C"
        head["identity_name"] = identity_name(head["color_identity"])
    return heads, units


def build_partner_legal(commanders: dict[str, dict]) -> dict[tuple[str, str], str]:
    """Pairs that legally partner under Commander rules, IGNORING the set rule.

    Used only to tell the two failure modes apart on the Team Builder page: cards
    that legally partner but never share a precon set, versus cards that simply
    cannot be commanders together.
    """
    records = sorted(commanders.values(), key=lambda r: r["name"])
    legal: dict[tuple[str, str], str] = {}
    for a, b in itertools.combinations(records, 2):
        reason = partner_reason(a, b)
        if reason:
            legal[tuple(sorted((a["name"], b["name"])))] = reason
    return legal


def build_teams(heads: dict) -> list[dict]:
    """Every legal two-seat team: both seats in one precon set, colors disjoint.

    Two colourless seats are rejected: the tournament treats colourlessness as a
    distinct identity that the two seats would then share, rather than as an
    empty set that trivially fails to intersect.
    """
    by_set: dict[str, list[dict]] = {}
    for head in heads.values():
        for code in head["sets"]:
            by_set.setdefault(code, []).append(head)

    teams: dict[tuple, dict] = {}
    for code, members in by_set.items():
        for a, b in itertools.combinations(sorted(members, key=lambda h: h["label"]), 2):
            if set(a["color_identity"]) & set(b["color_identity"]):
                continue
            # Colourlessness is an identity in its own right, not the absence of
            # one, so two colourless seats share it and cannot team up.
            if not a["color_identity"] and not b["color_identity"]:
                continue
            # Teammates cannot bring the same card as a commander.
            if {c["oracle_id"] for c in a["cards"]} & {c["oracle_id"] for c in b["cards"]}:
                continue
            key = tuple(sorted((a["label"], b["label"])))
            entry = teams.get(key)
            if entry is None:
                first, second = (a, b) if a["label"] <= b["label"] else (b, a)
                combined = color_key(first["color_identity"] + second["color_identity"])
                entry = teams[key] = {
                    "a": first, "b": second,
                    "combined_colors": combined or "C",
                    "combined_identity": identity_name(combined),
                    "combined_colors_count": len(combined),
                    "sets": {},
                }
            entry["sets"][code] = a["sets"][code]
    return list(teams.values())
