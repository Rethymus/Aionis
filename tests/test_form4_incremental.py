"""Hermetic tests for Form 4 incremental fetch (no network).

Imports the REAL helpers from ``scripts/form4_fetch.py`` (not copies) and locks
the load-bearing invariants:

1. ``_accumulate`` ALWAYS concats (per-issuer write-through) — a cursor-aware
   merge here would drop prior issuers on the first run (regression-tested).
2. Dedupe is on the FULL row, so an accession reporting multiple transactions
   is preserved (the real aggregate has up to 30 rows/accession — accession-only
   dedupe would collapse them and lose 86% of the data).
3. The per-issuer cursor tolerates a pre-``filing_date`` aggregate (schema
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
    assert f4._get_latest_filing_date_perissuer(p) == {}


def test_cursor_per_issuer_latest(tmp_path: Path) -> None:
    aapl = _txns("A1", 2, ticker="AAPL", filing_date="2024-01-01")
    msft = _txns("M1", 2, ticker="MSFT", filing_date="2024-03-01")
    p = tmp_path / "agg.parquet"
    pd.concat([aapl, msft], ignore_index=True).to_parquet(p, index=False)
    cur = f4._get_latest_filing_date_perissuer(p)
    assert cur == {"AAPL": "2024-01-01", "MSFT": "2024-03-01"}


# --- accumulate: _accumulate (per-issuer write-through) ----------------------


def test_accumulate_first_call_returns_new_data() -> None:
    new = _txns("ACC1", 3)
    out = f4._accumulate(None, new)
    assert len(out) == 3


def test_accumulate_first_run_multi_issuer_preserves_all() -> None:
    # THE REGRESSION: main() accumulates per-issuer on the first run (no cursor).
    # An earlier cursor-aware _merge_incremental dropped `running` when
    # latest_dates was empty → only the LAST issuer survived. _accumulate always
    # concats, so both issuers survive.
    aapl = _txns("A1", 3, ticker="AAPL", filing_date="2024-01-01")
    msft = _txns("M1", 2, ticker="MSFT", filing_date="2024-03-01")
    running = f4._accumulate(None, aapl)
    running = f4._accumulate(running, msft)
    assert len(running) == 5
    assert set(running["issuer_ticker"]) == {"AAPL", "MSFT"}


def test_accumulate_preserves_multi_transaction_accession() -> None:
    # One accession with 5 transactions, fully re-fetched. Accession-only dedupe
    # would collapse 5 → 1 (data loss). Full-row dedupe keeps the 5 distinct rows.
    prev = _txns("ACC1", 5)
    new = _txns("ACC1", 5)  # same 5 rows, re-fetched
    out = f4._accumulate(prev, new)
    assert len(out) == 5
    assert out["accession"].nunique() == 1


def test_accumulate_dedupes_exact_repeats_keeps_distinct() -> None:
    prev = _txns("ACC1", 3, filing_date="2024-06-01")
    new = pd.concat(
        [
            _txns("ACC1", 3, filing_date="2024-06-01"),  # re-fetch of prev
            _txns("ACC2", 2, filing_date="2024-08-01"),  # genuinely new
        ],
        ignore_index=True,
    )
    out = f4._accumulate(prev, new)
    assert len(out) == 5  # 3 (ACC1) + 2 (ACC2); exact dupes removed


# --- per-issuer checkpointing (write-through path) ---------------------------


def test_checkpoint_after_first_issuer_saved_immediately(tmp_path: Path) -> None:
    # main()'s per-issuer write-through: after issuer 1 of 2 completes, the
    # aggregate exists on disk with only issuer 1's transactions.
    out_path = tmp_path / "form4_aggregate.parquet"
    aapl = _txns("A1", 3, ticker="AAPL", filing_date="2024-01-15")
    running_agg = f4._accumulate(None, aapl)
    running_agg.to_parquet(out_path, index=False)
    assert out_path.exists()
    checkpoint = pd.read_parquet(out_path)
    assert len(checkpoint) == 3
    assert set(checkpoint["issuer_ticker"]) == {"AAPL"}


def test_checkpoint_resumed_run_preserves_prior_issuer_data(tmp_path: Path) -> None:
    # A timed-out run saved issuer 1; the resumed run reads it back + adds issuer 2.
    out_path = tmp_path / "form4_aggregate.parquet"
    aapl = _txns("A1", 3, ticker="AAPL", filing_date="2024-01-15")
    aapl.to_parquet(out_path, index=False)
    # main() seeds running_agg from OUT when the cursor is valid, then accumulates.
    running_agg = pd.read_parquet(out_path)
    msft = _txns("M1", 2, ticker="MSFT", filing_date="2024-03-10")
    running_agg = f4._accumulate(running_agg, msft)
    running_agg.to_parquet(out_path, index=False)
    final = pd.read_parquet(out_path)
    assert len(final) == 5
    assert set(final["issuer_ticker"]) == {"AAPL", "MSFT"}


def test_checkpoint_multi_transaction_accession_survives_write_through(tmp_path: Path) -> None:
    # Multi-transaction accession survives the per-issuer write-through path
    # (a re-fetch of the same accession must not collapse to one row).
    out_path = tmp_path / "form4_aggregate.parquet"
    prev = _txns("ACC1", 5, ticker="AAPL", filing_date="2024-06-01")
    prev.to_parquet(out_path, index=False)
    running_agg = pd.read_parquet(out_path)
    refetch = _txns("ACC1", 5, ticker="AAPL", filing_date="2024-06-01")
    running_agg = f4._accumulate(running_agg, refetch)
    running_agg.to_parquet(out_path, index=False)
    final = pd.read_parquet(out_path)
    assert len(final) == 5  # not 1 — multi-tx accession preserved through checkpoint
