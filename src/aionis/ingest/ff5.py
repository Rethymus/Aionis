"""Fama-French 5-factor DAILY factor ingest — frozen snapshot + sha256 (RES-02).

Baseline-ladder data source (``docs/baseline-ladder.md``): the official
Kenneth French Data Library bulk ZIP
``F-F_Research_Data_5_Factors_2x3_daily_CSV.zip`` (daily frequency; monthly is
used only for cross-checks). Fetch/parse pattern reuses
``aionis.eval.ff5_residual`` (bulk ZIP + percent→decimal), upgraded with the
intake-rubric disciplines the exploratory trial requires:

* **G2 (PIT)**: the daily file carries a publish-date discipline — the value for
  day d is posted after the US equity close on d, hence knowable from d+1's open.
  Consumers must therefore never let a month-end feature computed at t use
  factor values dated after t (see ``aionis.features.ff5``, which builds the
  exposure window from observations with date <= t only).
* **G3 (no-revision)**: French publishes NO vintages; historical values may be
  revised. First ingestion therefore FREEZES the snapshot: the raw CSV is
  written once to ``data/cache/ff5_daily_snapshot.csv`` together with its
  sha256; every rerun reads the snapshot ONLY (zero HTTP, bit-identical — H6).
  Any upstream revision is a NEW snapshot + a NEW ledger row, never a silent
  overwrite.
* **G4 (reproducibility)**: the snapshot sha256 + source URL + fetch timestamp
  belong in the run config / ledger row (recorded by the runner, appended by
  the owner).
* **G5 (exploratory-only)**: no vintages ⇒ the FF5 side of BASELINE-FF5-001 is
  ``mode: exploratory`` (the DFF side via FRED/ALFRED is confirmatory-tier).
* **G7 (politeness)**: a single bulk ZIP fetch through the shared
  :class:`~aionis.ingest.http_policy.HttpRequestPolicy` — >=2s host spacing,
  bounded exponential retry, fail closed (no silent partial snapshot).
"""
from __future__ import annotations

import hashlib
import io
import zipfile
from pathlib import Path

import pandas as pd
import requests
import structlog

from aionis.ingest.http_policy import HttpRequestPolicy

log = structlog.get_logger()

FF5_DAILY_ZIP_URL = (
    "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
    "F-F_Research_Data_5_Factors_2x3_daily_CSV.zip"
)

# Stable FF5 daily factor set (Fama-French, 2015; same family as
# aionis.eval.ff5_residual). Values are decimal returns (e.g. 0.0012 = 0.12%).
FACTOR_COLS = ("mkt_rf", "smb", "hml", "rmw", "cma")
RF_COL = "rf"
ALL_COLS = ("date",) + FACTOR_COLS + (RF_COL,)

# Frozen snapshot files under data/cache/.
SNAPSHOT_CSV_NAME = "ff5_daily_snapshot.csv"
SNAPSHOT_SHA_NAME = "ff5_daily_snapshot.sha256"

# Fixed 7-column layout of the French daily CSV (date, Mkt-RF, SMB, HML, RMW,
# CMA, RF) — the order has been stable for years; the parser still validates
# every data row and drops (with a warning) any row with missing values.
_RAW_COLUMNS = ("date", "Mkt-RF", "SMB", "HML", "RMW", "CMA", "RF")
_NUMERIC_COLS = FACTOR_COLS + (RF_COL,)


def sha256_bytes(raw: bytes) -> str:
    """sha256 hex digest of ``raw`` bytes (the snapshot immutability anchor)."""
    return hashlib.sha256(raw).hexdigest()


def snapshot_sha256(snapshot_csv: Path) -> str:
    """sha256 of the snapshot CSV bytes on disk (G3/G4 frozen-truth anchor)."""
    return sha256_bytes(snapshot_csv.read_bytes())


