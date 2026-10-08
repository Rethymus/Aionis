"""Guard: docs/RESULTS.md section-6 ledger index must not lag the ledger.

This drift class hit twice (rounds 224->232 and 233->234: new exploratory
ledger rows landed without the section-6 index following). Assertions:

1. BOUND (no false positives on historical rows): the MAX exploratory row
   number indexed in section 6 >= the max exploratory row number in the
   ledger — a new exploratory row cannot land unindexed.
2. MODERN CONVENTION (exact, from row #59 on): every exploratory ledger
   row >= 59 is individually indexed in section 6.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "docs" / "RESULTS.md"
LEDGER = ROOT / "runs" / "ledger.jsonl"

MODERN_FLOOR = 59  # one-row-per-diagnostic indexing convention start


def _indexed_numbers() -> set[int]:
    text = RESULTS.read_text(encoding="utf-8")
    section = text.split("## 6. Ledger 索引", 1)[1]
    nums: set[int] = set()
    for cell in re.findall(
            r"\|\s*\**#?(\d+(?:/\#?\d+)*)\**\s*\|", section):
        for part in cell.split("/"):
            nums.add(int(part.lstrip("#")))
    assert nums, "section-6 index table not found — extraction pattern rotted"
    return nums


def _exploratory_rows() -> list[int]:
    rows = [json.loads(ln) for ln in
            LEDGER.read_text(encoding="utf-8").splitlines() if ln.strip()]
    return [i for i, r in enumerate(rows, 1)
            if r.get("event") == "exploratory"]


def test_section6_max_covers_ledger_max() -> None:
    indexed = _indexed_numbers()
    expl = _exploratory_rows()
    assert max(indexed) >= max(expl), (
        f"section-6 index max #{max(indexed)} lags ledger exploratory max "
        f"#{max(expl)} — a new exploratory row landed unindexed"
    )


def test_section6_indexes_every_modern_exploratory_row() -> None:
    indexed = _indexed_numbers()
    missing = [n for n in _exploratory_rows()
               if n >= MODERN_FLOOR and n not in indexed]
    assert not missing, (
        f"exploratory rows missing from the section-6 index: {missing}"
    )
