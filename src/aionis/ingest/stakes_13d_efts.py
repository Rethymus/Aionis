"""13D self-filing filter via EDGAR full-text search (efts).

Companion to :mod:`aionis.ingest.stakes_13d`. That module's ``filings_13d`` reads
the submissions endpoint, which is ISSUER/filer-side and does NOT expose the
FILER CIK per filing — so it cannot distinguish an external activist stake from a
financial-stock SELF-filing (banks / brokers / asset managers file ``SC 13D`` on
their OWN stock for trust / custody / preferred-share structures — see
``docs/phase-d-preregistration.md`` §0.5; BAC, WFC, JPM, GS dominate the raw
counts). This module discovers every ``SC 13D`` filing that NAMES a given issuer
CIK via EDGAR's full-text search, resolves the filer CIK per hit, and drops
self-filings (``filer_cik == issuer_cik``).

VERIFIED efts query (2026-07-29 live probe; do not re-derive)::

    https://efts.sec.gov/LATEST/search-index?q=&ciks={cik:010d}&forms=SC%2013D
        &dateRange=custom&startdt={start}&enddt={end}&from={n}

  * ``ciks=`` MUST be the 10-digit zero-padded CIK; it matches the SUBJECT
    (issuer) company — a filing naming the issuer is returned whether the issuer
    is the filer or the subject. A plain 7-digit CIK returns 0 hits.
  * ``forms=SC 13D`` is the ROOT form and expands to BOTH ``SC 13D`` and
    ``SC 13D/A`` (probe: 9 originals + 59 amendments for BAC 2024). Do NOT pass
    the comma list ``SC 13D,SC 13D/A`` — efts mis-parses it and returns only the
    amendments (a strict subset that drops every original).
  * ``dateRange=custom`` + ``startdt`` / ``enddt`` (YYYY-MM-DD) bound the window.
  * response: ``hits.hits[]._source`` carries ``ciks`` (the named entities),
    ``adsh`` (accession), ``file_date``, ``form``, ``display_names``. Default page
    size is 100; paginate with ``from=`` for issuers with >100 hits (verified:
    BAC 2016–2024 = 287 total, fully recovered across from=0/100/200).

FILER IDENTIFICATION: ``_source.ciks[]`` lists the named entities but its ORDER
is NOT a reliable filer/subject signal (probe: CACC had the issuer at index 0,
BAC at index 1). The accession prefix is a FILING AGENT (e.g. EDGARFILINGS LTD,
Toppan Merrill/FA — ``entityType='other'``), NOT the reporting person, so it is
unusable as the filer. Because we QUERY by the issuer CIK, the issuer is known;
the filer is therefore the first named CIK that is NOT the issuer. A filing whose
only distinct named CIK is the issuer is a SELF-filing and is dropped by
:func:`filter_external_13d`.

SEC EDGAR public domain (17 U.S.C. §105) — G1✓ (permissive license). PIT via
``file_date`` — G2✓ (filed-date, the same vintage discipline as
:mod:`aionis.ingest.fundamentals`); immutable (``SC 13D/A`` amendments are NEW
filings with new accession numbers, never silent overwrites) — G3✓ (strictly
cleaner than ALFRED/EPU). The assembled hit list is cached per
(issuer, start, end) so reruns make no HTTP call.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import pandas as pd
import structlog

from aionis.config import settings

log = structlog.get_logger()

_UA = "Aionis research 13d-efts contact@example.com"
_EFTS_URL = "https://efts.sec.gov/LATEST/search-index"
_13D_ROOT_FORM = "SC 13D"  # root form; efts expands to SC 13D + SC 13D/A (NOT the comma list)
_PAGE_SIZE = 100  # efts default + max per request; paginate via from= beyond this


def _cache_dir(cache_dir: Path | None = None) -> Path:
    d = cache_dir or settings.data_dir / "cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _efts_url(issuer_cik: int, start: str, end: str, from_: int) -> str:
    """One efts page URL for the given issuer + window + page offset.

    ``forms`` uses the root form ``SC 13D`` (expands to ``SC 13D/A``); the CIK is
    10-digit zero-padded (a plain CIK returns 0 hits). Exposed for tests."""
    return (
        f"{_EFTS_URL}?q=&ciks={int(issuer_cik):010d}"
        f"&forms={_13D_ROOT_FORM.replace(' ', '%20')}"
        f"&dateRange=custom&startdt={start}&enddt={end}&from={from_}"
    )


def _efts_cache_path(issuer_cik: int, start: str, end: str, cache_dir: Path | None) -> Path:
    return _cache_dir(cache_dir) / f"efts_13d_{int(issuer_cik):010d}_{start}_{end}.json"


def _get_json(url: str, fp: Path | None = None, *, retries: int = 4, backoff: int = 4) -> dict:
    """Fetch ``url`` -> JSON. If ``fp`` is given and exists, return cached (no
    call). Exp-backoff retries on TRANSIENT failures only (SEC drops connections
    under burst -> ``SSL: UNEXPECTED_EOF_WHILE_READING``; 5xx / 429 rate-limit).
    A PERMANENT 4xx (bad CIK / URL — e.g. 404) fails fast without retrying.
    Mirrors :func:`aionis.ingest.stakes_13d._get_json`; ``fp=None`` skips the
    per-call file cache (efts pages are cached as one assembled hit list instead)."""
    import requests

    if fp is not None and fp.exists():
        return json.loads(fp.read_text())
    last: Exception | None = None
    for attempt in range(retries):
        try:
            r = requests.get(url, headers={"User-Agent": _UA}, timeout=60)
        except Exception as e:  # network / SSL / timeout -> backoff and retry
            last = e
            log.warning("efts_retry", url=url, attempt=attempt + 1,
                        of=retries, error=str(e))
            if attempt < retries - 1:
                time.sleep(backoff * (attempt + 1))
            continue
        # permanent client error (bad CIK / URL) -> fail fast, do NOT retry
        if 400 <= r.status_code < 500 and r.status_code != 429:
            raise RuntimeError(
                f"{r.status_code} Client Error for {url} (permanent; not retried)"
            )
        if r.status_code != 200:  # 5xx / 429 -> backoff and retry
            last = RuntimeError(f"{r.status_code} for {url}")
            log.warning("efts_retry", url=url, attempt=attempt + 1,
                        of=retries, error=str(last))
            if attempt < retries - 1:
                time.sleep(backoff * (attempt + 1))
            continue
        data = r.json()
        if fp is not None:
            fp.write_text(json.dumps(data))
        time.sleep(0.15)  # SEC fair-access: <=10 req/s
        return data
    raise RuntimeError(f"fetch failed for {url} after {retries} retries: {last}")


def _fetch_efts_hits(
    issuer_cik: int, start: str, end: str, cache_dir: Path | None = None,
    *, retries: int = 4, backoff: int = 4,
) -> list[dict]:
    """Every ``_source`` for SC 13D filings naming ``issuer_cik`` in [start, end],
    paginated across ``from=`` pages and cached as one assembled list."""
    fp = _efts_cache_path(issuer_cik, start, end, cache_dir)
    if fp.exists():
        return json.loads(fp.read_text())
    out: list[dict] = []
    from_ = 0
    while True:
        data = _get_json(_efts_url(issuer_cik, start, end, from_), retries=retries, backoff=backoff)
        hits = data.get("hits", {})
        batch = [h.get("_source", {}) for h in hits.get("hits", [])]
        out.extend(batch)
        total_node = hits.get("total", 0)
        total = total_node.get("value", 0) if isinstance(total_node, dict) else total_node
        if len(batch) < _PAGE_SIZE or len(out) >= total:
            break
        from_ += _PAGE_SIZE
    fp.write_text(json.dumps(out))
    return out


def _filer_cik(source: dict, issuer_cik: int) -> int:
    """The filer CIK for one efts hit. ``ciks[]`` order is NOT a reliable
    filer/subject signal, so the filer is the first named CIK that is NOT the
    issuer; if every named CIK is the issuer (or none is named), the filing is a
    self-filing and the issuer is returned so :func:`filter_external_13d` drops it."""
    for c in source.get("ciks") or []:
        try:
            if int(str(c)) != int(issuer_cik):
                return int(str(c))
        except (ValueError, TypeError):
            continue
    return int(issuer_cik)


def fetch_13d_filings_with_filer(
    issuer_cik: int, *, start: str, end: str, cache_dir: Path | None = None,
) -> pd.DataFrame:
    """All SC 13D / 13D/A filings naming ``issuer_cik`` in [start, end], with the
    filer CIK resolved per filing.

    Returns ``[issuer_cik, filer_cik, filing_date, accession, form]`` sorted by
    ``filing_date``. PIT anchor is ``filing_date`` (immutable; the consumer aligns
    via backward-as-of, mirroring :func:`aionis.ingest.fundamentals.pit_align`).

    .. note:: NOT yet self-filing-filtered — call :func:`filter_external_13d`
       (or :func:`external_13d_events`) to drop ``filer_cik == issuer_cik`` rows.
    """
    hits = _fetch_efts_hits(issuer_cik, start, end, cache_dir)
    rows: list[dict] = []
    for s in hits:
        d = str(s.get("file_date", ""))
        if not d:
            continue
        # efts dateRange already bounds the window; this is defense-in-depth
        if start and d < start:
            continue
        if end and d > end:
            continue
        rows.append({
            "issuer_cik": int(issuer_cik),
            "filer_cik": _filer_cik(s, issuer_cik),
            "filing_date": d,
            "accession": str(s.get("adsh", "")),
            "form": str(s.get("form", "")),
        })
    df = pd.DataFrame(
        rows, columns=["issuer_cik", "filer_cik", "filing_date", "accession", "form"],
    )
    if df.empty:
        return df
    df["filing_date"] = pd.to_datetime(df["filing_date"]).dt.normalize()
    return df.sort_values("filing_date").reset_index(drop=True)


def filter_external_13d(df: pd.DataFrame) -> pd.DataFrame:
    """Drop self-filings: rows where ``filer_cik == issuer_cik`` (banks / brokers
    file ``SC 13D`` on their own stock). Returns a NEW frame; never mutates input."""
    if df.empty:
        return df.copy()
    mask = df["filer_cik"] != df["issuer_cik"]
    return df[mask].reset_index(drop=True)


def external_13d_events(
    issuer_cik: int, *, start: str, end: str, cache_dir: Path | None = None,
) -> pd.DataFrame:
    """Fetch + filter in one call: external (non-self) SC 13D events naming
    ``issuer_cik`` in [start, end]. Convenience over
    :func:`fetch_13d_filings_with_filer` + :func:`filter_external_13d`."""
    raw = fetch_13d_filings_with_filer(issuer_cik, start=start, end=end, cache_dir=cache_dir)
    return filter_external_13d(raw)
