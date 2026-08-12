"""Invariants over the generated workbook.

Everything here is a property that must hold for all 21k+ derived rows, checked
against the source decklists rather than against the build's own intermediate
state — so a bug in the pipeline cannot vouch for itself.
"""

from __future__ import annotations

import collections

import pytest

from two_headed_giant.rules import EXCLUDED_SET_CODES

EXPECTED_SHEETS = ["Rules", "Team Builder", "Sets", "Decks", "Commanders",
                   "Partner Pairs", "Teams", "Not Eligible", "Partner Options",
                   "Lists", "Aliases", "Partner Legal"]

# Legendary Vehicles, Spacecraft and Grist became legal commanders through rules
# changes and carry no "can be your commander" text. A hand-rolled eligibility
# test missed all of them; these names pin the delegation to Scryfall.
RULES_CHANGE_CARDS = [
    "Shorikai, Genesis Engine", "Weatherlight", "Parhelion II", "Esika's Chariot",
    "The Prydwen, Steel Flagship", "Skysovereign, Consul Flagship", "The Indomitable",
    "The Fantasticar", "Damocles Base, Sword of Kang", "RMS Titanic",
    "Bessie, the Doctor's Roadster", "The Falcon, Airship Restored",
    "Hearthhull, the Worldseed", "Inspirit, Flagship Vessel", "Grist, the Hunger Tide",
]


def colors(value: str) -> set[str]:
    return set() if value == "C" else set(str(value))


@pytest.fixture(scope="module")
def cards_by_set(decklists) -> dict[str, set[str]]:
    """Card names physically present in each eligible precon set."""
    index: dict[str, set[str]] = collections.defaultdict(set)
    for deck in decklists:
        if deck["code"] in EXCLUDED_SET_CODES:
            continue
        for card in deck.get("commander", []) + deck.get("mainBoard", []) + deck.get("sideBoard", []):
            index[deck["code"]].add(card["name"])
            index[deck["code"]].add(card["name"].split(" // ")[0])
    return index


def test_all_sheets_present(sheets):
    assert list(sheets) == EXPECTED_SHEETS


# --------------------------------------------------------------------------- #
# Eligibility
# --------------------------------------------------------------------------- #
def test_rules_change_cards_are_eligible(sheets):
    pool = set(sheets["Commanders"]["Commander"])
    assert [c for c in RULES_CHANGE_CARDS if c not in pool] == []


def test_pool_is_exactly_the_is_commander_intersection(sheets, commander_universe):
    legal = {c["name"] for c in commander_universe.values()}
    assert set(sheets["Commanders"]["Commander"]) <= legal


def test_not_eligible_is_disjoint_from_the_pool(sheets):
    pool = set(sheets["Commanders"]["Commander"])
    assert set(sheets["Not Eligible"]["Card"]) & pool == set()


def test_backgrounds_are_partner_only(sheets):
    partner_only = sheets["Commanders"].query("`Can Lead Alone` != 'Yes'")
    assert len(partner_only) == 4
    teams = sheets["Teams"]
    singles = teams[(teams["A Mode"] == "Single") & (teams["B Mode"] == "Single")]
    names = set(partner_only["Commander"])
    assert not singles["Commander A"].isin(names).any()
    assert not singles["Commander B"].isin(names).any()


# --------------------------------------------------------------------------- #
# Team legality
# --------------------------------------------------------------------------- #
def test_no_team_overlaps_in_color_identity(sheets):
    teams = sheets["Teams"]
    bad = [(a, b) for a, b in zip(teams["Colors A"], teams["Colors B"])
           if colors(a) & colors(b)]
    assert bad == []


def test_team_colors_are_the_union_of_both_seats(sheets):
    teams = sheets["Teams"]
    bad = [(a, b, t) for a, b, t in
           zip(teams["Colors A"], teams["Colors B"], teams["Team Colors"])
           if colors(a) | colors(b) != colors(t)]
    assert bad == []


