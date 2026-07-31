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
import requests
import structlog
from bs4 import BeautifulSoup

from aionis.config import settings
from aionis.ingest.universe import _policy_get

log = structlog.get_logger()

# --- URL templates ---------------------------------------------------------
_FOMC_STATEMENT = "https://www.federalreserve.gov/newsevents/pressreleases/monetary{yyyymmdd}a.htm"
_BLS_CPI = "https://www.bls.gov/news.release/archives/cpi_{mmddyyyy}.htm"
_BLS_NFP = "https://www.bls.gov/news.release/archives/empsit_{mmddyyyy}.htm"

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
    else:  # FOMC
        for marker in _FOMC_BODY_MARKERS:
            m = re.search(marker, text, re.IGNORECASE)
            if m:
                return text[m.start() :]
    return text


def _clean(html: str, event_type: str) -> str:
    """HTML -> cleaned text, hard-truncated to ``_MAX_CHARS`` for token control."""
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ")
    text = re.sub(r"\s+", " ", text).strip()
    text = _strip_boilerplate(text, event_type)
    return text[:_MAX_CHARS]


def _http_get(url: str, *, use_policy: bool = False) -> str | None:
    """GET with browser UA + 30s timeout; one retry on connection errors.

    Returns raw HTML on 2xx, None on 404 / persistent failure (fail-soft).
    """
    attempts = (1,) if use_policy else (1, 2)
    for attempt in attempts:
        try:
            if use_policy:
                resp = _policy_get(url, timeout=_TIMEOUT_S, headers=_HTTP_HEADERS)
            else:
                resp = requests.get(url, timeout=_TIMEOUT_S, headers=_HTTP_HEADERS)
            if resp.status_code == 404:
                log.warning("text_fetch_404", url=url)
                return None
            resp.raise_for_status()
            return resp.text
        except requests.exceptions.ConnectionError as e:
            # Transient host issues (rate-limit, TCP reset): one retry.
            if not use_policy and attempt == 1:
                continue
            log.warning("text_fetch_conn_error", url=url, error=str(e))
            return None
        except Exception as e:  # HTTPError, Timeout, SSLError, etc.
            log.warning("text_fetch_failed", url=url, error=str(e))
            return None
    return None  # pragma: no cover - every loop path returns


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
    raw = _http_get(url, use_policy=event_type == "FOMC")
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
