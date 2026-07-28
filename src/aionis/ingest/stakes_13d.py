"""Point-in-time 13D activist-stake filings + SIC code (SEC EDGAR submissions).

The TCR WRL.Relationship layer (Phase D): an SC 13D filing is the canonical
"ownership-edge event" — an external filer crossing 5%+ of an issuer. This module
captures the FILING-DATE-anchored 13D event stream per issuer (PIT via
``filing_date``, the same vintage discipline as :mod:`aionis.ingest.fundamentals`).
It also exposes the issuer's SIC code (free from the same submissions pull) for
the sector-peer feature.

SEC EDGAR public domain (17 U.S.C. §105); filed-date PIT; immutable (amendments
``SC 13D/A`` are NEW filings with new accession numbers, never silent overwrites)
— the cleanest possible G3 surface (strictly better than ALFRED/EPU). Cached as
``submissions_{cik}.json`` so reruns make no HTTP call.

KNOWN REFINEMENT (phase-d-preregistration §0.5): the submissions endpoint is
issuer-side and does NOT expose the filer CIK per filing, so the self-filing
over-count (banks / brokers file ``SC 13D`` on their OWN stock for trust / custody
/ preferred-share structures — BAC, WFC, JPM, GS dominate the raw counts) is NOT
yet filtered here. The ``filer != issuer`` filter (via the EFTS ``ciks[]`` field
or cover-page parsing) is a REQUIRED refinement before this feeds a confirmatory
feature; :func:`filings_13d` returns the raw event stream and documents this.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import pandas as pd
import structlog

from aionis.config import settings

log = structlog.get_logger()

_UA = "Aionis research 13D-ingest contact@example.com"
_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
_BLOCK_URL = "https://data.sec.gov/submissions/{name}"
_13D_FORMS = ("SC 13D", "SC 13D/A")  # activist stakes + amendments (NOT 13G passive)


def _cache_dir(cache_dir: Path | None = None) -> Path:
    d = cache_dir or settings.data_dir / "cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _get_json(url: str, fp: Path, *, retries: int = 4, backoff: int = 4) -> dict:
    """Fetch ``url`` -> cache at ``fp`` (cache hit makes no call), with exp-backoff
    retries on TRANSIENT failures only (SEC drops connections under burst ->
    ``SSL: UNEXPECTED_EOF_WHILE_READING``; 5xx / 429 rate-limit). A PERMANENT 4xx
    (bad CIK / URL — e.g. a 404 on an invalid CIK) fails fast without retrying,
    matching the fundamentals.py polite pattern but not wasting 4 backoffs on a
    permanent client error."""
    import requests

    if fp.exists():
        return json.loads(fp.read_text())
    last: Exception | None = None
    for attempt in range(retries):
        try:
            r = requests.get(url, headers={"User-Agent": _UA}, timeout=60)
        except Exception as e:  # network / SSL / timeout -> backoff and retry
            last = e
            log.warning("submissions_retry", url=url, attempt=attempt + 1,
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
            log.warning("submissions_retry", url=url, attempt=attempt + 1,
                        of=retries, error=str(last))
            if attempt < retries - 1:
                time.sleep(backoff * (attempt + 1))
            continue
        data = r.json()
        fp.write_text(json.dumps(data))
        time.sleep(0.15)  # SEC fair-access: <=10 req/s
        return data
    raise RuntimeError(f"fetch failed for {url} after {retries} retries: {last}")


def fetch_submissions(
    cik: int, cache_dir: Path | None = None, *, retries: int = 4, backoff: int = 4,
) -> dict:
    """Full submissions JSON for one issuer CIK (the filings index + SIC), cached.

    The top-level response carries ``filings.recent`` (the latest ~1000 filings as
    parallel arrays) and ``filings.files`` (archive-block filenames covering ALL
    older filings). :func:`filings_13d` paginates the blocks for full history."""
    fp = _cache_dir(cache_dir) / f"submissions_{cik:010d}.json"
    return _get_json(_SUBMISSIONS_URL.format(cik=cik), fp, retries=retries, backoff=backoff)


def _fetch_block(
    cik: int, name: str, cache_dir: Path | None = None,
) -> dict:
    """One archive block (older filings parallel arrays), cached per (cik, block)."""
    fp = _cache_dir(cache_dir) / f"submissions_{cik:010d}_{name}"
    return _get_json(_BLOCK_URL.format(name=name), fp)


def sic_for_cik(cik: int, cache_dir: Path | None = None) -> tuple[str, str]:
    """ ``(sic, sicDescription)`` for an issuer — free from the submissions pull
    (the sector-peer feature rides the same fetch as the 13D stream)."""
    sub = fetch_submissions(cik, cache_dir)
    return str(sub.get("sic", "")), str(sub.get("sicDescription", ""))


def _block_in_range(block: dict, start: str | None, end: str | None) -> bool:
    """Does this archive block's [from, to] overlap [start, end]? Skip blocks that
    cannot contain a wanted filing (avoids fetching the whole archive)."""
    b_from = str(block.get("from", ""))
    b_to = str(block.get("to", ""))
    if start and b_to and b_to < start:
        return False
    if end and b_from and b_from > end:
        return False
    return True


def _slice_filings(arrays: dict, start: str | None, end: str | None) -> list[dict]:
    """Parallel-arrays block -> rows of 13D filings within [start, end]."""
    forms = arrays.get("form", [])
    accns = arrays.get("accessionNumber", [])
    dates = arrays.get("filingDate", [])
    docs = arrays.get("primaryDocument", [])
    out = []
    for i, form in enumerate(forms):
        if form not in _13D_FORMS:
            continue
        d = str(dates[i]) if i < len(dates) else ""
        if start and d and d < start:
            continue
        if end and d and d > end:
            continue
        out.append({
            "form": form,
            "filing_date": d,
            "accession": str(accns[i]) if i < len(accns) else "",
            "primary_doc": str(docs[i]) if i < len(docs) else "",
        })
    return out


def filings_13d(
    cik: int, *, start: str | None = None, end: str | None = None,
    cache_dir: Path | None = None,
) -> pd.DataFrame:
    """All SC 13D / 13D/A filings for an issuer within [start, end], as-filed.

    Returns ``[form, filing_date, accession, primary_doc]`` sorted by filing_date,
    paginated across ``filings.recent`` + every overlapping ``filings.files``
    archive block (so heavy filers whose recent slice is exhausted are covered).
    PIT anchor is ``filing_date`` (immutable; the consumer aligns via
    backward-as-of, mirroring :func:`aionis.ingest.fundamentals.pit_align`).

    .. note:: NOT yet self-filing-filtered — banks file SC 13D on their own stock
       (trust/custody); see the module docstring + pre-reg §0.5. Filter before
       any confirmatory use.
    """
    sub = fetch_submissions(cik, cache_dir)
    filings = sub.get("filings", {})
    rows = list(_slice_filings(filings.get("recent", {}), start, end))

    for block in filings.get("files", []):
        if not _block_in_range(block, start, end):
            continue
        try:
            arrays = _fetch_block(cik, block["name"], cache_dir)
        except Exception as e:  # noqa: BLE001 — a missing block must not abort the issuer
            log.warning("submissions_block_skip", cik=cik, block=block.get("name"), error=str(e))
            continue
        rows.extend(_slice_filings(arrays, start, end))

    df = pd.DataFrame(rows, columns=["form", "filing_date", "accession", "primary_doc"])
    if df.empty:
        return df
    df["filing_date"] = pd.to_datetime(df["filing_date"]).dt.normalize()
    return df.sort_values("filing_date").reset_index(drop=True)
