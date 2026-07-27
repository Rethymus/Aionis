"""Polite health check for Aionis data sources + wheel repos.

Per the data-source registry (`docs/quant-selection-research.md` §8): probe each
data source's reachability and each wheel repo's last-commit freshness.

Strictly rate-limited — >=MIN_GAP_S between any two network calls + exponential
backoff. Short bursts get rate-limited/blocked from this egress (empirically:
gh search EOF, EastMoney RemoteDisconnected, Yahoo 429). Run off-peak via cron.

Usage:
  python scripts/health_check.py              # full probe (sources + wheels)
  python scripts/health_check.py --only data  # data sources only
  python scripts/health_check.py --only wheels

Emits runs/health_<iso>.json + prints a one-line-per-source summary.
Exit code: 0 if all ok, 1 otherwise (so cron can alert on failure).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

UA = {"User-Agent": "Aionis/0.1 research health-check"}
MIN_GAP_S = 2.0  # polite floor between any two network calls

_last = [0.0]


def _gap() -> None:
    wait = MIN_GAP_S - (time.monotonic() - _last[0])
    if wait > 0:
        time.sleep(wait)
    _last[0] = time.monotonic()


def probe_http(name: str, url: str, expect: int | None = None) -> dict:
    """GET with polite spacing + exp backoff. `expect` = the status that means
    'reachable' (e.g. 401 for Alpaca-without-key, 400 for FRED-no-key)."""
    _gap()
    for attempt in range(3):
        try:
            r = requests.get(url, headers=UA, timeout=20)
            ok = r.status_code == expect if expect is not None else r.status_code < 500
            return {
                "name": name, "kind": "http", "status": r.status_code,
                "ok": bool(ok), "bytes": len(r.content),
            }
        except Exception:  # pragma: no cover - network path
            time.sleep(2 ** attempt)
    return {"name": name, "kind": "http", "status": None, "ok": False,
            "error": "connection-failed"}


def probe_tiingo() -> dict:
    """Tiingo is the primary price source — probe with the key from env (.env).
    No key → reported as no-key (not a hard failure of the health check itself)."""
    key = os.environ.get("TIINGO_API_KEY")
    if not key:
        return {"name": "Tiingo (prices)", "kind": "http", "status": None,
                "ok": False, "error": "no-key-in-env"}
    _gap()
    for attempt in range(3):
        try:
            r = requests.get(
                "https://api.tiingo.com/tiingo/daily/SPY/prices",
                headers={"Authorization": f"Token {key}"}, timeout=20,
                params={"startDate": "2024-01-02", "endDate": "2024-01-03"},
            )
            return {"name": "Tiingo (prices)", "kind": "http",
                    "status": r.status_code, "ok": r.status_code == 200,
                    "bytes": len(r.content)}
        except Exception:  # pragma: no cover - network path
            time.sleep(2 ** attempt)
    return {"name": "Tiingo (prices)", "kind": "http", "status": None,
            "ok": False, "error": "connection-failed"}


def probe_alpaca() -> dict:
    """Alpaca backup price source — probe with creds from env (.env)."""
    kid, sec = os.environ.get("ALPACA_KEY_ID"), os.environ.get("ALPACA_SECRET_KEY")
    if not (kid and sec):
        return {"name": "Alpaca (prices backup)", "kind": "http", "status": None,
                "ok": False, "error": "no-creds-in-env"}
    _gap()
    for attempt in range(3):
        try:
            r = requests.get(
                "https://data.alpaca.markets/v2/stocks/SPY/bars",
                headers={"APCA-API-KEY-ID": kid, "APCA-API-SECRET-KEY": sec},
                params={"timeframe": "1Day", "start": "2024-01-02", "end": "2024-01-03",
                        "adjustment": "all", "limit": 1},
                timeout=20,
            )
            return {"name": "Alpaca (prices backup)", "kind": "http",
                    "status": r.status_code, "ok": r.status_code == 200,
                    "bytes": len(r.content)}
        except Exception:  # pragma: no cover - network path
            time.sleep(2 ** attempt)
    return {"name": "Alpaca (prices backup)", "kind": "http", "status": None,
            "ok": False, "error": "connection-failed"}


def probe_repo(repo: str) -> dict:
    """GitHub repo freshness via authed `gh api` (avoids the 60/hr unauth cap and
    the blocked raw/codeload hosts). Flags stale (>180d) and archived repos."""
    _gap()
    try:
        out = subprocess.run(
            ["gh", "api", f"repos/{repo}", "-q", ".pushed_at,.stargazers_count,.archived"],
            capture_output=True, text=True, timeout=20,
        )
        if out.returncode != 0:
            return {"name": repo, "kind": "repo", "ok": False,
                    "error": out.stderr.strip()[:80]}
        pushed, stars, archived = (out.stdout.strip().split(",") + ["?", "?", "?"])[:3]
        if pushed.endswith("Z"):
            dt = datetime.fromisoformat(pushed.replace("Z", "+00:00"))
            days = int((datetime.now(timezone.utc) - dt).days)
        else:
            days = 9999
        stale = days > 180
        ok = archived == "false" and not stale
        return {"name": repo, "kind": "repo", "pushed_at": pushed, "stars": stars,
                "archived": archived, "days_since_push": days, "ok": ok}
    except Exception as e:  # pragma: no cover - network/parse path
        return {"name": repo, "kind": "repo", "ok": False, "error": type(e).__name__}


# (name, url, expected_status) — expect = the status meaning "reachable"
DATA_SOURCES = [
    ("EDGAR XBRL (fundamentals, PIT)",
     "https://data.sec.gov/api/xbrl/companyconcept/CIK0000320193/us-gaap/Assets.json", 200),
    ("FRED (macro)",
     "https://api.stlouisfed.org/fred/series?series_id=SP500&file_type=json&api_key=none", 400),
    ("akshare/EastMoney (prices)",
     "https://push2his.eastmoney.com/api/qt/stock/kline/get?secid=105.AAPL&klt=101&fqt=1"
     "&beg=20240102&end=20240105&fields1=f1&fields2=f51", 200),
    ("GitHub raw-redirect (reference data)",
     "https://github.com/datasets/s-and-p-500-companies/raw/main/data/constituents.csv", 200),
]

WHEEL_REPOS = [
    "pmorissette/bt",
    "stefan-jansen/alphalens-reloaded",
    "stefan-jansen/pyfolio-reloaded",
    "eslazarev/purged-cross-validation",
    "bashtage/arch",
    "microsoft/LightGBM",
    "pydata/pandas-datareader",
    "mlflow/mlflow",
    "dgunning/edgartools",
    "akfamily/akshare",
    "DoubleML/doubleml",
    "posit-dev/great-tables",
    "ranaroussi/quantstats",
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=["data", "wheels"], default=None)
    args = ap.parse_args()

    results: list[dict] = []
    if args.only != "wheels":
        results += [probe_http(*s) for s in DATA_SOURCES]
        results.append(probe_tiingo())
        results.append(probe_alpaca())
    if args.only != "data":
        results += [probe_repo(r) for r in WHEEL_REPOS]

    report = {"checked_at": datetime.now(timezone.utc).isoformat(),
              "min_gap_s": MIN_GAP_S, "results": results}
    out = Path("runs") / f"health_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(report, indent=2))

    n_ok = sum(1 for r in results if r["ok"])
    print(f"health: {n_ok}/{len(results)} ok -> {out}")
    for r in results:
        flag = "OK  " if r["ok"] else "BAD "
        extra = r.get("status") or r.get("pushed_at") or r.get("error", "?")
        print(f"  [{flag}] {r['name']:<42} {extra}")
    return 0 if n_ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
