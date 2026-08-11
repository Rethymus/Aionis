"""Hermetic tests for Form 4 incremental fetch (no network).

Imports the REAL helpers from ``scripts/form4_fetch.py`` (not copies) and locks
the two load-bearing invariants:

1. The merge dedupes on the FULL row, so an accession reporting multiple
   transactions is preserved (the real aggregate has up to 30 rows/accession —
   accession-only dedupe would collapse them and lose 86% of the data).
2. The per-issuer cursor tolerates a pre-``filing_date`` aggregate (schema
   migration) and NaN filing dates without crashing.
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import form4_fetch as f4  # noqa: E402


def _txns(
    accession: str,
    n: int,
    *,
    ticker: str = "AAPL",
    filing_date: str = "2024-06-01",
) -> pd.DataFrame:
    """Build ``n`` transaction rows sharing one accession (real Form-4 shape:
    a single filing reports multiple trades on different dates)."""
    fd = datetime.strptime(filing_date, "%Y-%m-%d")
    rows = []
    for i in range(n):
        rows.append(
            {
                "filer_cik": 1234567,
                "filer_name": "TEST INSIDER",
                "ticker": ticker,
                "transaction_date": fd + timedelta(days=i),
                "buy_or_sell": "buy" if i % 2 == 0 else "sell",
                "shares": 1000.0 * (i + 1),
                "price_per_share": 150.0 + i,
                "accession": accession,
                "filing_date": fd,
                "issuer_ticker": ticker,
            }
        )
    return pd.DataFrame(rows)


# --- cursor: _get_latest_filing_date_perissuer -------------------------------


def test_cursor_empty_when_no_file(tmp_path: Path) -> None:
    assert f4._get_latest_filing_date_perissuer(tmp_path / "absent.parquet") == {}


def test_cursor_migration_when_filing_date_column_absent(tmp_path: Path) -> None:
    # Pre-filing_date aggregate (the schema before this change) → {} → first-run fallback.
    old = _txns("ACC1", 3).drop(columns=["filing_date"])
    p = tmp_path / "agg.parquet"
    old.to_parquet(p, index=False)
    assert f4._get_latest_filing_date_perissuer(p) == {}


def test_cursor_skips_nan_filing_date(tmp_path: Path) -> None:
    df = _txns("ACC1", 2, filing_date="2024-06-01")
    df.loc[:, "filing_date"] = pd.NaT  # corrupt the column
    p = tmp_path / "agg.parquet"
    df.to_parquet(p, index=False)
    # All-NaN → issuer omitted → empty cursor → safe full-pull fallback.
    assert f4._get_latest_filing_date_perissuer(p) == {}


def test_cursor_per_issuer_latest(tmp_path: Path) -> None:
    aapl = _txns("A1", 2, ticker="AAPL", filing_date="2024-01-01")
    msft = _txns("M1", 2, ticker="MSFT", filing_date="2024-03-01")
    p = tmp_path / "agg.parquet"
    pd.concat([aapl, msft], ignore_index=True).to_parquet(p, index=False)
    cur = f4._get_latest_filing_date_perissuer(p)
    assert cur == {"AAPL": "2024-01-01", "MSFT": "2024-03-01"}


# --- merge: _merge_incremental -----------------------------------------------


def test_merge_first_run_returns_new_data() -> None:
    new = _txns("ACC1", 3)
    out = f4._merge_incremental(prev=None, new_data=new, latest_dates={})
    assert len(out) == 3
    assert out.equals(new)


def test_merge_preserves_multi_transaction_accession() -> None:
    # THE REGRESSION: one accession with 5 transactions, fully re-fetched.
    # Accession-only dedupe would collapse 5 → 1 (data loss). Full-row dedupe
    # removes the 5 exact duplicates and keeps the 5 distinct transactions.
    prev = _txns("ACC1", 5)
    new = _txns("ACC1", 5)  # same 5 rows, re-fetched
    out = f4._merge_incremental(prev=prev, new_data=new, latest_dates={"AAPL": "2024-06-01"})
    assert len(out) == 5  # not 1 — multi-tx accession preserved
    assert out["accession"].nunique() == 1


def test_merge_dedupes_exact_repeats_keeps_distinct() -> None:
    # prev has 3 distinct rows on ACC1; new has the same 3 (re-fetched) + 2 new.
    prev = _txns("ACC1", 3, filing_date="2024-06-01")
    new = pd.concat(
        [
            _txns("ACC1", 3, filing_date="2024-06-01"),  # re-fetch of prev
            _txns("ACC2", 2, filing_date="2024-08-01"),  # genuinely new
        ],
        ignore_index=True,
    )
    out = f4._merge_incremental(prev=prev, new_data=new, latest_dates={"AAPL": "2024-06-01"})
    assert len(out) == 5  # 3 (ACC1) + 2 (ACC2); exact dupes removed


def test_merge_migration_replaces_when_no_cursor() -> None:
    # Old aggregate lacks filing_date → cursor empty → new full pull REPLACES
    # (concat would create NaN/non-NaN dupes for the same transactions).
    prev = _txns("ACC1", 3).drop(columns=["filing_date"])  # pre-schema
    new = _txns("ACC1", 4)  # fresh full pull carries filing_date
    out = f4._merge_incremental(prev=prev, new_data=new, latest_dates={})
    assert len(out) == 4  # replaced, not 3+4=7
    assert "filing_date" in out.columns
