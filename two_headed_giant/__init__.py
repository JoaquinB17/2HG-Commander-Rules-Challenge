"""Legal Two-Headed Giant Commander teams.

Two-Headed Giant is a TEAM format: you and your partner sit on the same side.
The tournament rule constrains that team, not anything about the opposing table.

Tournament rule being modelled:
  * Your commander and your partner's commander must both appear in a
    preconstructed Commander deck from the same set (original printing or reprint).
  * The two commanders must not overlap in color identity.

Either teammate may field a legal partner pair, so each seat is one or two cards.
Every commander card on the team -- two to four cards -- must appear in one shared
precon set.

Eligibility comes from actual precon DECKLISTS (MTGJSON), not from set membership.
A card only counts if it is physically in one of the 100-card decks, which keeps
out Special Guests, booster/collector exclusives and Jumpstart cards that share a
Commander set code but were never in a precon.

WHAT COUNTS AS A COMMANDER is delegated entirely to Scryfall's `is:commander`
filter rather than tested locally. A local rule ("legendary creature, or says it
can be your commander") goes stale the moment the rules change: legendary Vehicles
and Spacecraft are commanders now and carry no such text, and Grist, the Hunger
Tide is a creature card everywhere except the battlefield. Scryfall tracks those
changes; a hand-rolled test cannot.

Card facts (color identity, type, oracle text) come from the same Scryfall fetch,
keyed by oracle id. Responses are cached under ./data so re-runs are offline.
"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = PROJECT_ROOT / "data"
DEFAULT_OUTPUT = PROJECT_ROOT / "output" / "two_headed_giant_teams.xlsx"

__all__ = ["PROJECT_ROOT", "CACHE_DIR", "DEFAULT_OUTPUT"]
