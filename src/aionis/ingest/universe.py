"""Point-in-time S&P 500 membership universe (survivorship-correct, cross-phase).

Two independent MIT-licensed reconstructions, both **committed data** (no scraper
runs at ingest time → deterministic + polite by construction):
  * ``hanshof/sp500_constituents`` — DAILY constituents 1996-01-02→present
    (``sp_500_historical_components.csv``); primary.
  * ``pierrebrunelle/sp500-historical-constituents`` — MONTHLY snapshots
    2016-01→2026-04 (``data/spy{YYYYMM}``, 124 files); cross-check (pre-reg §3/§8.0).

The cross-section universe MUST be PIT — backtesting today's-500 on history is
textbook survivorship bias. This module also closes the ``cik_map`` look-ahead
leak (critic C1): the ticker set fundamentals are fetched for now comes from PIT
membership here, NOT from SEC's current ``company_tickers.json`` snapshot.

Permanent + cross-phase: reused by Phase B selection rank-IC and every later
phase needing a survivorship-controlled universe (NOT Phase-B scaffolding).
Raw files cached under ``data/cache/`` (sha256-pinnable) so reruns make no HTTP.
"""
from __future__ import annotations

import hashlib
import io
import tarfile
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import Literal

import pandas as pd
import requests
import structlog

from aionis.config import settings
from aionis.ingest.http_policy import HttpRequestPolicy, RetryPolicy

log = structlog.get_logger()

_HANSHOF_URL = (
    "https://raw.githubusercontent.com/hanshof/sp500_constituents/"
    "master/sp_500_historical_components.csv"
)
_PB_TARBALL = (
    "https://codeload.github.com/pierrebrunelle/"
    "sp500-historical-constituents/tar.gz/refs/heads/main"
)

_HTTP_POLICY = HttpRequestPolicy(retry_exceptions=(requests.RequestException,))


def _policy_get(
    url: str,
    *,
    total_attempts: int | None = None,
    backoff_base: float = 2.0,
    backoff_mode: Literal["exponential", "linear"] = "exponential",
    **kwargs: object,
) -> requests.Response:
    """Issue one approved direct GET through the process-wide HTTP policy."""
    retry = None
    if total_attempts is not None:
        retry = RetryPolicy(
            max_retries=total_attempts - 1,
            backoff_base=backoff_base,
            backoff_mode=backoff_mode,
        )
    def operation() -> requests.Response:
        return requests.get(url, **kwargs)

    if retry is None:
        return _HTTP_POLICY.request(url, operation)
    return _HTTP_POLICY.request(url, operation, retry=retry)


def _cache_dir(cache_dir: Path | None = None) -> Path:
    d = cache_dir or settings.data_dir / "cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


def normalize_ticker(s: str) -> str:
    """Canonical ticker: upper-case + share-class separator canonicalized to ``-``.

    Three conventions exist for the same thing (``BRK.B`` / ``BRK/B`` / ``BRK-B``)
    across hanshof (``-``), pierrebrunelle (``/``) and the price feeds; all map to
    ``-``. Idempotent. Preserves bankruptcy/history suffixes (e.g. ``EKDKQ``) —
    those are real identity, not formatting noise.
    """
    return s.strip().upper().replace(".", "-").replace("/", "-")


# --- parsers (pure functions; testable on strings/file dicts, no network) ---

def _parse_hanshof_csv(text: str) -> pd.DataFrame:
    """Parse hanshof ``date,tickers`` CSV text -> long ``[date, ticker]``.

    The tickers column is a quoted comma-list; one row per (date, constituent).
    """
    df = pd.read_csv(StringIO(text))
    rows: list[tuple[pd.Timestamp, str]] = []
    dates = pd.to_datetime(df["date"])
    for d, raw in zip(dates, df["tickers"], strict=True):
        for t in str(raw).split(","):
            t = t.strip()
            if t:
                rows.append((d, normalize_ticker(t)))
    out = pd.DataFrame(rows, columns=["date", "ticker"])
    out["date"] = pd.to_datetime(out["date"]).dt.normalize()
    return (
        out.drop_duplicates(["date", "ticker"])
        .sort_values(["date", "ticker"]).reset_index(drop=True)
    )


