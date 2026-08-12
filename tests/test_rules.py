"""Unit tests for the rules layer. No network, no workbook, no fixtures.

These pin the behaviour that is easy to get wrong and expensive to notice: which
cards may legally partner, and which may not.
"""

from __future__ import annotations

import pytest

from two_headed_giant.rules import (build_teams, can_be_sole_commander, color_key,
                                    dedupe_decks, partner_reason, partner_traits)

PARTNER = "Partner (You can have two commanders if both have partner.)"
CHAR_SELECT = "Partner—Character select (You can have two commanders if both have this ability.)"
COMPANION = "Doctor's companion (You can have two commanders if the other is the Doctor.)"


def record(name: str, text: str = "", types: str = "Legendary Creature — Human") -> dict:
    """A commander record shaped the way build_commanders() produces them."""
    card = {"name": name, "oracle_text": text, "type_line": types}
    return {"name": name, "card": card, "traits": partner_traits(card),
            "oracle_id": name, "color_identity": ""}


# --------------------------------------------------------------------------- #
# Partner legality
# --------------------------------------------------------------------------- #
def test_two_plain_partners_may_pair():
    assert partner_reason(record("A", PARTNER), record("B", PARTNER)) == "Partner"


def test_partner_with_matches_only_its_named_card():
    pir = record("Pir", "Partner with Toothy (When this creature enters...)")
    toothy = record("Toothy", "Partner with Pir (When this creature enters...)")
    assert partner_reason(pir, toothy) == "Partner with"


@pytest.mark.parametrize("other_text, label", [
    (PARTNER, "generic Partner"),
    (CHAR_SELECT, "Character select"),
])
def test_partner_with_card_cannot_pair_with_anything_else(other_text, label):
    """Scryfall tags 'partner with' cards with the generic Partner keyword too.

    Trusting that tag would make Pir a legal partner for any Partner card, which
    the rulings explicitly forbid: a creature with 'partner with' can't partner
    with any creature other than its designated partner.
    """
    pir = record("Pir", "Partner with Toothy (When this creature enters...)")
    assert partner_reason(pir, record("Other", other_text)) is None, label


def test_character_select_pairs_only_with_character_select():
    a, b = record("Donatello", CHAR_SELECT), record("Leonardo", CHAR_SELECT)
    assert partner_reason(a, b) == "Partner—Character select"
    assert partner_reason(a, record("Thrasios", PARTNER)) is None


def test_doctors_companion_needs_an_actual_doctor():
    clara = record("Clara", COMPANION)
    doctor = record("The Tenth Doctor", "", "Legendary Creature — Time Lord Doctor")
    assert partner_reason(clara, doctor) == "Doctor's companion"
    assert partner_reason(clara, record("Not A Doctor")) is None
    assert partner_reason(clara, record("Bill Potts", COMPANION)) is None


def test_background_pairs_only_with_choose_a_background():
    creature = record("Baeloth", "Choose a Background (You can have a Background as a second commander.)")
    background = record("Folk Hero", "", "Legendary Enchantment — Background")
    assert partner_reason(creature, background) == "Choose a Background"
    assert partner_reason(record("Plain"), background) is None


def test_unrelated_legends_do_not_partner():
    assert partner_reason(record("A"), record("B")) is None


# --------------------------------------------------------------------------- #
# Eligibility
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("types, expected", [
    ("Legendary Creature — Human Wizard", True),
    ("Legendary Artifact — Vehicle", True),        # legal commander since the rules change
    ("Legendary Artifact — Spacecraft", True),
    ("Legendary Planeswalker — Grist", True),
    ("Legendary Enchantment — Background", False),  # second commander only
])
def test_can_be_sole_commander(types, expected):
    assert can_be_sole_commander({"type_line": types, "name": "x"}) is expected


# --------------------------------------------------------------------------- #
# Colors
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("identity, expected", [
    (["G", "W", "U"], "WUG"),      # normalised to WUBRG order
    (["R"], "R"),
    ([], ""),
    (["B", "R", "G", "U", "W"], "WUBRG"),
])
def test_color_key_normalises_to_wubrg_order(identity, expected):
    assert color_key(identity) == expected


# --------------------------------------------------------------------------- #
# Deck selection
# --------------------------------------------------------------------------- #
def deck(name: str, code: str, cards: list[tuple[str, int, bool]]) -> dict:
    return {"name": name, "code": code, "releaseDate": "2024-01-01",
            "commander": [], "sideBoard": [],
            "mainBoard": [{"name": n, "count": c,
                           "supertypes": ["Basic"] if basic else []} for n, c, basic in cards]}


def test_collectors_edition_collapses_despite_missing_basics():
    """MTGJSON records some Collector's Editions a few basic lands short.

    That is not a real decklist difference, so the base deck must win and the
    twin must disappear.
    """
    base = deck("Counter Blitz", "FIC", [("Cloud", 1, False), ("Forest", 8, True)])
    collector = deck("Counter Blitz Collector's Edition", "FIC",
                     [("Cloud", 1, False), ("Forest", 2, True)])
    kept = dedupe_decks([base, collector])
    assert [d["name"] for d in kept] == ["Counter Blitz"]


def test_genuinely_different_decks_are_kept():
    a = deck("Deck A", "XYZ", [("Cloud", 1, False)])
    b = deck("Deck B", "XYZ", [("Tifa", 1, False)])
    assert len(dedupe_decks([a, b])) == 2


# --------------------------------------------------------------------------- #
# Team building
# --------------------------------------------------------------------------- #
def head(label: str, colors: str, oracle_ids: tuple[str, ...], code: str = "SET") -> dict:
    return {"label": label, "color_identity": colors, "mode": "Single", "mechanic": "",
            "cards": [{"oracle_id": o} for o in oracle_ids], "sets": {code: "A Set"}}


def test_teams_require_disjoint_colors_and_a_shared_set():
    heads = {
        ("a",): head("Azorius Legend", "WU", ("a",)),
        ("b",): head("Golgari Legend", "BG", ("b",)),
        ("c",): head("Boros Legend", "WR", ("c",)),
        ("d",): head("Elsewhere", "BG", ("d",), code="OTHER"),
    }
    labels = {tuple(sorted((t["a"]["label"], t["b"]["label"]))) for t in build_teams(heads)}
    assert ("Azorius Legend", "Golgari Legend") in labels   # WU + BG, same set
    assert ("Boros Legend", "Golgari Legend") in labels     # WR + BG, same set
    assert ("Azorius Legend", "Boros Legend") not in labels  # both contain W
    assert ("Azorius Legend", "Elsewhere") not in labels     # no shared set


def test_colorless_teams_with_any_coloured_seat():
    heads = {("a",): head("Colorless", "", ("a",)),
             ("b",): head("Five Color", "WUBRG", ("b",))}
    assert len(build_teams(heads)) == 1


def test_two_colorless_seats_cannot_team():
    """Colourlessness is its own identity, so two colourless seats share it.

    Set intersection alone would allow this pair, since both identities are
    empty and therefore trivially disjoint.
    """
    heads = {("a",): head("Kozilek", "", ("a",)),
             ("b",): head("Traxos", "", ("b",))}
    assert build_teams(heads) == []


def test_teammates_cannot_share_a_card():
    """A partner pair and a single that reuse one card are not a legal team."""
    heads = {("a", "b"): head("A + B", "W", ("a", "b")),
             ("b",): head("B", "", ("b",))}
    assert build_teams(heads) == []
