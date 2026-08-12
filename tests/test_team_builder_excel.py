"""End-to-end test of the Team Builder page, driving a real Excel instance.

openpyxl writes formulas but never evaluates them, so an off-by-one in an
INDEX/MATCH offset would ship silently. This opens the workbook in Excel via COM,
types into the input cells, forces a recalculation and compares what Excel
actually computes against what the data says it should be.

Skipped automatically without Windows, pywin32 or Excel.
"""

from __future__ import annotations

import pytest

win32 = pytest.importorskip("win32com.client", reason="pywin32 not installed")

# Cell layout of the Team Builder sheet.
YOU1, YOU2, STATUS, INFO1, INFO2, HEAD, FIRST = 7, 8, 10, 12, 13, 16, 17
GRID_HEAD, GRID_FIRST = 5, 6
EXCEL_ERRORS = {"#N/A", "#NAME?", "#REF!", "#VALUE!", "#DIV/0!", "#NULL!", "#NUM!", "#SPILL!"}


class TeamBuilder:
    """Thin wrapper over the live sheet. COM objects reject added attributes,
    so the helper lives here rather than being bolted onto the sheet."""

    def __init__(self, excel, book):
        self.excel = excel
        self.book = book
        self.sheet = book.Worksheets("Team Builder")

    def pick(self, first: str, second: str = ""):
        self.sheet.Range(f"B{YOU1}").Value = first
        self.sheet.Range(f"B{YOU2}").Value = second
        self.excel.CalculateFullRebuild()
        return self.sheet


@pytest.fixture(scope="module")
def builder(workbook_path):
    """A live Excel sheet, with a helper to set the two pickers and recalculate."""
    try:
        excel = win32.DispatchEx("Excel.Application")
    except Exception as exc:                                  # noqa: BLE001
        pytest.skip(f"Excel not available: {exc}")
    excel.Visible = False
    excel.DisplayAlerts = False
    book = None
    try:
        book = excel.Workbooks.Open(str(workbook_path), ReadOnly=False, UpdateLinks=0)
        yield TeamBuilder(excel, book)
    finally:
        if book is not None:
            book.Close(SaveChanges=False)
        excel.Quit()


@pytest.fixture(scope="module")
def options(sheets):
    return sheets["Partner Options"]


def partners_for(options, label):
    return options[options["You"] == label].sort_values("Partner", ignore_index=True)


def test_helper_sheets_are_hidden(builder):
    for name in ("Lists", "Aliases", "Partner Legal"):
        assert builder.book.Worksheets(name).Visible == 0, name