def _parse_pierrebrunelle_files(files: dict[str, str]) -> pd.DataFrame:
    """Parse ``{filename: text}`` (names like ``spy201801``) -> long ``[date, ticker]``.

    Each file line is ``SYMBOL\\tNAME\\tWEIGHT``; ``date`` = month-start of YYYYMM.
    """
    rows: list[tuple[pd.Timestamp, str]] = []
    for fname, text in files.items():
        month_start = pd.to_datetime(fname.replace("spy", "") + "01")
        for line in text.splitlines():
            parts = line.split("\t")
            if not parts or not parts[0].strip():
                continue
            rows.append((month_start, normalize_ticker(parts[0])))
    out = pd.DataFrame(rows, columns=["date", "ticker"])
    out["date"] = pd.to_datetime(out["date"]).dt.normalize()
    return (
        out.drop_duplicates(["date", "ticker"])
        .sort_values(["date", "ticker"]).reset_index(drop=True)
    )


# --- loaders (network + cache; not exercised by the hermetic test suite) ---

def load_hanshof_membership(
    cache_dir: Path | None = None, force: bool = False,
) -> pd.DataFrame:
    """Long PIT DAILY membership ``[date, ticker]`` from hanshof. Cached as parquet.

    The raw CSV is also cached so a rerun makes no HTTP call; its sha256 is the
    pinned snapshot (satisfies the pre-reg §8 "fork + audit" intent locally).
    """
    cdir = _cache_dir(cache_dir)
    pq, csv = cdir / "universe_hanshof.parquet", cdir / "hanshof_sp500_components.csv"
    if pq.exists() and not force:
        return pd.read_parquet(pq)
    text = csv.read_text() if csv.exists() else None
    if text is None:
        log.info("universe_fetch_hanshof", url=_HANSHOF_URL)
        r = _policy_get(_HANSHOF_URL, headers={"User-Agent": "aionis/0.1"}, timeout=120)
        r.raise_for_status()
        text = r.text
        csv.write_text(text)
    mem = _parse_hanshof_csv(text)
    mem.to_parquet(pq)
    log.info("universe_hanshof_loaded", rows=len(mem), date_min=str(mem["date"].min()),
             date_max=str(mem["date"].max()), n_dates=int(mem["date"].nunique()),
             n_tickers=int(mem["ticker"].nunique()),
             sha256=_sha256(csv))
    return mem


def load_pierrebrunelle_membership(
    cache_dir: Path | None = None, force: bool = False,
) -> pd.DataFrame:
    """Long PIT MONTHLY membership from pierrebrunelle ``data/spy*``. Cached as parquet.

    Downloads the repo tarball once (one polite call) and caches it.
    """
    cdir = _cache_dir(cache_dir)
    pq, tgz = cdir / "universe_pierrebrunelle.parquet", cdir / "pierrebrunelle.tar.gz"
    if pq.exists() and not force:
        return pd.read_parquet(pq)
    files: dict[str, str] = {}
    if tgz.exists():
        files = _read_spy_files_from_tarball(tgz)
    else:
        log.info("universe_fetch_pierrebrunelle")
        r = _policy_get(_PB_TARBALL, headers={"User-Agent": "aionis/0.1"}, timeout=180)
        r.raise_for_status()
        tgz.write_bytes(r.content)
        files = _read_spy_files_from_tarball(tgz)
    mem = _parse_pierrebrunelle_files(files)
    mem.to_parquet(pq)
    log.info("universe_pierrebrunelle_loaded", rows=len(mem), date_min=str(mem["date"].min()),
             date_max=str(mem["date"].max()), n_months=int(mem["date"].nunique()),
             sha256=_sha256(tgz))
    return mem


