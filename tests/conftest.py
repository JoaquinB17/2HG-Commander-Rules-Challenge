"""Shared fixtures.

The unit tests in test_rules.py need nothing but the package. The workbook and
Excel suites need a built workbook, and skip cleanly when one is not present.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from two_headed_giant import CACHE_DIR, DEFAULT_OUTPUT

BUILD_HINT = "Build one first: python -m two_headed_giant"


@pytest.fixture(scope="session")
def workbook_path() -> Path:
    if not DEFAULT_OUTPUT.exists():
        pytest.skip(f"{DEFAULT_OUTPUT} not found. {BUILD_HINT}")
    return DEFAULT_OUTPUT


@pytest.fixture(scope="session")
def sheets(workbook_path: Path) -> dict[str, pd.DataFrame]:
    """Every sheet of the workbook, read once."""
    book = pd.ExcelFile(workbook_path)
    return {name: book.parse(name) for name in book.sheet_names}


@pytest.fixture(scope="session")
def decklists() -> list[dict]:
    path = CACHE_DIR / "mtgjson_commander_decks.json"
    if not path.exists():
        pytest.skip(f"{path} not found. {BUILD_HINT}")
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def commander_universe() -> dict[str, dict]:
    path = CACHE_DIR / "scryfall_is_commander.json"
    if not path.exists():
        pytest.skip(f"{path} not found. {BUILD_HINT}")
    return json.loads(path.read_text(encoding="utf-8"))
