"""Form 4 XML-fetch orchestrator — bridges ``form4_efts`` (metadata) and ``form4`` (parser).

Given an accession returned by EFTS, fetch the filing's Form 4 document XML from
EDGAR Archives and parse it into transactions. Reuses the politeness-bound HTTP
policy (≥2s host spacing) and the idempotent disk-cache pattern from
:mod:`aionis.ingest.form4_efts` — no new HTTP client.

SEC EDGAR public domain (17 U.S.C. §105); filed-date PIT; immutable; ≥2s polite.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import structlog

from aionis.ingest.form4 import form4_filings_to_dataframe, parse_form4_xml
from aionis.ingest.form4_efts import _UA, _cache_dir, _policy_get, fetch_form4_filings

log = structlog.get_logger()

_ARCHIVE_BASE = "https://www.sec.gov/Archives/edgar/data"


def accession_to_no_dash(accession: str) -> str:
    """``"0001234567-25-000001"`` -> ``"000123456725000001"``."""
    return accession.replace("-", "")


def accession_to_index_url(issuer_cik: int, accession: str) -> str:
    """EDGAR Archives filing ``index.json`` URL for (issuer_cik, accession)."""
    return f"{_ARCHIVE_BASE}/{int(issuer_cik)}/{accession_to_no_dash(accession)}/index.json"


def _xml_cache_path(issuer_cik: int, accession: str, cache_dir: Path | None) -> Path:
    no_dash = accession_to_no_dash(accession)
    return _cache_dir(cache_dir) / f"form4_xml_{int(issuer_cik):010d}_{no_dash}.xml"


def _index_cache_path(issuer_cik: int, accession: str, cache_dir: Path | None) -> Path:
    no_dash = accession_to_no_dash(accession)
    return _cache_dir(cache_dir) / f"form4_index_{int(issuer_cik):010d}_{no_dash}.json"


def _pick_form4_doc(index_json: dict, accession: str) -> str | None:
    """Pick the Form 4 document filename from a filing ``index.json``.

    Robust to two SEC schemas: ``directory.item[]`` (current) and top-level
    ``items[]``. Prefers an ``.xml`` doc, else the accession's own ``.txt``,
    else the first non-index file. Returns ``None`` if nothing usable.
    """
    items: list[dict] = []
    directory = index_json.get("directory") if isinstance(index_json, dict) else None
    if isinstance(directory, dict):
        raw = directory.get("item", [])
        items = raw if isinstance(raw, list) else [raw]
    elif isinstance(index_json, dict) and isinstance(index_json.get("items"), list):
        items = index_json["items"]

    names = [str(it.get("name", "")) for it in items if isinstance(it, dict)]
    if not names:
        return None

    no_dash = accession_to_no_dash(accession)
    xml = next((n for n in names if n.lower().endswith(".xml")), None)
    if xml:
        return xml
    acc_txt = next(
        (n for n in names if no_dash in n and n.lower().endswith(".txt")), None
    )
    if acc_txt:
        return acc_txt
    return next(
        (n for n in names if n.lower().endswith((".xml", ".txt")) and "index" not in n.lower()),
        None,
    )


def _doc_url(issuer_cik: int, accession: str, filename: str) -> str:
    return f"{_ARCHIVE_BASE}/{int(issuer_cik)}/{accession_to_no_dash(accession)}/{filename}"


def fetch_form4_xml(
    issuer_cik: int, accession: str, cache_dir: Path | None = None
) -> str:
    """Fetch the Form 4 document XML for ``(issuer_cik, accession)``.

    Idempotent: a cached XML (or index) is reused with no HTTP call. Goes through
    ``_policy_get`` (≥2s host spacing, exp-backoff). Returns ``""`` if the index
    lists no usable Form 4 document.
    """
    xml_fp = _xml_cache_path(issuer_cik, accession, cache_dir)
    if xml_fp.exists():
        return xml_fp.read_text()

    idx_fp = _index_cache_path(issuer_cik, accession, cache_dir)
    if idx_fp.exists():
        idx = json.loads(idx_fp.read_text())
    else:
        resp = _policy_get(
            accession_to_index_url(issuer_cik, accession),
            total_attempts=4,
            backoff_base=4,
            backoff_mode="linear",
            headers={"User-Agent": _UA},
            timeout=60,
        )
        idx = resp.json()
        idx_fp.write_text(json.dumps(idx))

    doc = _pick_form4_doc(idx, accession)
    if not doc:
        log.warning("form4_no_doc_in_index", issuer_cik=issuer_cik, accession=accession)
        return ""

    text = _policy_get(
        _doc_url(issuer_cik, accession, doc),
        total_attempts=4,
        backoff_base=4,
        backoff_mode="linear",
        headers={"User-Agent": _UA},
        timeout=60,
    ).text
    xml_fp.write_text(text)
    return text


def parse_form4_filing(
    issuer_cik: int, accession: str, cache_dir: Path | None = None
) -> pd.DataFrame:
    """Fetch + parse one Form 4 filing into a tidy transaction DataFrame."""
    xml_text = fetch_form4_xml(issuer_cik, accession, cache_dir)
    return form4_filings_to_dataframe(parse_form4_xml(xml_text))


def fetch_form4_transactions(
    issuer_cik: int, *, start: str, end: str, cache_dir: Path | None = None
) -> pd.DataFrame:
    """All Form 4 transactions for ``issuer_cik`` in [start, end].

    EFTS metadata -> per-accession fetch+parse (polite spacing, idempotent) ->
    concatenated tidy DataFrame. Failures per accession are logged and skipped
    (one bad filing does not abort the batch).

    Returns columns: ``[filer_cik, filer_name, ticker, transaction_date,
    buy_or_sell, shares, price_per_share, accession, filing_date]`` where
    ``filing_date`` is the SEC filing date from EFTS (PIT anchor) and
    ``transaction_date`` is the trade date from the Form 4 XML.
    """
    meta = fetch_form4_filings(issuer_cik, start=start, end=end, cache_dir=cache_dir)
    if meta.empty:
        return pd.DataFrame(
            columns=[
                "filer_cik", "filer_name", "ticker", "transaction_date",
                "buy_or_sell", "shares", "price_per_share", "accession",
                "filing_date",
            ]
        )

    frames: list[pd.DataFrame] = []
    for _, row in meta.iterrows():
        accession = str(row["accession"])
        filing_date = row["filing_date"]  # Preserve EFTS filing_date for incremental fetch
        try:
            df = parse_form4_filing(int(issuer_cik), accession, cache_dir=cache_dir)
        except Exception as exc:  # noqa: BLE001 — batch must survive one bad filing
            log.warning("form4_parse_failed", accession=accession, error=str(exc))
            continue
        if not df.empty:
            df["accession"] = accession
            df["filing_date"] = filing_date  # Add filing_date from EFTS
            frames.append(df)

    if not frames:
        return pd.DataFrame()
    out = pd.concat(frames, ignore_index=True)
    return out.sort_values("filing_date").reset_index(drop=True)