def _read_spy_files_from_tarball(tgz: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    with tarfile.open(tgz) as tf:
        for m in tf.getmembers():
            base = Path(m.name).name
            if m.isfile() and base.startswith("spy"):
                f = tf.extractfile(m)
                if f is not None:
                    out[base] = io.TextIOWrapper(f, encoding="utf-8").read()
    return out


def _sha256(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


@dataclass(frozen=True)
class ConstituentsManifest:
    """Immutable snapshot manifest for a point-in-time constituent query.

    Attributes:
        members: Frozen set of ticker symbols in the snapshot
        snapshot_date: Date of the membership snapshot used (None if no snapshot ≤ query date)
        age_days: Days between query date and snapshot_date (None if no snapshot)
        hash: SHA-256 hex digest of sorted member tickers (None if empty/no snapshot)
    """
    members: frozenset[str]
    snapshot_date: pd.Timestamp | None
    age_days: int | None
    hash: str | None


def _resolve_snapshot(membership: pd.DataFrame, date) -> tuple[set[str], pd.Timestamp | None]:
    """Resolve the latest snapshot on or before date.

    Returns:
        (members, snapshot_date): Set of ticker symbols and the snapshot date.
        snapshot_date is None if no snapshot exists ≤ date.
    """
    as_of = pd.Timestamp(date).normalize()
    sub = membership[membership["date"] <= as_of]
    if sub.empty:
        return set(), None
    latest = sub["date"].max()
    return set(membership.loc[membership["date"] == latest, "ticker"]), latest


# --- PIT access + cross-source agreement (pure, testable) ---

def constituents_on(membership: pd.DataFrame, date) -> set[str]:
    """PIT constituent set as of ``date``: the membership of the latest snapshot
    on or before ``date``. Empty if no snapshot exists yet (no forward-fill)."""
    members, _snapshot_date = _resolve_snapshot(membership, date)
    return members


def constituents_manifest_on(membership: pd.DataFrame, date) -> ConstituentsManifest:
    """PIT constituent manifest as of ``date`` with snapshot metadata.

    Returns an immutable structure containing:
      - members: frozen set of ticker symbols
      - snapshot_date: date of the snapshot used (None if no snapshot ≤ date)
      - age_days: days between query date and snapshot_date (None if no snapshot)
      - hash: SHA-256 hex digest of sorted member tickers (None if empty/no snapshot)

    Age is REPORTED only; no freshness threshold is enforced.
    """
    as_of = pd.Timestamp(date).normalize()
    members, snapshot_date = _resolve_snapshot(membership, date)

    if snapshot_date is None:
        return ConstituentsManifest(
            members=frozenset(),
            snapshot_date=None,
            age_days=None,
            hash=None,
        )

    age_days = (as_of - snapshot_date).days
    hash_str = hashlib.sha256(",".join(sorted(members)).encode()).hexdigest() if members else None

    return ConstituentsManifest(
        members=frozenset(members),
        snapshot_date=snapshot_date,
        age_days=age_days,
        hash=hash_str,
    )


def mask_panel_to_pit(panel: pd.DataFrame, membership: pd.DataFrame) -> pd.DataFrame:
    """Filter a tidy ``[date, ticker, ...]`` panel to rows whose ticker was a PIT
    constituent on that date (latest membership snapshot ``<= date``).

    Rows dated before the first membership snapshot are dropped (the universe is
    never forward-filled). This is the survivorship mask applied before rank-IC so
    a date's cross-section is exactly its PIT index members — NOT today's 500.
    """
    import numpy as np

    snap = pd.DatetimeIndex(pd.to_datetime(membership["date"]).unique()).sort_values()
    snap_arr = snap.to_numpy(dtype="datetime64[ns]")
    pan = panel.copy()
    pan["date"] = pd.to_datetime(pan["date"]).dt.normalize()
    pos = np.searchsorted(snap_arr, pan["date"].to_numpy(dtype="datetime64[ns]"), side="right") - 1
    valid = pos >= 0
    pan = pan.loc[valid].copy()
    pan["_snap"] = snap_arr[np.clip(pos[valid], 0, len(snap_arr) - 1)]
    out = pan.merge(
        membership[["date", "ticker"]].rename(columns={"date": "_snap"}),
        on=["_snap", "ticker"], how="inner",
    )
    return out.drop(columns=["_snap"]).reset_index(drop=True)


def pierrebrunelle_names(
    cache_dir: Path | None = None, force: bool = False,
) -> dict[str, str]:
    """``{normalized ticker: modal company name}`` from pierrebrunelle's ``data/spy*``
    (each line ``SYMBOL\\tNAME\\tWEIGHT``). The historical names power the
    ticker-reuse entity-mismatch cross-check. Cached as parquet."""
    cdir = _cache_dir(cache_dir)
    pq = cdir / "pierrebrunelle_names.parquet"
    if pq.exists() and not force:
        df = pd.read_parquet(pq)
        return dict(zip(df["ticker"], df["name"], strict=True))
    tgz = cdir / "pierrebrunelle.tar.gz"
    files = _read_spy_files_from_tarball(tgz) if tgz.exists() else {}
    rows: list[tuple[str, str]] = []
    for text in files.values():
        for line in text.splitlines():
            parts = line.split("\t")
            if len(parts) >= 2 and parts[0].strip():
                rows.append((normalize_ticker(parts[0]), parts[1].strip()))
    df = pd.DataFrame(rows, columns=["ticker", "name"])
    df = (
        df.groupby("ticker")["name"]
        .agg(lambda s: s.mode().iloc[0] if not s.mode().empty else s.iloc[0])
        .reset_index()
    )
    df.to_parquet(pq)
    return dict(zip(df["ticker"], df["name"], strict=True))


# --- ticker-reuse entity-mismatch filter (two-stage: token flag -> SEC confirm) ---

_SUFFIX_WORDS = {
    "inc", "corp", "corporation", "ltd", "co", "group", "holdings", "holding",
    "the", "plc", "ag", "sa", "nv", "llc", "international", "industries",
    "companies", "enterprises", "limited", "company",
}


def _name_tokens(name: str) -> set[str]:
    """Significant word-tokens of a company name: lower-cased, all non-alphanumeric
    chars -> spaces (handles en-dash ``Brown–Forman``, possessives ``Domino's``,
    punctuation), corporate suffixes removed, and a light trailing-``s`` stem (so
    ``Dominos``/``Domino's``, ``Kohls``/``Kohl's`` align). Token length >= 2 so a
    name that degenerates to its ticker (``BB&T`` -> ``bb``) still carries signal."""
    import re

    t = re.sub(r"[^a-z0-9]+", " ", name.lower())
    out: set[str] = set()
    for w in t.split():
        if len(w) < 2 or w in _SUFFIX_WORDS:
            continue
        out.add(w[:-1] if len(w) > 4 and w.endswith("s") else w)
    return out


def names_agree(sec_title: str, pb_name: str) -> bool:
    """Stage-1 (coarse): do the two names share >= 1 significant token? Conservative
    — ambiguous names (no significant tokens) are treated as agreeing (don't
    over-flag). Used to FLAG candidates; confirmation is stage-2
    (:func:`confirm_reuse_mismatches`)."""
    a, b = _name_tokens(sec_title), _name_tokens(pb_name)
    if not a or not b:
        return True
    return bool(a & b)


def _is_abbreviation(tokens: set[str], ticker: str) -> bool:
    """The name is just the ticker abbreviation (e.g. PB name ``IBM``) -> can't verify
    via tokens -> keep (PB membership already vouches for it)."""
    return bool(tokens) and tokens <= {normalize_ticker(ticker).lower()}


def filter_reuse_mismatches(
    resolved: dict[str, int], pb_names: dict[str, str], sec_titles: dict[int, str],
) -> tuple[dict[str, int], dict[str, dict]]:
    """Stage-1 (pure): flag resolved tickers whose SEC title and pierrebrunelle name
    share no significant token. Returns ``(clean, flagged)`` where ``flagged`` are
    CANDIDATES pending stage-2 confirmation (most are legit renames / abbreviations,
    NOT true reuse). Tickers absent from either name source are kept.
    """
    clean: dict[str, int] = {}
    flagged: dict[str, dict] = {}
    for ticker, cik in resolved.items():
        pb = pb_names.get(ticker)
        sec = sec_titles.get(cik)
        if pb is None or sec is None or names_agree(sec, pb):
            clean[ticker] = cik
        else:
            flagged[ticker] = {"cik": cik, "sec": sec, "pb": pb}
    return clean, flagged


def _name_similarity(a: str, b: str) -> float:
    """Character-level similarity (difflib ratio) — catches concat / short-form
    renames that share no token: ``Supermicro`` vs ``Super Micro Computer``."""
    from difflib import SequenceMatcher

    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


# Manually verified legit renames the heuristic cannot confirm (no token AND low
# char-similarity between the PB common name and the SEC legal name). Auditable;
# re-check on data refresh. GE Aerospace IS General Electric (same CIK 0040533).
_LEGIT_RENAME_OVERRIDES: set[str] = {"GE"}


def confirm_reuse_mismatches(
    flagged: dict[str, dict], pb_names: dict[str, str],
    cache_dir: Path | None = None,
) -> dict[str, dict]:
    """Stage-2 (robust, network): for each stage-1 candidate, fetch the resolved
    CIK's name history (SEC ``submissions`` current + ``formerNames``). Legit
    rename (keep) if the pierrebrunelle name shares a token with any current/former
    name, OR has high char-similarity (concatenated/short-form), OR is just the
    ticker abbreviation, OR is a reviewed override. Otherwise the resolved CIK is a
    DIFFERENT company that reused the ticker -> confirmed reuse (drop).

    One cached submissions fetch per candidate (~tens, not the full universe).
    """
    from aionis.ingest.cik_resolver import cik_name_history

    confirmed: dict[str, dict] = {}
    for ticker, info in flagged.items():
        if ticker in _LEGIT_RENAME_OVERRIDES:
            continue
        pb = pb_names.get(ticker, "")
        pb_tok = _name_tokens(pb)
        if _is_abbreviation(pb_tok, ticker):
            continue
        hist = cik_name_history(info["cik"], cache_dir)
        sec_names = [hist["current"], *hist["former"]]
        sec_names = [n for n in sec_names if n]
        if any(_name_tokens(n) & pb_tok for n in sec_names):
            continue
        # Char-similarity fallback for concat / short-form renames sharing no token
        # (e.g. ``Supermicro`` vs ``Super Micro Computer``). 0.5 is empirically tuned
        # with a ~0.06 margin: legit SMCI 0.556 >= 0.5 (keep) vs true-reuse POM 0.444 /
        # SE 0.381 / STI 0.267 < 0.5 (drop). Re-verify on data refresh.
        if any(_name_similarity(pb, n) >= 0.5 for n in sec_names):
            continue
        confirmed[ticker] = info
    return confirmed


def build_oos_resolvable_universe(
    start: str = "2016-01-01", cache_dir: Path | None = None,
) -> dict:
    """The clean OOS universe: pierrebrunelle members (>= ``start``) that resolve to
    a SEC CIK AND survive the two-stage ticker-reuse check. This is the
    survivorship-correct, correctly-resolved set Phase B fetches fundamentals for.
    Both arms use this SAME set, so the rank-IC differential isolates
    fundamental-timing regardless of the coverage reduction (a scope limitation, not
    a bias). Drops only confirmed ticker-reuse entity-mismatches (stage-2 verified).
    """
    # lazy import: cik_resolver imports normalize_ticker from this module
    from aionis.ingest.cik_resolver import cik_title_map, resolve_ciks

    pb = load_pierrebrunelle_membership(cache_dir)
    pb = pb[pb["date"] >= pd.Timestamp(start)]
    pb_tickers = sorted({normalize_ticker(t) for t in pb["ticker"].unique()})
    resolved = resolve_ciks(pb_tickers, cache_dir)
    pb_names = pierrebrunelle_names(cache_dir)
    sec_titles = cik_title_map(cache_dir)
    _clean_stage1, flagged = filter_reuse_mismatches(resolved, pb_names, sec_titles)
    confirmed = confirm_reuse_mismatches(flagged, pb_names, cache_dir)
    clean = {t: c for t, c in resolved.items() if t not in confirmed}
    unresolved = [t for t in pb_tickers if t not in resolved]
    log.info(
        "oos_resolvable_universe", n_pb=len(pb_tickers), n_resolved=len(resolved),
        n_flagged=len(flagged), n_confirmed_reuse=len(confirmed), n_clean=len(clean),
        n_unresolved=len(unresolved),
    )
    return {
        "tickers": sorted(clean), "ciks": clean,
        "flagged": flagged, "dropped": confirmed, "unresolved": unresolved,
        "n_pb": len(pb_tickers), "n_resolved": len(resolved),
        "n_clean": len(clean),
    }

def jaccard_monthly(
    mem_daily: pd.DataFrame, mem_monthly: pd.DataFrame, start: str = "2016-01-01",
) -> pd.Series:
    """Monthly Jaccard overlap of a daily source vs a monthly source.

    For each month >= ``start`` present in ``mem_monthly``: ``A`` = daily
    constituents on the latest daily date within that month, ``B`` = the monthly
    snapshot; ``J = |A ∩ B| / |A ∪ B|``. Indexed by month-start.
    """
    start_ts = pd.Timestamp(start)
    daily_by_date = {d: set(g["ticker"]) for d, g in mem_daily.groupby("date")}
    recs: list[tuple[pd.Timestamp, float]] = []
    for month_start, g in mem_monthly.groupby("date"):
        if month_start < start_ts:
            continue
        end_of_month = month_start + pd.offsets.MonthEnd(0)
        in_month = [d for d in daily_by_date if month_start <= d <= end_of_month]
        if not in_month:
            continue
        a, b = daily_by_date[max(in_month)], set(g["ticker"])
        union = a | b
        recs.append((month_start, (len(a & b) / len(union)) if union else 1.0))
    jac = pd.Series(dict(recs))
    jac.index.name = "month"
    return jac.sort_index()


def universe_agreement_verdict(jac: pd.Series, threshold: float = 0.95) -> dict:
    """Apply pre-reg §8.0 frozen rule.

    ``min monthly Jaccard >= threshold`` -> the two independent reconstructions
    agree → hanshof is trusted for the full range (OOS 2017-2026 stands).
    Below threshold -> disagreement → headline restricted to the pierrebrunelle
    reproducible window (2016+) and both reported as sensitivity. Pure function
    over the Jaccard series; the outcome is logged to the ledger by the caller.
    """
    if jac.empty:
        return {"agreement": None, "min_jaccard": float("nan"),
                "mean_jaccard": float("nan"), "min_jaccard_month": None,
                "n_months": 0, "threshold": threshold,
                "verdict": "no overlap to compare"}
    mn_month, mn = jac.idxmin(), float(jac.min())
    mean = float(jac.mean())
    agree = mn >= threshold
    verdict = (
        f"min monthly Jaccard {mn:.4f} >= {threshold} at {mn_month}: hanshof trusted full range"
        if agree else
        f"min monthly Jaccard {mn:.4f} < {threshold} at {mn_month}: "
        f"headline OOS restricted to 2016+ reproducible window"
    )
    return {"agreement": agree, "min_jaccard": mn, "mean_jaccard": mean,
            "min_jaccard_month": mn_month, "n_months": int(len(jac)),
            "threshold": threshold, "verdict": verdict}
