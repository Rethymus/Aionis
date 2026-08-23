"""Theme-ETF daily holdings — issuer-official CSV ingest (display-only).

Ten thematic ETFs across two issuers, both publishing their FULL daily
holdings as free official files on their own sites (no key, no login):

- **iShares / BlackRock** — one stable direct CSV endpoint per product page
  (``.../<product-id>/<slug>/latest-holdings.csv``; endpoint verified live
  2026-08-23 by downloading each file). Column order differs slightly per
  fund (ICLN carries an extra ``Type`` column), so rows are parsed BY NAME,
  never by position.
- **Global X (Mirae Asset)** — each fund page (server-rendered WordPress)
  links a DATED full-holdings CSV on ``assets.globalxetfs.com``
  (``<slug>_full-holdings_YYYYMMDD.csv``). The date lives in the filename,
  so the ingest fetches the fund page first and extracts the current href
  from its own HTML — link structure = API configuration; the DATA always
  comes from Global X's own file host. A missing link on a renamed page is
  an honest per-fund failure, never a silent gap.

Selection honesty: candidates WITHOUT a reachable free official file were
dropped and recorded in ``docs/data-intake-etf-holdings.md`` (Amplify BLOK
JS-only holdings table; Invesco's redesigned SPA; VanEck unreachable;
First Trust unreachable; SPDR XLS-only with no openpyxl in the pinned
venv). Both issuers keep no CSV history — callers persist every dated
snapshot they fetch. Display lane ONLY: nothing here may feed any research
pipeline (anti-leakage constraint on live/current data).
"""
from __future__ import annotations

import csv
import re
import time
from datetime import datetime

import requests

from aionis.ingest.http_policy import HttpRequestPolicy, RetryPolicy

# Each entry: issuer + official fund name (for display), a parser tag, and
# either a direct file URL (iShares) or the fund page whose HTML carries the
# dated CSV href (Global X). All URLs verified live 2026-08-23.
FUND_DEFS: dict[str, dict[str, str]] = {
    # --- iShares (BlackRock): stable direct latest-holdings.csv -----------
    "SOXX": {
        "issuer": "iShares (BlackRock)",
        "fund": "iShares Semiconductor ETF",
        "url": "https://www.ishares.com/us/products/239705/ishares-semiconductor-etf/latest-holdings.csv",
        "parser": "ishares",
    },
    "ICLN": {
        "issuer": "iShares (BlackRock)",
        "fund": "iShares Global Clean Energy ETF",
        "url": "https://www.ishares.com/us/products/239738/ishares-global-clean-energy-etf/latest-holdings.csv",
        "parser": "ishares",
    },
    "ARTY": {
        "issuer": "iShares (BlackRock)",
        "fund": "iShares Future AI & Tech ETF",
        "url": "https://www.ishares.com/us/products/297905/ishares-future-ai-tech-etf/latest-holdings.csv",
        "parser": "ishares",
    },
    "BAI": {
        "issuer": "iShares (BlackRock)",
        "fund": "iShares A.I. Innovation and Tech Active ETF",
        "url": "https://www.ishares.com/us/products/339081/ishares-a-i-innovation-and-tech-active-etf/latest-holdings.csv",
        "parser": "ishares",
    },
    # --- Global X (Mirae Asset): dated CSV href on each fund page ---------
    "AIQ": {
        "issuer": "Global X (Mirae Asset)",
        "fund": "Global X Artificial Intelligence & Technology ETF",
        "page": "https://www.globalxetfs.com/funds/aiq/",
        "parser": "globalx",
    },
    "CLOU": {
        "issuer": "Global X (Mirae Asset)",
        "fund": "Global X Cloud Computing ETF",
        "page": "https://www.globalxetfs.com/funds/clou/",
        "parser": "globalx",
    },
    "BKCH": {
        "issuer": "Global X (Mirae Asset)",
        "fund": "Global X Blockchain ETF",
        "page": "https://www.globalxetfs.com/funds/bkch/",
        "parser": "globalx",
    },
    "LIT": {
        "issuer": "Global X (Mirae Asset)",
        "fund": "Global X Lithium & Battery Tech ETF",
        "page": "https://www.globalxetfs.com/funds/lit/",
        "parser": "globalx",
    },
    "BOTZ": {
        "issuer": "Global X (Mirae Asset)",
        "fund": "Global X Robotics & Artificial Intelligence ETF",
        "page": "https://www.globalxetfs.com/funds/botz/",
        "parser": "globalx",
    },
    "BUG": {
        "issuer": "Global X (Mirae Asset)",
        "fund": "Global X Cybersecurity ETF",
        "page": "https://www.globalxetfs.com/funds/bug/",
        "parser": "globalx",
    },
}

# Host spacing (>=2s per host) is enforced by the shared HttpRequestPolicy.
_POLICY = HttpRequestPolicy(retry_exceptions=(requests.RequestException,))
# iShares 403s non-browser user agents — use the UA the endpoints were
# verified with, plus the Aionis contact suffix.
_UA = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36 "
        "Aionis-Research/1.0 (educational; contact via repo)"
    )
}
_GX_CSV_RE = re.compile(
    r"https://assets\.globalxetfs\.com/funds/holdings/[a-z0-9-]+_full-holdings_\d{8}\.csv"
)
_ISHARES_ASOF_RE = re.compile(r"Fund Holdings as of,?\s*\"?([A-Za-z]{3} \d{1,2}, \d{4})")
_GX_ASOF_RE = re.compile(r"as of (\d{2}/\d{2}/\d{4})")
_EQUITY = "Equity"


