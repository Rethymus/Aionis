"""Historical ticker -> SEC CIK resolution (closes the ``cik_map`` look-ahead leak).

``fundamentals.cik_map`` builds its ticker->CIK map from SEC's CURRENT
``company_tickers.json`` snapshot, which lists only tickers active TODAY. The PIT
universe (``universe.py``) carries ~1126 distinct tickers spanning 1996-2025,
including renamed / delisted ones (FB->META, BLL->BALL, BBT, ANTM, EKDKQ), so the
current-only map misses them. This resolver resolves ticker STRINGS to their
stable SEC CIK so ``fundamentals.company_facts(cik)`` works. CIK is stable per
company (FB and META share CIK 1326801); this is a static ticker-string->CIK
lookup, NOT a universe definition.

Source
------
SEC EDGAR ``company_tickers.json``
(https://www.sec.gov/files/company_tickers.json) - a ~1 MB JSON listing every
entity with an active SEC ticker. Free, no auth, fair-access policy (<=10 req/s),
descriptive User-Agent only. Data produced by the U.S. Securities and Exchange
Commission is a work of the U.S. federal government and is not subject to
copyright in the United States (public domain) - no license restriction, fully
compatible with the project's permissive-only policy.

Known gaps (READ BEFORE RELYING ON COVERAGE)
--------------------------------------------
This source resolves CURRENT tickers only (~60% of the ~1126 historical S&P 500
universe, measured on the cached hanshof parquet). The residual ~40% are
delisted / renamed / merged-acquired firms (FB, BLL, BBT, ANTM, EKDKQ, ...) whose
tickers no longer appear in today's snapshot. Higher coverage requires either:

  * per-CIK mining of the ``dei:TradingSymbol`` XBRL fact from ``companyfacts``
    (carries a company's historical ticker aliases - catches renamed-but-still-
    existing firms like FB->META; does NOT catch truly-delisted/merged firms
    whose CIK is absent from the current snapshot); or
  * a vendored permissive historical ticker<->CIK dataset (none found - every
    GitHub dataset located, e.g. BlackFalconData-org/delisted-stocks-list,
    radikon/ticker-cik-name-lookup, ivan020/ticker-cik-EDGAR_DB, is UNLICENSED
    and rejected per project license policy). ``edgartools`` (MIT) is rejected:
    it resolves tickers from the SAME current ``company_tickers`` snapshot, so it
    adds a heavy dependency with ZERO coverage gain on the historical tail.

Unresolved tickers are simply ABSENT from the result (this function never raises).

Ticker-reuse caveat (entity-mismatch, NOT look-ahead)
-----------------------------------------------------
Ticker strings are occasionally REUSED by a different company after the original
delists (rare for S&P 500, but it happens). Because this resolver maps via the
current snapshot, a reused ticker returns the CURRENT holder's CIK, which may
differ from the historical entity you wanted. This is a wrong-entity risk, not a
look-ahead: CIK is stable and the resolver does not define membership (the
universe comes from PIT ``universe.py``). Flag any ticker whose CIK's current
name disagrees with the known historical company.

PIT / anti-leakage
------------------
Resolution is a STATIC lookup over a fixed snapshot; it introduces no look-ahead.
The set of tickers fundamentals are fetched for is governed by PIT
``universe.py`` membership, NOT by this resolver.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import structlog

from aionis.config import settings
from aionis.ingest.universe import normalize_ticker

log = structlog.get_logger()

_UA = "Aionis research cik-resolver contact@example.com"
_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
_CACHE_NAME = "cik_resolver_tickers.json"


def _cache_dir(cache_dir: Path | None = None) -> Path:
    d = cache_dir or settings.data_dir / "cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


# --- pure parser (testable on a dict, no network) ---


def _parse_sec_tickers(raw: dict) -> dict[str, int]:
    """SEC ``company_tickers.json`` raw ``{idx: {cik_str, ticker, title}}`` ->
    normalized ``{TICKER: CIK}`` (upper-case, share-class separator ``-``).

    ``normalize_ticker`` (reused from ``universe``) canonicalizes ``.``/``/`` ->
    ``-`` so the SEC's ``BRK-B`` / ``BF-B`` and any dotted variants all align with
    the universe's normalized tickers. First CIK wins on a duplicate ticker
    (SEC dedupes; the guard is just defensive).
    """
    out: dict[str, int] = {}
    for v in raw.values():
        if not isinstance(v, dict):
            continue
        t = normalize_ticker(str(v.get("ticker", "")))
        cik = v.get("cik_str")
        if t and cik is not None and t not in out:
            out[t] = int(cik)
    return out


# --- loader (network + cache; not exercised by the hermetic test suite) ---


def _fetch_with_backoff(url: str, retries: int = 4, backoff: int = 2) -> dict:
    """Polite GET -> parsed JSON. >=2s exponential backoff on every retry; the
    snapshot is a single one-time ~1 MB fetch cached forever after."""
    import requests

    last: Exception | None = None
    for attempt in range(retries):
        try:
            r = requests.get(url, headers={"User-Agent": _UA}, timeout=30)
            r.raise_for_status()
            return r.json()
        except Exception as e:  # pragma: no cover - network path
            last = e
            log.warning(
                "cik_resolver_fetch_retry",
                url=url, attempt=attempt + 1, of=retries, error=str(e),
            )
            if attempt < retries - 1:
                time.sleep(backoff * (2**attempt))  # 2s, 4s, 8s
    raise RuntimeError(f"cik_resolver: failed to fetch {url}: {last}")


def _load_sec_ticker_map(
    cache_dir: Path | None = None, force: bool = False,
) -> dict[str, int]:
    """Normalized ``{TICKER: CIK}`` from SEC, cached. Reruns make no HTTP call."""
    fp = _cache_dir(cache_dir) / _CACHE_NAME
    if fp.exists() and not force:
        return json.loads(fp.read_text())
    raw = _fetch_with_backoff(_TICKERS_URL)
    m = _parse_sec_tickers(raw)
    fp.write_text(json.dumps(m))
    log.info("cik_resolver_map_loaded", n=len(m), cache=str(fp))
    return m


def resolve_ciks(
    tickers: list[str], cache_dir: Path | None = None, force: bool = False,
) -> dict[str, int]:
    """Historical ticker -> SEC CIK. Upper-cases input and normalizes share-class
    separators to ``-`` (reuse ``aionis.ingest.universe.normalize_ticker``). Cached.

    Returns ``{TICKER: CIK}`` for as many inputs as resolve; unresolved tickers
    are simply absent (NEVER raises). ``force=True`` bypasses the parse cache.
    See module docstring for the current-snapshot coverage gap and the
    ticker-reuse entity-mismatch caveat.
    """
    cmap = _load_sec_ticker_map(cache_dir, force=force)
    out: dict[str, int] = {}
    for t in tickers:
        nt = normalize_ticker(t)
        if nt in cmap:
            out[nt] = cmap[nt]
    return out


_RAW_CACHE = "cik_resolver_raw.json"


def _load_sec_raw(cache_dir: Path | None = None, force: bool = False) -> dict:
    """Raw SEC ``company_tickers.json`` ``{idx: {cik_str, ticker, title}}``, cached.

    Kept separate from the parsed ticker map so the title field (company name) is
    available for the ticker-reuse entity-mismatch cross-check without re-fetching.
    """
    fp = _cache_dir(cache_dir) / _RAW_CACHE
    if fp.exists() and not force:
        return json.loads(fp.read_text())
    raw = _fetch_with_backoff(_TICKERS_URL)
    fp.write_text(json.dumps(raw))
    log.info("cik_resolver_raw_cached", cache=str(fp))
    return raw


def cik_title_map(cache_dir: Path | None = None, force: bool = False) -> dict[int, str]:
    """``{CIK: company title}`` from the SEC snapshot (the resolved entity's name).

    Used with :func:`aionis.ingest.universe.filter_reuse_mismatches` to drop
    ticker-reuse entity-mismatches (a delisted ticker string later held by a
    different company — the resolver would return the NEW holder's CIK).
    """
    raw = _load_sec_raw(cache_dir, force=force)
    out: dict[int, str] = {}
    for v in raw.values():
        if isinstance(v, dict) and v.get("cik_str") and v.get("title"):
            out[int(v["cik_str"])] = str(v["title"])
    return out


_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"


def cik_name_history(
    cik: int, cache_dir: Path | None = None, force: bool = False,
) -> dict:
    """``{current: str, former: [str]}`` from SEC ``submissions`` (the entity's name
    history). Cached per CIK. The robust stage-2 signal for the ticker-reuse check:
    a renamed company lists its old name in ``formerNames`` (e.g. CNX Resources -> ex
    CONSOL ENERGY); a reused ticker's CIK has no such history (e.g. POM -> PomDoctor,
    never Pepco). One polite submissions fetch per CIK, cached forever after.
    """
    fp = _cache_dir(cache_dir) / f"cik_names_{int(cik):010d}.json"
    if fp.exists() and not force:
        return json.loads(fp.read_text())
    import requests

    r = requests.get(
        _SUBMISSIONS_URL.format(cik=int(cik)),
        headers={"User-Agent": _UA}, timeout=30,
    )
    r.raise_for_status()
    d = r.json()
    out = {
        "current": str(d.get("name", "")),
        "former": [str(f.get("name", "")) for f in d.get("formerNames", [])],
    }
    fp.write_text(json.dumps(out))
    time.sleep(0.15)  # SEC fair-access (matches fundamentals.py)
    return out