def parse_ff5_daily_csv(raw: bytes) -> pd.DataFrame:
    """Parse the French daily FF5 CSV inside the bulk ZIP (percent → decimal).

    Doc lines and the header are located ROBUSTLY: the first row whose first
    cell is an 8-digit YYYYMMDD is the first data row; the row above it is the
    header (soft-verified, warned if unexpected). Columns are assigned in the
    fixed 7-column layout and converted from percent to decimal. Rows with any
    missing numeric value are dropped with a warning (fail closed on a fully
    empty result is the caller's job — a parse here returns the frame).

    Args:
        raw: bytes of the French ``..._daily_CSV.zip`` bulk file.

    Returns:
        DataFrame with columns ``ALL_COLS`` (date + mkt_rf/smb/hml/rmw/cma/rf
        as decimal returns), sorted by date, index reset.

    Raises:
        ValueError: if the ZIP contains no CSV, or no 8-digit-dated data rows
            are found, or the data rows do not carry the expected columns.
    """
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        csv_names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        if len(csv_names) != 1:
            raise ValueError(f"FF5 bulk ZIP must contain exactly one CSV, got {csv_names}")
        with zf.open(csv_names[0]) as f:
            raw_csv = f.read()

    lines = raw_csv.decode("latin1").splitlines()
    first_data_idx: int | None = None
    for i, line in enumerate(lines):
        first_cell = line.split(",", 1)[0].strip()
        if first_cell.isdigit() and len(first_cell) == 8:
            first_data_idx = i
            break
    if first_data_idx is None:
        raise ValueError("FF5 daily CSV: no YYYYMMDD data rows found")

    header_line = lines[first_data_idx - 1] if first_data_idx > 0 else ""
    expected_upper = {c.upper() for c in _RAW_COLUMNS[1:]}
    header_cells = {c.strip().upper() for c in header_line.split(",")}
    if not expected_upper.issubset(header_cells):
        log.warning("ff5_daily_header_unexpected", header=header_line)

    df = pd.read_csv(io.StringIO("\n".join(lines[first_data_idx:])), header=None, dtype=str)
    if df.shape[1] < len(_RAW_COLUMNS):
        raise ValueError(
            f"FF5 daily CSV data rows have {df.shape[1]} columns, expected >= {len(_RAW_COLUMNS)}"
        )
    df = df.iloc[:, : len(_RAW_COLUMNS)]
    df.columns = list(_RAW_COLUMNS)
    df = df.rename(
        columns={
            "Mkt-RF": "mkt_rf",
            "SMB": "smb",
            "HML": "hml",
            "RMW": "rmw",
            "CMA": "cma",
            "RF": "rf",
        }
    )
    df = df.apply(lambda c: c.str.strip())  # whitespace-tolerant (dtype=str)
    # French files sometimes carry trailing annotation lines (e.g. a
    # "Copyright ..." footer after the data rows); filter any row whose
    # date cell is not exactly 8 digits before dtype coercion.
    df = df[df["date"].str.fullmatch(r"\d{8}", na=False)]
    df["date"] = pd.to_datetime(df["date"], format="%Y%m%d")
    for col in _NUMERIC_COLS:
        df[col] = pd.to_numeric(df[col], errors="coerce") / 100.0

    n_before = len(df)
    df = df.dropna(subset=list(_NUMERIC_COLS))
    if len(df) != n_before:
        log.warning("ff5_daily_missing_values_dropped", n_dropped=n_before - len(df))
    if df.empty:
        raise ValueError("FF5 daily CSV parsed to zero valid rows (all values missing)")

    df = df[list(ALL_COLS)].sort_values("date").reset_index(drop=True)
    return df


def _snapshot_paths(cache_dir: Path) -> tuple[Path, Path]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / SNAPSHOT_CSV_NAME, cache_dir / SNAPSHOT_SHA_NAME


def fetch_ff5_daily_snapshot(
    cache_dir: Path,
    *,
    policy: HttpRequestPolicy | None = None,
    url: str = FF5_DAILY_ZIP_URL,
) -> tuple[pd.DataFrame, str]:
    """FF5 daily factors, snapshot-first (G3/G4) — cache hit makes zero HTTP.

    Cache miss: one polite bulk ZIP fetch through ``policy`` (default: shared
    >=2s host spacing + bounded exponential retry, fail closed), parse,
    freeze the CSV snapshot + record its sha256. Cache hit: read the snapshot
    ONLY and verify the recorded sha256 still matches the bytes (a drift is a
    hard error — the frozen truth must never change under a rerun).

    Returns ``(factors, sha256_of_snapshot_csv)``; the sha is the value that
    must be recorded in the run config / ledger row (G4).
    """
    csv_path, sha_path = _snapshot_paths(cache_dir)
    if csv_path.exists():
        df = pd.read_csv(csv_path, parse_dates=["date"])
        sha = snapshot_sha256(csv_path)
        recorded = sha_path.read_text().strip() if sha_path.exists() else ""
        if recorded and recorded != sha:
            raise RuntimeError(
                "FF5 snapshot sha256 mismatch: "
                f"recorded {recorded} != recomputed {sha} — snapshot bytes drifted; "
                "an upstream revision must be a NEW snapshot + NEW ledger row, "
                "never a silent overwrite"
            )
        log.info("ff5_snapshot_cache_hit", path=str(csv_path), sha256=sha)
        return df, sha

    fetcher = policy or HttpRequestPolicy()
    resp = fetcher.request(url, lambda: requests.get(url, timeout=60))
    df = parse_ff5_daily_csv(resp.content)
    csv_path.write_text(df.to_csv(index=False))
    sha = snapshot_sha256(csv_path)
    sha_path.write_text(sha + "\n")
    log.info(
        "ff5_snapshot_written",
        path=str(csv_path),
        sha256=sha,
        n_rows=len(df),
        source_url=url,
    )
    return df, sha


__all__ = [
    "FF5_DAILY_ZIP_URL",
    "FACTOR_COLS",
    "RF_COL",
    "ALL_COLS",
    "SNAPSHOT_CSV_NAME",
    "SNAPSHOT_SHA_NAME",
    "sha256_bytes",
    "snapshot_sha256",
    "parse_ff5_daily_csv",
    "fetch_ff5_daily_snapshot",
]