def test_single_commander_lists_every_partner(builder, options):
    """Massacre Girl is the workhorse of Lorwyn Eclipsed's 7 legal teams."""
    sheet = builder.pick("Massacre Girl, Known Killer")
    expected = partners_for(options, "Massacre Girl, Known Killer")
    assert "single commander" in sheet.Range(f"A{STATUS}").Value
    assert sheet.Range(f"F{INFO2}").Value == len(expected)
    for k in (0, len(expected) // 2, len(expected) - 1):
        assert sheet.Range(f"A{FIRST + k}").Value == expected.loc[k, "Partner"]
        assert sheet.Range(f"I{FIRST + k}").Value == expected.loc[k, "Shared Set Codes"]
    assert not sheet.Range(f"A{FIRST + len(expected)}").Value  # one past the end


def test_a_rules_change_card_resolves(builder, options):
    """Shorikai is only eligible because eligibility is delegated to Scryfall."""
    sheet = builder.pick("Shorikai, Genesis Engine")
    expected = partners_for(options, "Shorikai, Genesis Engine")
    assert "single commander" in sheet.Range(f"A{STATUS}").Value
    assert sheet.Range(f"F{INFO2}").Value == len(expected)
    assert sheet.Range(f"A{FIRST}").Value == expected.loc[0, "Partner"]


def test_legal_partner_pair_names_its_mechanic(builder, sheets, options):
    units = sheets["Partner Pairs"]
    pair = units[units["Mechanic"] == "Doctor's companion"].iloc[0]
    sheet = builder.pick(pair["Commander A"], pair["Commander B"])
    label = f'{pair["Commander A"]} + {pair["Commander B"]}'
    assert "Doctor's companion" in sheet.Range(f"A{STATUS}").Value
    assert sheet.Range(f"F{INFO2}").Value == len(partners_for(options, label))


def test_card_order_does_not_matter(builder, sheets, options):
    """Excel's text collation differs from Python's ordinal sort, so the page
    resolves input through an alias table carrying both orders."""
    units = sheets["Partner Pairs"]
    pair = units[units["Mechanic"] == "Doctor's companion"].iloc[0]
    a, b = pair["Commander A"], pair["Commander B"]

    sheet = builder.pick(a, b)
    forward = [sheet.Range(f"A{FIRST + k}").Value for k in range(5)]
    sheet = builder.pick(b, a)
    assert [sheet.Range(f"A{FIRST + k}").Value for k in range(5)] == forward


def test_pair_that_never_shares_a_set_says_so(builder, sheets):
    plegal, units = sheets["Partner Legal"], sheets["Partner Pairs"]
    same_set = {f"{a}|{b}" for a, b in zip(units["Commander A"], units["Commander B"])}
    same_set |= {f"{b}|{a}" for a, b in zip(units["Commander A"], units["Commander B"])}
    row = next(r for _, r in plegal.iterrows() if r["Key"] not in same_set)
    sheet = builder.pick(row["Card A"], row["Card B"])
    assert "never appear together" in sheet.Range(f"A{STATUS}").Value
    assert not sheet.Range(f"A{FIRST}").Value


def test_pair_that_cannot_partner_says_so(builder):
    sheet = builder.pick("Massacre Girl, Known Killer", "Shorikai, Genesis Engine")
    assert "cannot be your commanders together" in sheet.Range(f"A{STATUS}").Value


def test_background_alone_is_explained(builder, sheets):
    background = sheets["Commanders"].query("`Can Lead Alone` != 'Yes'").iloc[0]["Commander"]
    sheet = builder.pick(background)
    assert "SECOND commander" in sheet.Range(f"A{STATUS}").Value


@pytest.mark.parametrize("first, second, fragment", [
    ("Shorikai, Genesis Engine", "Shorikai, Genesis Engine", "two different cards"),
    ("", "", "Pick your commander above"),
])
def test_input_edge_cases(builder, first, second, fragment):
    sheet = builder.pick(first, second)
    assert fragment in sheet.Range(f"A{STATUS}").Value


def test_collection_grid(builder, options):
    sheet = builder.pick("")
    row = options[options["You"] == "Massacre Girl, Known Killer"].iloc[0]
    sheet.Range(f"O{GRID_FIRST}").Value = "Massacre Girl, Known Killer"
    sheet.Range(f"O{GRID_FIRST + 1}").Value = row["Partner"]
    sheet.Range(f"O{GRID_FIRST + 2}").Value = "Shorikai, Genesis Engine"
    builder.excel.CalculateFullRebuild()

    assert sheet.Range("Q6").Value == row["Shared Set Codes"]   # legal team
    assert sheet.Range("P7").Value == row["Shared Set Codes"]   # and symmetric
    assert sheet.Range("R6").Value == "—"                       # not a legal team
    assert not sheet.Range("P6").Value                          # diagonal


def test_blank_mechanic_shows_blank_not_zero(builder, options):
    """Excel renders a formula pointing at an empty cell as 0.

    The mechanic column is empty for single commanders, so without coercion
    every such row displays a bare 0.
    """
    sheet = builder.pick("Massacre Girl, Known Killer")
    expected = partners_for(options, "Massacre Girl, Known Killer")
    singles = [k for k in range(len(expected)) if expected.loc[k, "Partner Mode"] == "Single"]
    assert singles, "fixture needs at least one single-commander row"
    for k in singles:
        assert not sheet.Range(f"C{FIRST + k}").Value, f"row {k} mechanic should be blank"


def test_no_formula_errors_anywhere_on_the_page(builder):
    sheet = builder.pick("Massacre Girl, Known Killer")
    bad = [(c.Address, c.Text)
           for area in (sheet.Range("A1:Z40"), sheet.Range(f"A{FIRST}:K{FIRST + 500}"))
           for c in area
           if isinstance(c.Text, str) and c.Text.strip() in EXCEL_ERRORS]
    assert bad == []