def _get(url: str, total_attempts: int = 3) -> requests.Response:
    retry = RetryPolicy(max_retries=total_attempts - 1, backoff_base=2.0)
    return _POLICY.request(
        url, lambda: requests.get(url, headers=_UA, timeout=30), retry=retry
    )


def _num(value: str | None) -> float:
    """'3,797,569,144.40' / '9.05' / '-0.02' / '' → float (empty → 0.0)."""
    v = (value or "0").replace("$", "").replace(",", "").replace("%", "").strip()
    return float(v) if v else 0.0


def _header_index(lines: list[str], prefix: str) -> int:
    for i, ln in enumerate(lines):
        if ln.startswith(prefix):
            return i
    raise RuntimeError(f"no header row starting with {prefix!r}")


def parse_ishares(text: str) -> tuple[str, list[dict], int]:
    """Parse one iShares latest-holdings CSV → (as-of ISO date, rows, skipped).

    Rows are read BY COLUMN NAME (ICLN carries an extra ``Type`` column vs
    SOXX/ARTY/BAI). Only ``Asset Class == "Equity"`` rows with a ticker are
    kept; futures/cash/FX rows are skipped, honestly counted.
    """
    lines = text.splitlines()
    as_of = ""
    for ln in lines[:8]:
        m = _ISHARES_ASOF_RE.search(ln)
        if m:
            as_of = datetime.strptime(m.group(1), "%b %d, %Y").strftime("%Y-%m-%d")
            break
    if not as_of:
        raise RuntimeError("no 'Fund Holdings as of' date line")
    reader = csv.DictReader(lines[_header_index(lines, "Ticker,") :])
    rows: list[dict] = []
    skipped = 0
    for raw in reader:
        ticker = (raw.get("Ticker") or "").strip()
        if (raw.get("Asset Class") or "").strip() != _EQUITY or not ticker:
            skipped += 1
            continue
        rows.append({
            "ticker": ticker,
            "company": (raw.get("Name") or "").strip(),
            "weight_pct": _num(raw.get("Weight (%)")),
            "market_value": _num(raw.get("Market Value")),
        })
    return as_of, rows, skipped


def parse_globalx(text: str) -> tuple[str, list[dict], int]:
    """Parse one Global X full-holdings CSV → (as-of ISO date, rows, skipped).

    Line 1 = fund name, line 2 = ``Fund Holdings Data as of MM/DD/YYYY``.
    Rows with no ticker are cash / FX / payable bookkeeping rows — skipped
    and counted; positions WITH a ticker (including small futures legs such
    as ``NQU6 Index``) are kept at their official weight, never guessed away.
    """
    lines = text.splitlines()
    as_of = ""
    for ln in lines[:4]:
        m = _GX_ASOF_RE.search(ln)
        if m:
            mm, dd, yy = m.group(1).split("/")
            as_of = f"{yy}-{mm}-{dd}"
            break
    if not as_of:
        raise RuntimeError("no 'Fund Holdings Data as of' date line")
    reader = csv.DictReader(lines[_header_index(lines, "% of Net Assets,") :])
    rows: list[dict] = []
    skipped = 0
    for raw in reader:
        ticker = (raw.get("Ticker") or "").strip()
        if not ticker:
            skipped += 1
            continue
        rows.append({
            "ticker": ticker,
            "company": (raw.get("Name") or "").strip(),
            "weight_pct": _num(raw.get("% of Net Assets")),
            "market_value": _num(raw.get("Market Value ($)")),
        })
    return as_of, rows, skipped


_PARSERS = {"ishares": parse_ishares, "globalx": parse_globalx}


def parse_any(ticker: str, text: str) -> tuple[str, list[dict], int]:
    """Dispatch the issuer parser pinned for ``ticker`` (FUND_DEFS)."""
    return _PARSERS[FUND_DEFS[ticker]["parser"]](text)


def _resolve_file(tick: str, spec: dict[str, str]) -> str:
    """iShares: the pinned direct URL. Global X: extract the dated CSV href
    from the fund page's own HTML (same request budget, every day's link)."""
    if "url" in spec:
        return spec["url"]
    page = _get(spec["page"])
    page.raise_for_status()
    m = _GX_CSV_RE.search(page.text)
    if not m:
        raise RuntimeError("fund page carried no holdings CSV link (renamed?)")
    return m.group(0)


def fetch_all(sleep_s: float = 2.1) -> dict[str, dict]:
    """Fetch every fund politely (>=2.1s between requests; per-host spacing
    is additionally enforced by HttpRequestPolicy). Per-fund fault isolation.

    Returns ``{tick: {"as_of", "rows", "skipped", "text"}}``; failures come
    back as ``{"error": "..."}`` entries so one broken fund never takes the
    other nine down. Global X funds cost two GETs (page + dated file);
    iShares funds cost one.
    """
    out: dict[str, dict] = {}
    first = True
    for tick, spec in FUND_DEFS.items():
        if not first:
            time.sleep(sleep_s)
        first = False
        try:
            url = _resolve_file(tick, spec)
            if spec["parser"] == "globalx":
                time.sleep(sleep_s)  # page → dated file on the same host
            r = _get(url)
            r.raise_for_status()
            as_of, rows, skipped = parse_any(tick, r.text)
            if not as_of:
                raise RuntimeError("CSV carried no parseable as-of date")
            out[tick] = {"as_of": as_of, "rows": rows, "skipped": skipped, "text": r.text}
        except Exception as e:  # noqa: BLE001 — per-fault isolation, disclosed
            out[tick] = {"error": f"{type(e).__name__}: {e}"}
    return out
