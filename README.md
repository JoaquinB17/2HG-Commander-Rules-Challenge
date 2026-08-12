# Two-Headed Giant Commander — team finder

*English · [Español](README.es.md)*

A local Magic: The Gathering tournament ran Two-Headed Giant Commander with a
house rule that turns deckbuilding into a constraint-satisfaction problem:

> You and your teammate may only use commanders **printed in the same
> preconstructed Commander set** (any printing, original or reprint), and your two
> commanders **may not overlap in color identity**.

Nobody could answer "what can my partner play?" without manually cross-referencing
decklists. This reconciles two card APIs, derives every legal team, and ships the
answer as an Excel workbook with an interactive lookup page.

**Result: 21,699 legal teams** from 1,055 eligible cards across 44 precon sets.

![The Team Builder page in Excel: two yellow input cells hold a commander and its
partner, a status line reads "OK — legal partner pair (Doctor's companion). 15 choices
for your partner", and the table below lists each legal partner with its colors, the
resulting team identity, the shared precon set and which deck to find it in.](docs/team-builder.png)

📄 **Read the case study** —
[English](https://joaquinb17.github.io/2HG-Commander-Rules-Challenge/case-study.html) ·
[Español](https://joaquinb17.github.io/2HG-Commander-Rules-Challenge/case-study.es.html) —
the problem, the three decisions that changed the answer, and how a spreadsheet
gets tested.

```bash
pip install -e ".[dev]"
python -m two_headed_giant
```

Writes `output/two_headed_giant_teams.xlsx`. API responses are cached under
`data/`, so re-runs are offline and take a few seconds.

| Flag | Effect |
| --- | --- |
| `--refresh` | Re-download from MTGJSON and Scryfall |
| `--include-unreleased` | Include decks not yet released |
| `--singles-only` | Ignore partner mechanics; one commander per seat |
| `--out PATH` | Write elsewhere |

## Architecture

```
two_headed_giant/
├── sources.py    fetch + cache MTGJSON decklists and the Scryfall is:commander universe
├── rules.py      eligibility, partner mechanics, commander configurations, legal teams
├── workbook.py   Excel output, including the interactive Team Builder page
└── cli.py        wires the pipeline together
tests/
├── test_rules.py               23 unit tests, no network or workbook needed
├── test_workbook.py            invariants over the 21,699 generated rows
└── test_team_builder_excel.py  drives a real Excel instance via COM
```

The pipeline is: decklists ∩ commander-legal cards → per-set commander pool →
commander configurations (a "seat" is one card, or two that legally partner) →
every disjoint-color pair sharing a set.

## Three decisions worth explaining

### 1. Decklists, not set membership

The obvious approach — "every commander-legal card whose Scryfall set is a
Commander set" — is wrong, and quietly so. Commander set codes also cover Special
Guests, booster/collector exclusives and Jumpstart cards that were never in any
precon. That inflated Marvel Super Heroes Commander from its real 88 eligible
commanders to 251.

Eligibility therefore comes from **actual MTGJSON decklists**: a card counts only if
it is physically one of the 100 cards in a deck. This also correctly *includes*
cards whose printing carries the parent expansion's set code, like IKO-coded cards
inside a C20 deck.

### 2. Delegate the rules, don't reimplement them

Eligibility was originally a local test: *legendary creature, or text says "can be
your commander"*. That is the kind of rule that looks right and rots silently.
Rules changes made legendary **Vehicles** and **Spacecraft** legal commanders — and
they carry no such text, so no wording test can ever find them.

Eligibility is now delegated to Scryfall's `is:commander` filter. Switching added 15
cards and removed none:

| Added | Count | Examples |
| --- | --- | --- |
| Legendary Artifact — Vehicle | 12 | Shorikai, Weatherlight, Parhelion II, Esika's Chariot |
| Legendary Artifact — Spacecraft | 2 | Hearthhull the Worldseed, Inspirit Flagship Vessel |
| Legendary Planeswalker | 1 | Grist, the Hunger Tide |

Grist is the tell that the local rule was unsound on its own terms, independent of
any rules change: it is a creature card everywhere except the battlefield, has
always been a legal commander, and the wording test silently dropped it.

**Backgrounds** are the one case still needing local handling — they match
`is:commander` but can only ever be a *second* commander.

### 3. Partner mechanics come from oracle text, not `keywords`

Scryfall's `keywords` field reports a plain `Partner` for cards that actually have a
*restricted* variant. Every `Partner with [name]` card is tagged `Partner`, and so is
`Partner—Character select`. Building on that field would make Pir a legal partner for
Thrasios, which the rulings explicitly forbid:

> a creature with a "partner with" ability can't partner with any creature other
> than its designated partner

So mechanics are parsed from oracle text instead, and `test_rules.py` pins each
illegal combination directly.

| Mechanic | Pairs with | Units found |
| --- | --- | --- |
| `Partner` | any other plain-Partner card | 116 |
| `Partner with [name]` | **only** its named card | 14 |
| `Partner—Character select` | only other Character select cards | 15 |
| `Doctor's companion` | any legendary Time Lord Doctor | 390 |
| `Choose a Background` | any Background | 16 |

## The workbook

**Team Builder** is the page it opens on. Enter your commander (and a second card if
you are running a partner pair) and it lists every commander your partner may
legally bring, with the shared set and which deck to find it in. A status line
separates *legal*, *legally partners but never co-printed*, and *cannot partner at
all* — three different problems that all look identical as an empty result.

Other sheets: `Rules`, `Sets`, `Decks`, `Commanders`, `Partner Pairs`, `Teams`, and
`Not Eligible` (legendary cards in precons that are *not* legal commanders, with the
reason, so exclusions are auditable rather than invisible).

**Formulas are restricted to `INDEX`/`MATCH`.** `FILTER`, `XLOOKUP` and `SORT` are
"future functions" that must be written as `_xlfn._xlws.FILTER` when a file is
generated outside Excel, and render as `#NAME?` if the prefix is wrong. Avoiding
them also keeps the workbook working in older Excel and in Google Sheets, where it
has been verified.

Lookups are also cheap by construction: the partner list resolves its block position
with **one** `MATCH`, then reads 469 rows by offset. A per-row `MATCH` would rescan a
43,000-row table on every keystroke.

## Testing

```bash
pytest
```

On a fresh clone this reports **23 passed, 32 skipped**, which is the intended result.
Only the unit layer is self-contained; the other two skip themselves cleanly until
their prerequisites exist:

| Layer | Needs |
| --- | --- |
| `test_rules.py` | nothing — runs anywhere in 0.1s |
| `test_workbook.py` | a built workbook (`python -m two_headed_giant`) |
| `test_team_builder_excel.py` | the workbook, plus Windows with Excel and pywin32 |

55 tests in three layers:

- **`test_rules.py`** — pure functions, no I/O, 0.1s. Pins the partner-legality
  matrix, including the combinations that must *not* be legal.
- **`test_workbook.py`** — invariants over all 21,699 generated teams, validated
  against the source decklists rather than the build's own intermediate state, so a
  bug cannot vouch for itself.
- **`test_team_builder_excel.py`** — opens the workbook in a real Excel instance via
  COM, types into the input cells, forces recalculation and compares what Excel
  computes against what the data says. openpyxl writes formulas but never evaluates
  them, so an off-by-one in an `INDEX` offset would otherwise ship silently. Skips
  cleanly without Windows/Excel.

## Findings

Some sets barely function under the house rule:

| Set | Commanders | With no legal partner | Legal teams |
| --- | --- | --- | --- |
| Phyrexia: All Will Be One (`ONC`) | 7 | **7** | **0** |
| Lorwyn Eclipsed (`ECC`) | 17 | 10 | 7 |
| Modern Horizons 3 (`M3C`) | 19 | 6 | 34 |

`ONC` has no legal team at all — every color identity in it contains red or white.
Lorwyn Eclipsed has 17 commanders but only 7 teams: four are five-color and the set
has no colorless commander, so those four have zero options. The `Sets` sheet
surfaces this per set, which is worth checking before committing to one.

## Data sources

- [MTGJSON](https://mtgjson.com) — precon decklists
- [Scryfall](https://scryfall.com) — the `is:commander` universe and all card data

Both are polled with a delay between requests, per their published guidelines.
