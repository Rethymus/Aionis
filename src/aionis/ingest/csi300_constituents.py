"""CSI300 PIT historical constituents ingestion via index-constitution (MIT).

Track C S0 universe source for CSI300 cross-sectional membership.

This module provides point-in-time CSI300 constituents from the
`index-constitution` PyPI package (MIT license, Python 3.13 compatible).
Data is embedded in the package (no runtime HTTP), sourced from official
CSIndex (csindex.com.cn) announcements.

G3 no-revision contract: index composition announcements are immutable
historical facts (like EDGAR filings). Once announced, a constituent
addition/removal is fixed. The `index-constitution` package embeds a
snapshot of this reconstruction; version changes = new ledger row.

G6 survivorship: the CSV includes `opt-out` dates for delisted/removed
stocks. `constituents_on(t)` returns membership AS-OF date t (reconstructed
from historical announcements), NOT a today-snapshot.

Lazy import: index-constitution is intentionally NOT a core dependency.
Activate with `uv add index-constitution` before the first real pull
(MIT license, Python 3.13 compatible). Tests mock the module via `sys.modules`.

7-gate intake: `docs/data-intake-csi300-constituents.md` (PROPOSED, PASS).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import structlog

from aionis.config import settings

log = structlog.get_logger()

# Expected columns from index-constitution CSV
_CSV_COLUMNS = ["symbol", "name", "opt-in", "opt-out"]
_LONG_COLUMNS = ["date", "ticker"]


def _require_index_constitution() -> Any:
    """Lazy-import index-constitution (intentionally not a core dependency)."""
    try:
        import index_constitution as ic
    except ImportError as e:  # pragma: no cover - exercised when package missing
        raise ImportError(
            "index-constitution is required for CSI300 constituents (Track C S0). "
            "It is intentionally NOT a core dependency. Activate with "
            "`uv add index-constitution` (MIT license, Python 3.13 compatible)."
        ) from e
    return ic


def _cache_dir(cache_dir: Path | None = None) -> Path:
    """Get the cache directory for storing parquet snapshots."""
    d = cache_dir or settings.data_dir / "cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _parse_opt_in_opt_out_to_long(df: pd.DataFrame) -> pd.DataFrame:
    """Convert opt-in/opt-out wide format to long [date, ticker] daily membership.

    SEMANTICS (pinned): membership days are the HALF-OPEN interval
    ``[opt_in, opt_out)`` — from the opt-in day INCLUSIVE to the opt-out day
    EXCLUSIVE. On the opt-out (index-removal) day the stock is already NOT an
    index member, so no membership row is generated for that date. NaT handling
    (the raw data has 4 NaT opt-in + 300 NaT opt-out):

    * NaT opt-in, known opt-out → the stock predates the dataset's recording window
      (early/founding member); treat opt-in as the dataset's earliest known opt-in
      (conservative: member from data start).
    * NaT opt-out → still a member → extend to the SNAPSHOT DATE (not 2099-12-31 — the
      prior cap materialized ~73 years of future daily rows per current member, ~12M
      rows total). A future re-pull extends the cap; under the half-open contract
      constituents_on(t) is exact for t < snapshot date and returns nothing for
      t >= snapshot date for capped still-members (the cap day itself yields no row;
      we never query future membership).
    * both NaT → skip (cannot place membership).

    Degenerate intervals: ``opt_out < opt_in`` is skipped upstream (defensive);
    ``opt_out == opt_in`` yields an EMPTY membership period (zero rows); a one-day
    window (``opt_out == opt_in + 1``) yields exactly one row (the opt-in day).
    """
    if df.empty:
        return pd.DataFrame(columns=_LONG_COLUMNS)

    opt_in_col = pd.to_datetime(df["opt-in"])
    opt_out_col = pd.to_datetime(df["opt-out"])
    data_start = opt_in_col.min()  # earliest recorded opt-in (fallback for NaT opt-in)
    snapshot_date = pd.Timestamp.today().normalize()  # cap for still-members

    rows: list[tuple[pd.Timestamp, str]] = []
    for symbol, opt_in, opt_out in zip(df["symbol"], opt_in_col, opt_out_col, strict=True):
        symbol = str(symbol).strip()
        in_missing = bool(pd.isna(opt_in))
        out_missing = bool(pd.isna(opt_out))
        if in_missing and out_missing:
            continue  # cannot place membership at all
        if in_missing:
            opt_in = data_start  # predates dataset → member from data start
        if out_missing:
            opt_out = snapshot_date  # still a member → cap at snapshot date
        if opt_out < opt_in:
            continue  # defensive: malformed interval

        # Half-open [opt_in, opt_out): the removal day itself is NOT a member day.
        # opt_in == opt_out -> end < start -> empty range (empty membership period).
        dates = pd.date_range(start=opt_in, end=opt_out - pd.Timedelta(days=1), freq="D")
        for date in dates:
            rows.append((date, symbol))

    long_df = pd.DataFrame(rows, columns=_LONG_COLUMNS)
    long_df["date"] = pd.to_datetime(long_df["date"]).dt.normalize()
    return (
        long_df.drop_duplicates(["date", "ticker"])
        .sort_values(["date", "ticker"])
        .reset_index(drop=True)
    )


def fetch_csi300_constituents(
    cache_dir: Path | None = None,
    force: bool = False,
    enable_fetch: bool = False,
) -> pd.DataFrame:
    """Fetch CSI300 historical constituents as a long [date, ticker] DataFrame.

    The function reads from the embedded index-constitution CSV, converts
    opt-in/opt-out dates to daily membership, and caches the result as parquet.

    Args:
        cache_dir: Directory for cache files (default: settings.data_dir / "cache")
        force: If True, bypass cache and recompute from source CSV
        enable_fetch: If False (default), return cached data only; if True,
                      allow reading from index-constitution package (requires it installed)

    Returns:
        Long DataFrame with columns [date, ticker] representing daily CSI300
        membership. Each row indicates that a stock was a constituent on that date.

    Raises:
        ImportError: If enable_fetch=True and index-constitution not installed
        FileNotFoundError: If cache miss and enable_fetch=False

    Examples:
        >>> df = fetch_csi300_constituents(enable_fetch=True)
        >>> # Query PIT membership on a specific date
        >>> constituents_2020 = df[df["date"] == "2020-06-30"]["ticker"].tolist()
        >>> # Check if a stock was in CSI300 on a date
        >>> is_member = df[(df["ticker"] == "SZ000001") & (df["date"] == "2020-06-30")].shape[0] > 0
    """
    cdir = _cache_dir(cache_dir)
    pq_path = cdir / "csi300_constituents.parquet"

    # Return cached if available and not forcing refresh
    if pq_path.exists() and not force:
        log.info("csi300_constituents_cache_hit", path=str(pq_path))
        return pd.read_parquet(pq_path)

    # Cache miss: need to read from source (requires enable_fetch=True)
    if not enable_fetch:
        raise FileNotFoundError(
            f"Cached CSI300 constituents not found at {pq_path}. "
            "Set enable_fetch=True to read from index-constitution package "
            "(requires `uv add index-constitution`)."
        )

    # Lazy import index-constitution
    ic = _require_index_constitution()

    # Read history CSV from embedded package data
    log.info("csi300_constituents_fetch", source="index-constitution")
    history_df = ic.history("csi300")

    # Convert to long format
    long_df = _parse_opt_in_opt_out_to_long(history_df)

    # Cache as parquet
    long_df.to_parquet(pq_path)
    log.info(
        "csi300_constituents_loaded",
        rows=len(long_df),
        date_min=str(long_df["date"].min()),
        date_max=str(long_df["date"].max()),
        n_dates=int(long_df["date"].nunique()),
        n_tickers=int(long_df["ticker"].nunique()),
        cache_path=str(pq_path),
    )

    return long_df


def constituents_on(df: pd.DataFrame, date: str | pd.Timestamp) -> set[str]:
    """Query PIT membership as of a specific date (no forward-fill).

    This function returns the set of tickers that were CSI300 constituents
    on the exact date specified. It does NOT forward-fill from the most recent
    announcement, preventing look-ahead bias.

    Args:
        df: Long DataFrame from fetch_csi300_constituents (columns: date, ticker)
        date: Date to query (string YYYY-MM-DD or pd.Timestamp)

    Returns:
        Set of ticker symbols that were CSI300 members on the queried date.

    Examples:
        >>> df = fetch_csi300_constituents(enable_fetch=True)
        >>> members_2020 = constituents_on(df, "2020-06-30")
        >>> len(members_2020)
        300
    """
    date_norm = pd.to_datetime(date).normalize()
    subset = df[df["date"] == date_norm]
    return set(subset["ticker"].astype(str).tolist())


def verify_snapshot_integrity(
    df: pd.DataFrame,
    expected_date_range: tuple[str, str],
    expected_n_constituents: int | None = None,
) -> bool:
    """Verify that the CSI300 constituents snapshot meets basic integrity checks.

    Args:
        df: Long DataFrame from fetch_csi300_constituents
        expected_date_range: (start_date, end_date) expected coverage
        expected_n_constituents: Expected number of unique tickers (optional)

    Returns:
        True if all checks pass, False otherwise

    Raises:
        ValueError: If any check fails with details
    """
    if df.empty:
        raise ValueError("CSI300 constituents DataFrame is empty")

    date_min, date_max = expected_date_range
    actual_min = df["date"].min()
    actual_max = df["date"].max()

    if pd.to_datetime(date_min) > actual_min:
        raise ValueError(
            f"Date range start mismatch: expected <= {date_min}, got {actual_min}"
        )
    if pd.to_datetime(date_max) < actual_max:
        raise ValueError(
            f"Date range end mismatch: expected >= {date_max}, got {actual_max}"
        )

    if expected_n_constituents is not None:
        actual_n = df["ticker"].nunique()
        if actual_n != expected_n_constituents:
            raise ValueError(
                f"Unique ticker count mismatch: expected {expected_n_constituents}, "
                f"got {actual_n}"
            )

    return True
