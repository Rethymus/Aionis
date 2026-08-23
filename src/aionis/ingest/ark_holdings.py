"""ARK Invest daily ETF holdings — official CSV ingest (display-only).

Eight ETF "Full Holdings CSV" endpoints on ``assets.ark-funds.com``. The
fund pages are a JS shell (raw HTML has no CSV href), so the URLs were
extracted once via a real browser from each fund page's live DOM
(2026-08-23) and pinned here — link structure = API configuration; the DATA
always comes from ARK's own CSV endpoint. Names carry unguessable
punctuation (``TECH._&_ROBOTICS``); a rename surfaces as a per-fund FAIL
(disclosed, never silent).

ARK publishes one CSV per trading day after close and keeps no history, so
callers persist every dated snapshot they fetch — the cache becomes the
time series. Display lane ONLY: nothing in this module may feed any
research pipeline (anti-leakage constraint on live/current data).
"""
from __future__ import annotations

import csv
import re
import time

import requests

from aionis.ingest.http_policy import HttpRequestPolicy, RetryPolicy

# Browser-verified 2026-08-23 from each fund page's live DOM (see docstring).
FUND_CSV_URLS: dict[str, str] = {
    "ARKK": "https://assets.ark-funds.com/fund-documents/funds-etf-csv/ARK_INNOVATION_ETF_ARKK_HOLDINGS.csv",
    "ARKQ": "https://assets.ark-funds.com/fund-documents/funds-etf-csv/ARK_AUTONOMOUS_TECH._&_ROBOTICS_ETF_ARKQ_HOLDINGS.csv",
    "ARKW": "https://assets.ark-funds.com/fund-documents/funds-etf-csv/ARK_NEXT_GENERATION_INTERNET_ETF_ARKW_HOLDINGS.csv",
    "ARKG": "https://assets.ark-funds.com/fund-documents/funds-etf-csv/ARK_GENOMIC_REVOLUTION_ETF_ARKG_HOLDINGS.csv",
    "ARKF": "https://assets.ark-funds.com/fund-documents/funds-etf-csv/ARK_BLOCKCHAIN_&_FINTECH_INNOVATION_ETF_ARKF_HOLDINGS.csv",
    "ARKX": "https://assets.ark-funds.com/fund-documents/funds-etf-csv/ARK_SPACE_&_DEFENSE_INNOVATION_ETF_ARKX_HOLDINGS.csv",
    "PRNT": "https://assets.ark-funds.com/fund-documents/funds-etf-csv/THE_3D_PRINTING_ETF_PRNT_HOLDINGS.csv",
    "IZRL": "https://assets.ark-funds.com/fund-documents/funds-etf-csv/ARK_ISRAEL_INNOVATIVE_TECHNOLOGY_ETF_IZRL_HOLDINGS.csv",
}

_POLICY = HttpRequestPolicy(retry_exceptions=(requests.RequestException,))
_UA = {"User-Agent": "Aionis-Research/1.0 (educational; contact via repo)"}
_DATE_RE = re.compile(r"\d{2}/\d{2}/\d{4}")


def _get(url: str, total_attempts: int = 3) -> requests.Response:
    retry = RetryPolicy(max_retries=total_attempts - 1, backoff_base=2.0)
    return _POLICY.request(
        url, lambda: requests.get(url, headers=_UA, timeout=30), retry=retry
    )


def _num(value: str | None) -> float:
    """'$1,713,664' / '9.24%' / '' → float (empty → 0.0)."""
    v = (value or "0").replace("$", "").replace(",", "").replace("%", "").strip()
    return float(v) if v else 0.0


def parse_csv(text: str) -> tuple[str, list[dict], int]:
    """Parse one ARK CSV → (as-of ISO date, position rows, skipped-row count).

    Skipped honestly and counted: the trailing DISCLAIMER footer row (the
    whole paragraph lands in the date field) and rows with no ticker
    (warrants/units keep a company name but no symbol — never guessed).
    """
    reader = csv.DictReader(text.splitlines())
    rows: list[dict] = []
    skipped = 0
    as_of = ""
    for raw in reader:
        d = (raw.get("date") or "").strip()
        if not _DATE_RE.fullmatch(d):
            skipped += 1
            continue
        mm, dd, yy = d.split("/")
        as_of = f"{yy}-{mm}-{dd}"
        ticker = (raw.get("ticker") or "").strip()
        if not ticker or ticker == "CASHX":
            skipped += 1
            continue
        rows.append({
            "fund": (raw.get("fund") or "").strip(),
            "company": (raw.get("company") or "").strip(),
            "ticker": ticker,
            "cusip": (raw.get("cusip") or "").strip(),
            "shares": _num(raw.get("shares")),
            "market_value": _num(raw.get("market value ($)")),
            "weight_pct": _num(raw.get("weight (%)")),
        })
    return as_of, rows, skipped


def fetch_all(sleep_s: float = 2.1) -> dict[str, dict]:
    """Fetch every fund CSV politely (≥2s spacing). Per-fund fault isolation.

    Returns ``{tick: {"as_of", "rows", "skipped", "text"}}``; failures come
    back as ``{"error": "..."}`` entries so one broken rename never takes
    the other seven funds down.
    """
    out: dict[str, dict] = {}
    for i, (tick, url) in enumerate(FUND_CSV_URLS.items()):
        if i:
            time.sleep(sleep_s)
        try:
            r = _get(url)
            r.raise_for_status()
            as_of, rows, skipped = parse_csv(r.text)
            if not as_of:
                raise RuntimeError("CSV carried no parseable date column")
            out[tick] = {"as_of": as_of, "rows": rows, "skipped": skipped, "text": r.text}
        except Exception as e:  # noqa: BLE001 — per-fault isolation, disclosed
            out[tick] = {"error": f"{type(e).__name__}: {e}"}
    return out