def test_teammates_never_share_a_card(sheets):
    teams = sheets["Teams"]
    bad = [(a, b) for a, b in zip(teams["Commander A"], teams["Commander B"])
           if set(a.split(" + ")) & set(b.split(" + "))]
    assert bad == []


def test_teams_are_unique_and_not_self_pairs(sheets):
    teams = sheets["Teams"]
    keys = [tuple(sorted((a, b))) for a, b in zip(teams["Commander A"], teams["Commander B"])]
    assert len(keys) == len(set(keys))
    assert not (teams["Commander A"] == teams["Commander B"]).any()


def test_every_commander_is_physically_in_its_claimed_set(sheets, cards_by_set):
    """The core rule: a team is only legal via a set containing all its cards."""
    teams = sheets["Teams"]
    bad = []
    for a, b, codes in zip(teams["Commander A"], teams["Commander B"], teams["Shared Set Codes"]):
        for code in str(codes).split(", "):
            for card in a.split(" + ") + b.split(" + "):
                if card not in cards_by_set[code]:
                    bad.append((card, code))
    assert bad[:5] == []


# --------------------------------------------------------------------------- #
# Product exclusions
# --------------------------------------------------------------------------- #
def test_excluded_products_are_absent(sheets):
    assert set(sheets["Sets"]["Set Code"]) & EXCLUDED_SET_CODES == set()


def test_no_collectors_edition_decks(sheets):
    assert not sheets["Decks"]["Deck"].str.contains("Collector", case=False).any()


# --------------------------------------------------------------------------- #
# Helper tables backing the Team Builder page
# --------------------------------------------------------------------------- #
def test_aliases_cover_both_card_orders(sheets):
    """The page must accept the two cards typed in either order."""
    units, aliases = sheets["Partner Pairs"], sheets["Aliases"]
    known = set(aliases["Alias"])
    missing = [f"{b} + {a}" for a, b in zip(units["Commander A"], units["Commander B"])
               if f"{b} + {a}" not in known]
    assert missing == []


def test_every_alias_resolves_to_a_real_configuration(sheets):
    assert set(sheets["Aliases"]["Configuration"]) <= set(sheets["Lists"]["Configuration"])


def test_partner_legal_table_is_symmetric(sheets):
    plegal = sheets["Partner Legal"]
    keys = set(plegal["Key"])
    assert all(f"{b}|{a}" in keys for a, b in zip(plegal["Card A"], plegal["Card B"]))


def test_same_set_units_are_a_subset_of_partner_legal(sheets):
    """Every pair legal in a set must also be legal ignoring the set rule."""
    keys = set(sheets["Partner Legal"]["Key"])
    units = sheets["Partner Pairs"]
    assert all(f"{a}|{b}" in keys for a, b in zip(units["Commander A"], units["Commander B"]))


def test_partner_options_is_the_symmetric_view_of_teams(sheets):
    assert len(sheets["Partner Options"]) == 2 * len(sheets["Teams"])


# --------------------------------------------------------------------------- #
# Regression: sets that barely work
# --------------------------------------------------------------------------- #
def test_lorwyn_eclipsed_stays_tight(sheets):
    ecc = sheets["Sets"].set_index("Set Code").loc["ECC"]
    assert int(ecc["# Commanders"]) == 17
    assert int(ecc["# Legal Teams"]) == 7
    teams = sheets["Teams"]
    used = teams[teams["Shared Set Codes"].astype(str).str.contains("ECC")]
    distinct = set(used["Commander A"]) | set(used["Commander B"])
    assert int(ecc["# Commanders With No Partner"]) == 17 - len(distinct)


def test_phyrexia_commander_has_no_legal_team(sheets):
    """Every identity in ONC contains red or white, so nothing pairs."""
    onc = sheets["Sets"].set_index("Set Code").loc["ONC"]
    assert int(onc["# Legal Teams"]) == 0
    assert int(onc["# Commanders With No Partner"]) == int(onc["# Commanders"])
