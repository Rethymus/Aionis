"""Form 4 insider-trading filings via EDGAR full-text search (efts).

Mirror of :mod:`aionis.ingest.stakes_13d_efts` for Form 4 filings. Form 4 captures
insider trading transactions (buy/sell by officers, directors, and 10% owners).

VERIFIED efts query (2026-08-06)::

    https://efts.sec.gov/LATEST/search-index?q=&ciks={cik:010d}&forms=4
        &dateRange=custom&startdt={start}&enddt={end}&from={n}

  * ``ciks=`` MUST be the 10-digit zero-padded CIK (issuer company).
  * ``forms=4`` matches BOTH Form 4 and Form 4/A (amendments).
  * ``dateRange=custom`` + ``startdt`` / ``enddt`` (YYYY-MM-DD) bound the window.
  * response: ``hits.hits[]._source`` carries ``ciks``, ``adsh`` (accession),
    ``file_date``, ``form``, ``display_names``, ``display_symbols``.

SEC EDGAR public domain (17 U.S.C. §105) — G1✓ (permissive license). PIT via
``file_date`` — G2✓ (filed-date, same vintage discipline as fundamentals);
immutable (Form 4/A amendments are NEW filings with new accession numbers, never
silent overwrites) — G3✓. Cached per (issuer, start, end) so reruns make no HTTP.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import structlog

from aionis.config import settings
from aionis.ingest.http_policy import HTTPStatusError
from aionis.ingest.universe import _policy_get

log = structlog.get_logger()

_UA = "Aionis research form4-efts contact@example.com"
_EFTS_URL = "https://efts.sec.gov/LATEST/search-index"
_FORM4_ROOT_FORM = "4"  # root form; efts expands to 4 + 4/A
_PAGE_SIZE = 100  # efts default + max per request; paginate via from=


def _cache_dir(cache_dir: Path | None = None) -> Path:
    d = cache_dir or settings.data_dir / "cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _efts_url(issuer_cik: int, start: str, end: str, from_: int) -> str:
    """One efts page URL for the given issuer + window + page offset.

    ``forms`` uses the root form ``4`` (expands to ``4/A``); the CIK is
    10-digit zero-padded. Exposed for tests."""
    return (
        f"{_EFTS_URL}?q=&ciks={int(issuer_cik):010d}"
        f"&forms={_FORM4_ROOT_FORM}"
        f"&dateRange=custom&startdt={start}&enddt={end}&from={from_}"
    )


def _efts_cache_path(issuer_cik: int, start: str, end: str, cache_dir: Path | None) -> Path:
    return _cache_dir(cache_dir) / f"efts_form4_{int(issuer_cik):010d}_{start}_{end}.json"


def _get_json(url: str, fp: Path | None = None, *, retries: int = 4, backoff: int = 4) -> dict:
    """Fetch ``url`` -> JSON. If ``fp`` is given and exists, return cached (no
    call). Exp-backoff retries on TRANSIENT failures only (SEC drops connections
    under burst -> ``SSL: UNEXPECTED_EOF_WHILE_READING``; 5xx / 429 rate-limit).
    A PERMANENT 4xx (bad CIK / URL — e.g. 404) fails fast without retrying."""
    if fp is not None and fp.exists():
        return json.loads(fp.read_text())
    try:
        r = _policy_get(
            url,
            total_attempts=retries,
            backoff_base=backoff,
            backoff_mode="linear",
            headers={"User-Agent": _UA},
            timeout=60,
        )
    except HTTPStatusError as exc:
        if 400 <= exc.status_code < 500 and exc.status_code != 429:
            raise RuntimeError(
                f"{exc.status_code} Client Error for {url} (permanent; not retried)"
            ) from exc
        raise RuntimeError(f"fetch failed for {url}: {exc}") from exc
    except Exception as exc:
        raise RuntimeError(f"fetch failed for {url}: {exc}") from exc
    data = r.json()
    if fp is not None:
        fp.write_text(json.dumps(data))
    return data


def _fetch_efts_hits(
    issuer_cik: int, start: str, end: str, cache_dir: Path | None = None,
    *, retries: int = 4, backoff: int = 4,
) -> list[dict]:
    """Every ``_source`` for Form 4 filings naming ``issuer_cik`` in [start, end],
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


def fetch_form4_filings(
    issuer_cik: int, *, start: str, end: str, cache_dir: Path | None = None,
) -> pd.DataFrame:
    """All Form 4 / 4/A filings naming ``issuer_cik`` in [start, end].

    Returns ``[issuer_cik, filing_date, accession, form]`` sorted by
    ``filing_date``. PIT anchor is ``filing_date`` (immutable).

    This is the EFTS metadata only — full transaction details (shares, price,
    buy/sell) are parsed from the filing XML by :mod:`aionis.ingest.form4`.
    """
    hits = _fetch_efts_hits(issuer_cik, start, end, cache_dir)
    rows: list[dict] = []
    for s in hits:
        d = str(s.get("file_date", ""))
        if not d:
            continue
        if start and d < start:
            continue
        if end and d > end:
            continue
        rows.append({
            "issuer_cik": int(issuer_cik),
            "filing_date": d,
            "accession": str(s.get("adsh", "")),
            "form": str(s.get("form", "")),
        })
    df = pd.DataFrame(
        rows, columns=["issuer_cik", "filing_date", "accession", "form"],
    )
    if df.empty:
        return df
    df["filing_date"] = pd.to_datetime(df["filing_date"]).dt.normalize()
    return df.sort_values("filing_date").reset_index(drop=True)
