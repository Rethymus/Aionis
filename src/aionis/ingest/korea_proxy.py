"""Korea risk-appetite proxy — USD/KRW (FRED DEXKOUS), display-only.

The Korean RETAIL-LEVERAGE dimension (신용융자 margin balances) has every
free first-party route hard-blocked (KRX old portal session-enforced ×4,
FRED carries no such series, BOK ECOS is TLS-blocked from this network) and
KRX's only official channel is a PAID marketplace (bank transfer + review
+ file delivery — see ``archive/krx-probes/README.md``). Under the owner's
boundary-revocation directive this module ships the TACO→BTS-style DEGRADED
equivalent the owner's option C describes: the won's dollar rate as a
Korean risk-appetite/stress proxy (sharp won weakness tracks capital-flight
and forced-margin-unwind episodes), with the degradation stated IN THE
PANEL — it is NOT margin financing and never claims to be.

Source: FRED ``DEXKOUS`` (Korean Won to U.S. Dollar Exchange Rate, weekly,
Board of Governors of the Federal Reserve System — public domain), fetched
with the same plain-observations pattern as ``macro_display`` (≥2s host
spacing via ``_policy_get``, idempotent cache).
"""
from __future__ import annotations

import json
from pathlib import Path

SERIES_ID = "DEXKOUS"
SERIES_TITLE = "Korean Won to U.S. Dollar Exchange Rate (USD/KRW)"
_CACHE = Path("data/cache/korea_proxy_usdkrw.json")


def _fetch_observations(fred_api_key: str, start_date: str = "2015-01-01") -> list[dict]:
    from aionis.ingest.universe import _policy_get

    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {
        "series_id": SERIES_ID,
        "api_key": fred_api_key,
        "file_type": "json",
        "observation_start": start_date,
        "limit": 100_000,
        "offset": 0,
    }
    resp = _policy_get(url, params=params, timeout=60)
    resp.raise_for_status()
    return resp.json().get("observations", [])


def fetch_korea_proxy(fred_api_key: str, *, force: bool = False) -> Path:
    """Fetch DEXKOUS weekly observations into the idempotent cache."""
    if _CACHE.exists() and not force:
        return _CACHE
    rows = [
        {"date": o["date"], "value": float(o["value"])}
        for o in _fetch_observations(fred_api_key)
        if o.get("value") not in (".", "", None)
    ]
    _CACHE.parent.mkdir(parents=True, exist_ok=True)
    _CACHE.write_text(json.dumps({"series_id": SERIES_ID, "observations": rows}))
    return _CACHE
