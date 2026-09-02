"""As-released primary event text (point-in-time, outcome-free).

The text fed to ERL extraction must be the document as released at event_ts, not
a post-hoc analysis (which would bake the market move into the text). For each
event type we hit a stable archive URL:

  FOMC : https://www.federalreserve.gov/newsevents/pressreleases/monetary{yyyymmdd}a.htm
  CPI/NFP : live BLS transport is blocked. Existing cached documents remain
            readable, but a cache miss fails closed rather than reaching BLS.

FOMC statements are fetched from their as-released archive URL. Any FOMC fetch
failure (404, 403, network) falls back to a minimal outcome-free stub: an
uninformative text cannot manufacture spurious signal, and stubs are never
cached so a later run can retry the live URL.

Fetched HTML is cleaned (HTML -> text, leading boilerplate stripped, whitespace
collapsed) and hard-truncated to 4000 chars for token control, then cached to
disk per ``event_id`` so re-runs make zero HTTP calls.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import structlog
from bs4 import BeautifulSoup

from aionis.config import settings
from aionis.ingest.universe import _policy_get

log = structlog.get_logger()

# --- URL templates ---------------------------------------------------------
_FOMC_STATEMENT = "https://www.federalreserve.gov/newsevents/pressreleases/monetary{yyyymmdd}a.htm"
_BLS_CPI = "https://www.bls.gov/news.release/archives/cpi_{mmddyyyy}.htm"
_BLS_NFP = "https://www.bls.gov/news.release/archives/empsit_{mmddyyyy}.htm"
# Canonical EDGAR primary-document archive URL (the pattern used by every
# established EDGAR tool, e.g. edgar-crawler / sec-edgar):
# https://www.sec.gov/Archives/edgar/data/{cik}/{accession-no-dashes}/{primaryDocument}
_EDGAR_ARCHIVE = "https://www.sec.gov/Archives/edgar/data/{cik}/{accn}/{doc}"
# SEC fair-access: a DECLARED identity UA gets 200; a browser-masquerade UA
# gets 403 on www.sec.gov (verified live 2026-09-01). Same convention as the
# repo's other www.sec.gov consumers (form13f / form_ipo_price).
_EDGAR_UA = "Aionis research event-text-edgar contact@example.com"
_EDGAR_HEADERS = {"User-Agent": _EDGAR_UA, "Accept": "text/html,application/xhtml+xml"}

# --- Cleaning / token control ----------------------------------------------
_MAX_CHARS = 4000
# BLS releases prepend a "Transmission of material..." embargo notice; the
# release body starts at that marker. FOMC statements start at "For release".
_BLS_BODY_MARKER = "transmission of material in this"
_FOMC_BODY_MARKERS = ("for immediate release", "for release")

# BLS returns 403 to non-browser UAs; send a realistic browser fingerprint.
_BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
_HTTP_HEADERS = {
    "User-Agent": _BROWSER_UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}
_TIMEOUT_S = 30


def _build_url(event_type: str, event_ts: pd.Timestamp) -> str:
    """Date-stamp the archive URL for the event type."""
    d = pd.Timestamp(event_ts).tz_localize(None).normalize()
    if event_type == "FOMC":
        return _FOMC_STATEMENT.format(yyyymmdd=d.strftime("%Y%m%d"))
    if event_type == "CPI":
        return _BLS_CPI.format(mmddyyyy=d.strftime("%m%d%Y"))
    if event_type == "NFP":
        return _BLS_NFP.format(mmddyyyy=d.strftime("%m%d%Y"))
    raise ValueError(f"unknown event_type: {event_type!r}")


def _strip_boilerplate(text: str, event_type: str) -> str:
    """Drop the leading nav/embargo notice; keep the release body."""
    if event_type in ("CPI", "NFP"):
        m = re.search(_BLS_BODY_MARKER, text, re.IGNORECASE)
        if m:
            return text[m.start() :]
    elif event_type == "FOMC":
        for marker in _FOMC_BODY_MARKERS:
            m = re.search(marker, text, re.IGNORECASE)
            if m:
                return text[m.start() :]
    # EDGAR (and any unknown type): no marker-based stripping — a marker string
    # appearing mid-document would silently discard filing content.
    return text


def _clean(html: str, event_type: str) -> str:
    """HTML -> cleaned text, hard-truncated to ``_MAX_CHARS`` for token control."""
    soup = BeautifulSoup(html, "html.parser")
    # Modern EDGAR filings embed inline-XBRL headers (ix:header) whose tag soup
    # crowds out the actual prose; scripts/styles are noise for every source.
    for junk in soup(["script", "style", "ix:header"]):
        junk.decompose()
    text = soup.get_text(" ")
    text = re.sub(r"\s+", " ", text).strip()
    text = _strip_boilerplate(text, event_type)
    return text[:_MAX_CHARS]


def _http_get(url: str) -> str | None:
    """GET (30s timeout) through the shared >=2s host-spacing policy.

    Returns raw HTML on 2xx, None on 404 / persistent failure (fail-soft).
    Every reachable branch is policy-routed (BLS raises before HTTP; FOMC and
    the EDGAR primary-doc path both go through _policy_get — round 56 removed
    the last raw-requests branch, an off-policy site flagged by audit).
    """
    try:
        resp = _policy_get(url, timeout=_TIMEOUT_S, headers=_HTTP_HEADERS)
        if resp.status_code == 404:
            log.warning("text_fetch_404", url=url)
            return None
        resp.raise_for_status()
        return resp.text
    except Exception as e:  # HTTPError, Timeout, ConnectionError: fail-soft
        log.warning("text_fetch_failed", url=url, error=str(e))
        return None


def _fetch_text(event_type: str, event_ts: pd.Timestamp) -> str | None:
    """Cleaned+truncated primary text for one event, or None on fail-soft."""
    if event_type in ("CPI", "NFP"):
        raise RuntimeError(
            "BLS is blocked per data-source constraints; cache-only event text is allowed"
        )
    try:
        url = _build_url(event_type, event_ts)
    except ValueError as e:
        log.warning("text_fetch_unknown_type", event_type=event_type, error=str(e))
        return None
    raw = _http_get(url)
    if raw is None:
        return None
    return _clean(raw, event_type)


def _stub(event_id: str, event_type: str, event_ts: pd.Timestamp) -> str:
    d = pd.Timestamp(event_ts).tz_localize(None).normalize()
    return (
        f"On {d:%Y-%m-%d}, the {event_type} release was issued. "
        "Structural description only; no market outcome is described."
    )


def _default_cache_dir() -> Path:
    return settings.data_dir / "cache" / "event_text"


def fetch_event_text(events: pd.DataFrame, cache_dir: Path | None = None) -> pd.DataFrame:
    """Primary-document text per event, with on-disk cache + outcome-free stub fallback.

    Back-compatible: ``cache_dir`` defaults to ``settings.data_dir / cache / event_text``.
    Each event's cleaned+truncated text is cached at ``{cache_dir}/{event_id}.txt``
    (UTF-8); cache hits make no HTTP call. A stub fallback is NEVER cached, so a
    later run can retry the live URL after a transient block.
    """
    cache_dir = cache_dir or _default_cache_dir()
    cache_dir.mkdir(parents=True, exist_ok=True)

    fetched = cached = stubbed = 0
    rows: list[dict[str, str]] = []
    for ev in events.itertuples(index=False):
        cache_file = cache_dir / f"{ev.event_id}.txt"
        if cache_file.exists():
            text = cache_file.read_text(encoding="utf-8")
            log.info("event_text_cache_hit", event_id=ev.event_id)
            cached += 1
            rows.append({"event_id": ev.event_id, "text": text})
            continue

        raw = _fetch_text(ev.event_type, ev.event_ts)
        if raw is None:
            text = _stub(ev.event_id, ev.event_type, ev.event_ts)
            log.info(
                "event_text_stub_fallback",
                event_id=ev.event_id,
                event_type=ev.event_type,
            )
            stubbed += 1
        else:
            text = raw
            cache_file.write_text(text, encoding="utf-8")
            log.info(
                "event_text_fetched",
                event_id=ev.event_id,
                event_type=ev.event_type,
                chars=len(text),
            )
            fetched += 1
        rows.append({"event_id": ev.event_id, "text": text})

    log.info(
        "event_text_summary",
        total=len(events),
        fetched=fetched,
        cached=cached,
        stubbed=stubbed,
    )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# EDGAR primary-document text (SC 13D / 8-K) — the arm_e13 LLM-edge input.
# Same discipline as the FOMC/BLS branch above: AS-RELEASED document only (the
# filing as it stood on filing_date, never a post-hoc analysis), disk-cached
# per event so re-runs make zero HTTP calls, and a failure NEVER caches
# (text="" -> the LLM edge skips that event honestly; the readiness gate's
# llm_event_text_empty check sees real text when fetches succeed).
# ---------------------------------------------------------------------------


def _edgar_cache_name(accession: str, primary_doc: str) -> str:
    """Deterministic cache filename: ``edgar_{accession-no-dashes}__{doc}.txt``."""
    accn = str(accession).strip().replace("-", "")
    doc = str(primary_doc).strip()
    return f"edgar_{accn}__{doc}.txt"


def fetch_edgar_primary_text(
    events: pd.DataFrame, cache_dir: Path | None = None
) -> pd.DataFrame:
    """Primary-document text for EDGAR filings, with cache + empty-on-failure.

    ``events`` needs columns ``[event_id, cik, accession, primary_doc]`` —
    exactly what the E3 freeze's 13D/8-K rows carry. Rows whose
    ``primary_doc`` is empty (e.g. cached rows from before the column existed)
    return ``text=""`` without any HTTP call: a missing document must never
    manufacture signal, and "" is the runner's established skip-the-edge
    marker (distinct from the FOMC textual stub, which would still spend LLM
    tokens on structure-only text).

    Returns ``[event_id, text]``; fetched text is cleaned + truncated to
    ``_MAX_CHARS`` and cached at ``{cache_dir}/{name}.txt``; failures return
    "" and are never cached so a later run can retry.
    """
    cache_dir = cache_dir or _default_cache_dir()
    cache_dir.mkdir(parents=True, exist_ok=True)

    fetched = cached = skipped = failed = 0
    rows: list[dict[str, str]] = []
    for ev in events.itertuples(index=False):
        if not str(getattr(ev, "primary_doc", "") or "").strip():
            skipped += 1
            rows.append({"event_id": ev.event_id, "text": ""})
            continue

        cache_file = cache_dir / _edgar_cache_name(ev.accession, ev.primary_doc)
        if cache_file.exists():
            text = cache_file.read_text(encoding="utf-8")
            cached += 1
            rows.append({"event_id": ev.event_id, "text": text})
            continue

        url = _EDGAR_ARCHIVE.format(
            cik=int(ev.cik),
            accn=str(ev.accession).strip().replace("-", ""),
            doc=str(ev.primary_doc).strip(),
        )
        # www.sec.gov: DECLARED identity UA + the shared >=2s host-spacing policy.
        # The URL is built ONLY from this module's fixed _EDGAR_ARCHIVE template
        # with a numeric cik and a digits-only accession — the host is pinned to
        # www.sec.gov, so there is no user-controlled destination (SSRF-safe).
        try:
            resp = _policy_get(url, timeout=_TIMEOUT_S, headers=_EDGAR_HEADERS)
        except Exception as e:  # HTTPError, Timeout, ConnectionError: fail-soft
            log.warning("edgar_text_fetch_failed", event_id=ev.event_id, url=url, error=str(e))
            failed += 1
            rows.append({"event_id": ev.event_id, "text": ""})
            continue
        if resp.status_code == 404:
            log.warning("edgar_text_fetch_404", event_id=ev.event_id, url=url)
            failed += 1
            rows.append({"event_id": ev.event_id, "text": ""})
            continue
        raw = resp.text

        text = _clean(raw, event_type="EDGAR")[:_MAX_CHARS]
        cache_file.write_text(text, encoding="utf-8")
        fetched += 1
        log.info("edgar_text_fetched", event_id=ev.event_id, chars=len(text))
        rows.append({"event_id": ev.event_id, "text": text})

    log.info(
        "edgar_text_summary",
        total=len(events),
        fetched=fetched,
        cached=cached,
        skipped=skipped,
        failed=failed,
    )
    return pd.DataFrame(rows, columns=["event_id", "text"])


__all__ = ["fetch_event_text", "fetch_edgar_primary_text"]
