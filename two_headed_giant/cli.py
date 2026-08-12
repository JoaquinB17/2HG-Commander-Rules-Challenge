"""Command-line entry point: build the workbook end to end."""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

import pandas as pd

from . import DEFAULT_OUTPUT
from . import __doc__ as package_doc
from .rules import (build_commanders, build_heads, build_partner_legal, build_teams,
                    identity_name, select_decks)
from .sources import load_data
from .workbook import write_workbook


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m two_headed_giant",
                                     description=package_doc,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--refresh", action="store_true", help="re-download source data")
    parser.add_argument("--include-unreleased", action="store_true",
                        help="include decks that have not been released yet")
    parser.add_argument("--singles-only", action="store_true",
                        help="ignore partner mechanics; one commander per seat")
    parser.add_argument("--out", type=Path,
                        default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    decks_raw, sets, cards = load_data(args.refresh)
    decks = select_decks(decks_raw, args.include_unreleased)
    print(f"{len(decks)} unique precon decklists "
          f"(from {len(decks_raw)} MTGJSON entries, duplicates and excluded products removed)")

    commanders, rejected = build_commanders(decks, cards, sets)
    codes = sorted({code for r in commanders.values() for code in r["sets"]})
    solo_count = sum(1 for r in commanders.values() if r["solo"])
    print(f"{len(cards)} commander-legal cards known to Scryfall; "
          f"{len(commanders)} of them appear in precon decks")
    print(f"{solo_count} can lead alone (+{len(commanders) - solo_count} partner-only cards) "
          f"across {len(codes)} precon sets")

    heads, units = build_heads(commanders)
    if args.singles_only:
        heads = {k: h for k, h in heads.items() if h["mode"] == "Single"}
        units = []
    print(f"{len(heads)} commander configurations ({len(units)} partner pairs)")

    teams = build_teams(heads)
    both_single = sum(1 for t in teams if t["a"]["mode"] == "Single" and t["b"]["mode"] == "Single")
    print(f"{len(teams)} legal teams ({both_single} with a single commander each, "
          f"{len(teams) - both_single} involving a partner pair)")

    def decks_for(head, shared_codes):
        names = {n for card in head["cards"]
                 for code in shared_codes for n in card["decks"].get(code, ())}
        return ", ".join(sorted(names))

    def mechanic_of(record):
        t = record["traits"]
        bits = []
        if t["partner"] and not t["restricted"] and not t["partner_with"]:
            bits.append("Partner")
        bits += [f"Partner with {n}" for n in t["partner_with"]]
        bits += [f"Partner—{n}" for n in t["restricted"]]
        if t["companion"]:
            bits.append("Doctor's companion")
        if t["doctor"]:
            bits.append("Time Lord Doctor")
        if t["choose_background"]:
            bits.append("Choose a Background")
        if t["background"]:
            bits.append("Background")
        return ", ".join(dict.fromkeys(bits))

    commanders_df = pd.DataFrame([
        {
            "Commander": r["name"],
            "Colors": r["color_identity"] or "C",
            "Color Identity": identity_name(r["color_identity"]),
            "# Colors": r["colors_count"],
            "Can Lead Alone": "Yes" if r["solo"] else "No (partner only)",
            "Partner Mechanic": mechanic_of(r),
            "Type": r["type_line"],
            "Mana Cost": r["mana_cost"],
            "MV": r["cmc"],
            "# Precon Sets": len(r["sets"]),
            "Precon Set Codes": ", ".join(sorted(r["sets"])),
            "Precon Sets": ", ".join(sorted(set(r["sets"].values()))),
            "Precon Decks": ", ".join(sorted({n for v in r["decks"].values() for n in v})),
            "Scryfall": r["scryfall_uri"],
        }
        for r in commanders.values()
    ]).sort_values("Commander", ignore_index=True)

    units_df = pd.DataFrame([
        {
            "Commander A": u["cards"][0]["name"],
            "Commander B": u["cards"][1]["name"],
            "Mechanic": u["mechanic"],
            "Colors": u["colors"],
            "Color Identity": u["identity_name"],
            "# Colors": len(u["color_identity"]),
            "# Precon Sets": len(u["sets"]),
            "Precon Set Codes": ", ".join(sorted(u["sets"])),
            "Precon Sets": ", ".join(sorted(set(u["sets"].values()))),
            "Scryfall A": u["cards"][0]["scryfall_uri"],
            "Scryfall B": u["cards"][1]["scryfall_uri"],
        }
        for u in units
    ]).sort_values(["Mechanic", "Commander A", "Commander B"], ignore_index=True)

    teams_df = pd.DataFrame([
        {
            "Commander A": t["a"]["label"],
            "A Mode": t["a"]["mode"],
            "A Mechanic": t["a"]["mechanic"],
            "Colors A": t["a"]["colors"],
            "Identity A": t["a"]["identity_name"],
            "Commander B": t["b"]["label"],
            "B Mode": t["b"]["mode"],
            "B Mechanic": t["b"]["mechanic"],
            "Colors B": t["b"]["colors"],
            "Identity B": t["b"]["identity_name"],
            "Team Colors": t["combined_colors"],
            "Team Identity": t["combined_identity"],
            "# Team Colors": t["combined_colors_count"],
            "# Shared Sets": len(t["sets"]),
            "Shared Set Codes": ", ".join(sorted(t["sets"])),
            "Shared Sets": ", ".join(sorted(set(t["sets"].values()))),
            "Decks with A": decks_for(t["a"], t["sets"]),
            "Decks with B": decks_for(t["b"], t["sets"]),
        }
        for t in teams
    ]).sort_values(["# Team Colors", "Commander A", "Commander B"],
                   ascending=[False, True, True], ignore_index=True)

    per_set = {code: {"teams": 0, "units": 0, "commanders": 0, "decks": 0} for code in codes}
    for t in teams:
        for code in t["sets"]:
            per_set[code]["teams"] += 1
    for u in units:
        for code in u["sets"]:
            per_set[code]["units"] += 1
    for r in commanders.values():
        if r["solo"]:
            for code in r["sets"]:
                per_set[code]["commanders"] += 1
    for deck in decks:
        if deck["code"] in per_set:
            per_set[deck["code"]]["decks"] += 1

    # A commander is stranded in a set if nothing else there avoids its colors.
    partnered = {code: set() for code in codes}
    for t in teams:
        for code in t["sets"]:
            partnered[code].update((t["a"]["label"], t["b"]["label"]))
    stranded = {code: 0 for code in codes}
    for r in commanders.values():
        if not r["solo"]:
            continue
        for code in r["sets"]:
            if r["name"] not in partnered[code]:
                stranded[code] += 1

    sets_df = pd.DataFrame([
        {
            "Set Code": code,
            "Set": sets.get(code.lower(), {}).get("name", code),
            "Released": sets.get(code.lower(), {}).get("released_at", ""),
            "# Decks": per_set[code]["decks"],
            "# Commanders": per_set[code]["commanders"],
            "# Commanders With No Partner": stranded[code],
            "# Partner Pairs": per_set[code]["units"],
            "# Legal Teams": per_set[code]["teams"],
        }
        for code in codes
    ]).sort_values("Released", ascending=False, ignore_index=True)

    in_deck: dict[tuple[str, str], int] = {}
    for r in commanders.values():
        for code, names in r["decks"].items():
            for name in names:
                in_deck[(code, name)] = in_deck.get((code, name), 0) + 1

    decks_df = pd.DataFrame([
        {
            "Set Code": d["code"],
            "Set": sets.get(d["code"].lower(), {}).get("name", d["code"]),
            "Deck": d["name"],
            "Released": d["releaseDate"],
            "Face Commander(s)": ", ".join(c["name"] for c in d.get("commander", [])),
            "# Eligible Cards in Deck": in_deck.get((d["code"], d["name"]), 0),
        }
        for d in decks
    ]).sort_values(["Released", "Set Code", "Deck"], ascending=[False, True, True],
                   ignore_index=True)

    mech_counts = {}
    for u in units:
        mech_counts[u["mechanic"]] = mech_counts.get(u["mechanic"], 0) + 1

    rules_df = pd.DataFrame([
        ("Format",
         "Two-Headed Giant Commander. You and your partner are TEAMMATES on the same side; the "
         "rules below constrain your own team and say nothing about the opposing table."),
        ("Team rule",
         "Your commander and your partner's commander must both appear in a preconstructed "
         "Commander deck from the SAME set. Original printing or reprint both count."),
        ("Color rule",
         "Your color identity and your partner's must not overlap. For a partner pair, the "
         "identity is the union of both cards."),
        ("Partner pairs",
         "Either teammate may field two commanders if the cards legally partner. Both halves "
         "must also be in that same precon set, so a team can involve up to four cards from "
         "one set."),
        ("Same card twice",
         "Teammates cannot both bring the same card as a commander."),
        ("Partner mechanics supported",
         "; ".join(f"{k} ({v})" for k, v in sorted(mech_counts.items())) or "none"),
        ("Partner with",
         "Restricted to its named card. Per Scryfall rulings, a creature with 'partner with' "
         "cannot partner with anything other than its designated partner, even though Scryfall "
         "also tags those cards with the generic 'Partner' keyword."),
        ("Partner—Character select",
         "A restricted variant: pairs only with other cards having the same named variant, not "
         "with generic Partner cards."),
        ("Doctor's companion", "Pairs with any legendary Time Lord Doctor in the same set."),
        ("Choose a Background",
         "Pairs with any Background in the same set. A Background can never lead a deck alone, "
         "so it is marked 'partner only' on the Commanders sheet."),
        ("Which cards are eligible",
         "Whatever Scryfall's 'is:commander' filter accepts. This is deliberately NOT a local "
         "rule: recent rules changes made legendary Vehicles and Spacecraft/Station cards legal "
         "commanders, and they carry no 'can be your commander' text, so no wording test could "
         "find them. Delegating to Scryfall means this tracks future rules changes too."),
        ("Vehicles and Stations",
         "Included. Every legendary Vehicle and Spacecraft in these precons is a legal commander "
         "(Shorikai, Weatherlight, Parhelion II, Esika's Chariot, The Prydwen, Hearthhull, "
         "Inspirit and the rest). Grist, the Hunger Tide is in for the same reason: it is a "
         "creature card everywhere except the battlefield."),
        ("Which printings count",
         "Actual precon decklists from MTGJSON. A card only counts if it is physically in one "
         "of the 100 cards. Special Guests, booster-exclusive cards and Jumpstart cards that "
         "share a Commander set code but were never in a precon are NOT eligible."),
        ("Excluded products",
         "Secret Lair Commander decks (7 unrelated drops sharing the SLD code) and Commander "
         "Anthology I & II (CMA, CM2)."),
        ("Duplicate decklists",
         "Collector's Edition printings are collapsed into the base deck: they are the same "
         "decklist in premium treatments, so they add no commanders."),
        ("Colorless commanders",
         "A colorless commander can team with any COLORED configuration in its set, but not "
         "with another colorless one. The tournament treats colorlessness as an identity in "
         "its own right, which two colorless seats would then share."),
        ("Precon sets", len(codes)),
        ("Unique decklists", len(decks)),
        ("Commanders", solo_count),
        ("Partner-only cards (Backgrounds)", len(commanders) - solo_count),
        ("Legal partner pairs", len(units)),
        ("Commander configurations", len(heads)),
        ("Legal teams", len(teams)),
        ("Data sources",
         "MTGJSON (decklists) - https://mtgjson.com | Scryfall (card data) - https://scryfall.com"),
        ("Generated", date.today().isoformat()),
    ], columns=["Item", "Detail"])

    # Directed view of every team, so the finder can look up one commander and
    # read its legal partners off contiguous rows.
    option_rows = []
    for t in teams:
        shared_codes = ", ".join(sorted(t["sets"]))
        shared_names = ", ".join(sorted(set(t["sets"].values())))
        for you, partner in ((t["a"], t["b"]), (t["b"], t["a"])):
            option_rows.append({
                "You": you["label"],
                "Partner": partner["label"],
                "Partner Mode": partner["mode"],
                "Partner Mechanic": partner["mechanic"],
                "Partner Colors": partner["colors"],
                "Partner Identity": partner["identity_name"],
                "Team Colors": t["combined_colors"],
                "Team Identity": t["combined_identity"],
                "# Shared Sets": len(t["sets"]),
                "Shared Set Codes": shared_codes,
                "Shared Sets": shared_names,
                "Decks with Partner": decks_for(partner, t["sets"]),
            })
    options_df = pd.DataFrame(option_rows).sort_values(["You", "Partner"], ignore_index=True)
    options_df.insert(0, "SeqKey",
                      options_df["You"] + "#"
                      + (options_df.groupby("You").cumcount() + 1).astype(str))
    options_df.insert(0, "PairKey", options_df["You"] + "|" + options_df["Partner"])
    capacity = int(options_df.groupby("You").size().max())
    print(f"{len(options_df)} directed partner options; "
          f"most flexible commander has {capacity} partners")

    lists_df = pd.DataFrame([
        {
            "Configuration": h["label"],
            "Mode": h["mode"],
            "Mechanic": h["mechanic"],
            "Colors": h["colors"],
            "Color Identity": h["identity_name"],
            "# Precon Sets": len(h["sets"]),
            "Precon Set Codes": ", ".join(sorted(h["sets"])),
            "Precon Sets": ", ".join(sorted(set(h["sets"].values()))),
        }
        for h in heads.values()
    ]).sort_values("Configuration", ignore_index=True)

    # Both card orders map to the canonical label, so the sheet never depends on
    # Excel's text collation agreeing with Python's ordinal sort.
    alias_rows = []
    for h in heads.values():
        alias_rows.append({"Alias": h["label"], "Configuration": h["label"]})
        if len(h["cards"]) == 2:
            first, second = (c["name"] for c in h["cards"])
            alias_rows.append({"Alias": f"{second} + {first}", "Configuration": h["label"]})
    aliases_df = pd.DataFrame(alias_rows).drop_duplicates("Alias").sort_values(
        "Alias", ignore_index=True)

    partner_legal = build_partner_legal(commanders)
    partner_legal_rows = []
    for (a, b), mechanic in partner_legal.items():
        partner_legal_rows.append({"Key": f"{a}|{b}", "Card A": a, "Card B": b,
                                   "Mechanic": mechanic})
        partner_legal_rows.append({"Key": f"{b}|{a}", "Card A": b, "Card B": a,
                                   "Mechanic": mechanic})
    partner_legal_df = pd.DataFrame(partner_legal_rows).drop_duplicates("Key").sort_values(
        "Key", ignore_index=True)
    same_set_pairs = {tuple(sorted(c["name"] for c in u["cards"])) for u in units}
    print(f"{len(partner_legal)} partner-legal card pairs overall, "
          f"{len(same_set_pairs)} of which share a precon set")

    not_eligible_df = pd.DataFrame([
        {
            "Card": r["name"],
            "Type": r["type_line"],
            "Why Not Eligible": r["reason"],
            "Precon Set Codes": ", ".join(sorted(r["sets"])),
            "Precon Sets": ", ".join(sorted(set(r["sets"].values()))),
        }
        for r in rejected.values()
    ]).sort_values(["Type", "Card"], ignore_index=True)

    frames = {"Rules": rules_df, "Sets": sets_df, "Decks": decks_df,
              "Commanders": commanders_df}
    if len(units_df):
        frames["Partner Pairs"] = units_df
    frames["Teams"] = teams_df
    if len(not_eligible_df):
        frames["Not Eligible"] = not_eligible_df
    frames["Partner Options"] = options_df
    frames["Lists"] = lists_df
    frames["Aliases"] = aliases_df
    frames["Partner Legal"] = partner_legal_df

    write_workbook(args.out, frames, finder={
        "n_options": len(options_df),
        "n_configs": len(lists_df),
        "n_aliases": len(aliases_df),
        "n_partner_legal": len(partner_legal_df),
        "n_commanders": len(commanders_df),
        "capacity": capacity,
    })
    print(f"Wrote {args.out}")
    return 0
