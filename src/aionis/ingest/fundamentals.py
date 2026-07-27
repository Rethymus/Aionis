"""Point-in-time firm fundamentals from SEC EDGAR XBRL (as-filed).

The TCR Entity/State layer: Corporate Vital Signs. Every XBRL fact carries a
filing date (``filed``) and a period end (``end``); the PIT-correct join at
calendar date ``d`` is the latest fact with ``filed <= d`` — NOT ``end <= d``
(using a period-end value before it was actually filed is lookahead). This is
the same vintage discipline as ``macro_surprise.py``'s ALFRED as-of join.

Free, no key (only a descriptive User-Agent, per SEC fair-access); <=10 req/s.
Raw JSON cached at ``data/cache/`` so reruns make no HTTP calls.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import pandas as pd
import structlog

from aionis.config import settings
from aionis.ingest.universe import normalize_ticker

log = structlog.get_logger()

_UA = "Aionis research fundamentals contact@example.com"
_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"

# Minimal Vital Signs with multi-tag fallback (firms use different us-gaap tags).
# spans size / value / profitability / leverage / shares-out.
METRIC_TAGS: dict[str, tuple[str, ...]] = {
    "assets": ("Assets",),
    "equity": ("StockholdersEquity", "AssetsStockholdersEquity"),
    "revenue": (
        "Revenues",
        "RevenueFromContractWithCustomerExcludingAssessedTax",
    ),
    "net_income": ("NetIncomeLoss",),
    "shares_out": (
        "EntityCommonStockSharesOutstanding",
        "CommonStockSharesOutstanding",
    ),
    "long_term_debt": ("LongTermDebt", "LongTermDebtNoncurrent"),
}


def _cache_dir(cache_dir: Path | None = None) -> Path:
    d = cache_dir or settings.data_dir / "cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


def cik_map(cache_dir: Path | None = None) -> dict[str, int]:
    """Ticker -> CIK, cached (one ~1MB fetch for the whole universe)."""
    fp = _cache_dir(cache_dir) / "sec_tickers.json"
    if fp.exists():
        return json.loads(fp.read_text())
    import requests

    r = requests.get(_TICKERS_URL, headers={"User-Agent": _UA}, timeout=30)
    r.raise_for_status()
    raw = r.json()
    m = {v["ticker"].upper(): int(v["cik_str"]) for v in raw.values()}
    fp.write_text(json.dumps(m))
    return m


def company_facts(
    cik: int, cache_dir: Path | None = None, retries: int = 4, backoff: int = 4,
) -> dict:
    """Full as-filed XBRL facts for one CIK, cached.

    SEC (``data.sec.gov``) drops connections under sustained burst
    (``SSL: UNEXPECTED_EOF_WHILE_READING``); retries with exponential backoff
    (matches ``market.py``'s polite pattern). 0.15s between successes respects the
    fair-access <=10 req/s; the backoff handles transient resets."""
    import requests

    fp = _cache_dir(cache_dir) / f"sec_facts_{cik:010d}.json"
    if fp.exists():
        return json.loads(fp.read_text())
    last: Exception | None = None
    for attempt in range(retries):
        try:
            r = requests.get(
                _FACTS_URL.format(cik=cik), headers={"User-Agent": _UA}, timeout=60,
            )
            r.raise_for_status()
            data = r.json()
            fp.write_text(json.dumps(data))
            time.sleep(0.15)  # SEC fair-access: <=10 req/s
            return data
        except Exception as e:  # transient SSL/reset/timeout -> backoff and retry
            last = e
            log.warning(
                "company_facts_retry", cik=cik, attempt=attempt + 1, of=retries, error=str(e),
            )
            if attempt < retries - 1:
                time.sleep(backoff * (attempt + 1))  # 4s, 8s, 12s
    raise RuntimeError(f"company_facts failed for CIK {cik} after {retries} retries: {last}")


def _extract(facts: dict, tags: tuple[str, ...]) -> list[dict]:
    """Pull one metric's as-filed facts (end, filed, form, fy, fp, value, unit),
    trying tags in order. 10-K/10-Q only; sorted by filing date."""
    us_gaap = facts.get("facts", {}).get("us-gaap", {})
    for tag in tags:
        node = us_gaap.get(tag)
        if not node:
            continue
        rows: list[dict] = []
        for unit, lst in node.get("units", {}).items():
            for f in lst:
                if f.get("form") not in ("10-K", "10-Q"):
                    continue
                if not (f.get("fp") and f.get("fy")):
                    continue
                rows.append({
                    "end": f["end"], "filed": f["filed"], "form": f["form"],
                    "fy": f["fy"], "fp": f["fp"], "value": float(f["val"]), "unit": unit,
                })
        if rows:
            return sorted(rows, key=lambda x: x["filed"])
    return []


def build_fundamentals(
    tickers: list[str], cache_dir: Path | None = None,
    *, cik_override: dict[str, int] | None = None,
) -> pd.DataFrame:
    """Long-format as-filed fundamentals frame:
    [ticker, metric, end, filed, form, fy, fp, value, unit].
    Each row is one fact as it was FILED; PIT alignment is the consumer's job
    (see :func:`pit_align`), never use ``end`` as the knowable date.

    ``cik_override``: a pre-resolved ``{ticker: CIK}`` map (e.g. from
    :func:`aionis.ingest.universe.build_oos_resolvable_universe`) — bypasses the
    current-snapshot ``cik_map`` so historical/renamed tickers resolve. Keys are
    matched via :func:`normalize_ticker`; without it, ``cik_map`` (upper-case) is used.
    """
    if cik_override is not None:
        cmap = cik_override
        key = normalize_ticker
    else:
        cmap = cik_map(cache_dir)
        key = str.upper
    rows: list[dict] = []
    for t in tickers:
        cik = cmap.get(key(t))
        if not cik:
            log.warning("ticker_no_cik", ticker=t)
            continue
        try:
            facts = company_facts(cik, cache_dir)
        except Exception as e:  # a stubborn CIK must not abort the whole universe
            log.warning("ticker_facts_failed", ticker=t, cik=cik, error=str(e))
            continue
        n_before = len(rows)
        for metric, tags in METRIC_TAGS.items():
            for fr in _extract(facts, tags):
                rows.append({"ticker": key(t), "metric": metric, **fr})
        log.info("fundamentals_extracted", ticker=t, n_facts=len(rows) - n_before)
    return pd.DataFrame(rows)


# Fama-French / Compustat standard-practice "information availability" lag applied
# to period-end for the Phase B arm_base baseline (align_on="end_lag").
_DEFAULT_END_LAG = {"10-K": 6, "10-Q": 4}


def pit_align(
    long: pd.DataFrame, as_of_dates: pd.DatetimeIndex, tickers: list[str],
    metrics: list[str] | None = None, *, align_on: str = "filed",
    lag_months: dict[str, int] | None = None,
) -> dict[str, pd.DataFrame]:
    """PIT cross-section: for each metric, a wide DataFrame (as_of_dates x
    tickers) whose [d, t] cell is the value of the latest fact knowable on or
    before d. Knowability is set by ``align_on``:

      * ``"filed"`` (default) — the fact's SEC filing date. The PIT-correct join
        (Phase B ``arm_state``); ``merge_asof(direction='backward')`` on filing
        date, NaN before first filing. Never substitute period-end ``end``.
      * ``"end_lag"`` — ``end`` plus a form-dependent lag (10-K +6mo, 10-Q +4mo,
        or ``lag_months``). The Fama-French/Compustat standard-practice baseline
        (Phase B ``arm_base``); intentionally ignores ``filed``. Slow-filers
        (filed > end+lag) make this arm mildly leaky-optimistic for them — that
        bias is *against* the filed-date arm by construction.
    """
    metrics = metrics or list(METRIC_TAGS)
    if align_on not in ("filed", "end_lag"):
        raise ValueError(f"align_on must be 'filed' or 'end_lag', got {align_on!r}")
    df = long.copy()
    if align_on == "filed":
        df["align_dt"] = pd.to_datetime(df["filed"])
    else:
        lag = lag_months or _DEFAULT_END_LAG
        end_dt = pd.to_datetime(df["end"])
        months = df["form"].map(lambda f: lag.get(f, lag.get("10-K", 6)))
        df["align_dt"] = pd.Series(
            (e + pd.DateOffset(months=mm) for e, mm in zip(end_dt, months, strict=True)),
            index=df.index,
        )
    left = pd.DataFrame({"d": pd.DatetimeIndex(as_of_dates).normalize()})
    panels: dict[str, pd.DataFrame] = {}
    for metric in metrics:
        wide = pd.DataFrame(index=left["d"], columns=tickers, dtype=float)
        sub = df[df["metric"] == metric]
        for t in tickers:
            s = sub[sub["ticker"] == t].sort_values("align_dt")
            s = s.drop_duplicates("align_dt", keep="last")[["align_dt", "value"]]
            s = s.rename(columns={"align_dt": "d"})
            if s.empty:
                continue
            m = pd.merge_asof(left, s, on="d", direction="backward")
            wide[t] = m["value"].to_numpy()
        panels[metric] = wide
    return panels
