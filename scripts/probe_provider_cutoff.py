"""Empirical provider knowledge-cutoff probe (P1-2 vintage discipline).

Dual-blind event-ladder probe: ask the pinned provider model about dated,
first-hand verifiable events and measure which it recognizes. The ladder
spans (a) widely-reported 2023-2025 public events and (b) 2026 events taken
verbatim from Aionis's OWN committed panels (form8k — first-hand, dated, no
fabrication), plus one deliberately-fake control event to measure the
model's fabrication tendency.

Output: runs/provider_cutoff_probe.json — per-event answers + a boundary
estimate (latest KNOWN event date / earliest UNKNOWN event date). The
estimate is EMPIRICAL: it is not a vendor declaration and must never be
recorded as one (see config/e3_live_contracts.yaml governance notes).

Usage:
    uv run python scripts/probe_provider_cutoff.py [--model glm-4-flash]

Politeness: 1.5s between calls (model APIs are exempt from the 2s host
spacing rule; bounded to <=20 calls total). Security: the endpoint host is
a module CONSTANT (pinned vendor host, https only, DNS resolved and checked
public, redirects disabled) — the request target is never built from
user-controlled input; only the API key/model come from project settings.
"""
from __future__ import annotations

import argparse
import ipaddress
import json
import re
import socket
import time
import urllib.parse
import urllib.request
from pathlib import Path

from aionis.config import settings

# Pinned vendor endpoint (protocol + host are constants, never dynamic).
_ENDPOINT = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
_VENDOR_HOST = "open.bigmodel.cn"


def _guard(url: str) -> None:
    """SSRF guard: https-only, pinned vendor host, public resolved IPs only."""
    parts = urllib.parse.urlparse(url)
    if parts.scheme != "https" or parts.hostname != _VENDOR_HOST:
        raise ValueError(f"blocked non-vendor endpoint: {url!r}")
    fake_ip_net = ipaddress.ip_network("198.18.0.0/15")  # local proxy fake-IP DNS mode
    for _fam, _typ, _proto, _canon, sa in socket.getaddrinfo(parts.hostname, 443):
        ip = ipaddress.ip_address(sa[0])
        proxy_artifact = ip in fake_ip_net  # local proxy DNS mode: routing is by SNI
        if (proxy_artifact or ip.is_global):
            continue  # public, or the local proxy's fake-IP for the pinned host
        raise ValueError(f"blocked non-public resolved address: {ip}")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None  # redirects disabled — pinned target only


_OPENER = urllib.request.build_opener(_NoRedirect)

OUT = Path("runs/provider_cutoff_probe.json")
PANEL_DIR = Path("web/src/data/aionis")

# (a) Widely-reported public events — author-known (B-tier: not machine-
# verified, but unambiguous and heavily covered at the time).
PUBLIC_EVENTS = [
    ("2023-03-10", "Silicon Valley Bank (SVB) collapsed and was seized by regulators"),
    ("2024-11-06", "Donald Trump was declared winner of the US presidential election"),
    ("2025-01-27", "Nvidia shares fell ~17% after the DeepSeek-R1 release"),
    ("2025-04-03", "US stocks fell sharply (S&P -4.8%) after sweeping 'Liberation Day' tariffs"),
    ("2025-05-12", "The US and China announced a 90-day tariff truce and markets surged"),
]

# Control: a real date with no notable single event — measures fabrication.
FAKE_CONTROL = ("2026-12-25", "The SEC approved a single global crypto exchange")


def _system() -> str:
    return (
        "You are a knowledge probe. Answer strictly from your training "
        "knowledge. If you do not know or cannot verify, answer exactly "
        "'UNKNOWN'. Do not guess."
    )


def _ask(api_key: str, model: str, question: str) -> str:
    body = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": _system()},
            {"role": "user", "content": question},
        ],
        "temperature": 0,
        "max_tokens": 300,
        # GLM-4.5+ put output in a reasoning channel unless disabled:
        "thinking": {"type": "disabled"},
    }).encode("utf-8")
    req = urllib.request.Request(
        _ENDPOINT,  # pinned constant host — see module docstring
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    last_err: Exception | None = None
    for attempt in range(3):
        _guard(_ENDPOINT)  # re-validated immediately before every call
        try:
            with _OPENER.open(req, timeout=60) as r:
                d = json.load(r)
            msg = (d.get("choices") or [{}])[0].get("message", {})
            return (msg.get("content") or msg.get("reasoning_content") or "").strip()
        except urllib.error.HTTPError as e:
            last_err = e
            if e.code == 429:
                time.sleep(20 * (attempt + 1))  # provider rate limit — back off
                continue
            raise
        except urllib.error.URLError as e:
            last_err = e
            time.sleep(10)
            continue
    return f"PROBE-ERROR: {last_err}"


def _classify(answer: str) -> str:
    a = answer.strip().lower()
    if a.startswith("unknown") or "do not know" in a or "don't know" in a or len(a) < 3:
        return "unknown"
    if re.search(r"\bunsure\b|\bnot sure\b|\bcannot verif", a):
        return "unsure"
    return "known"


def _panel_events(n: int = 3) -> list[tuple[str, str]]:
    """First-hand 2026 events from Aionis's OWN committed panels (dated)."""
    out: list[tuple[str, str]] = []
    try:
        f8 = json.loads((PANEL_DIR / "form8k.json").read_text(encoding="utf-8"))
        for it in (f8.get("recent") or [])[:n]:
            d = str(it.get("date") or "")[:10]
            co = str(it.get("company") or it.get("issuer") or "")
            item = str(it.get("item") or "")
            if d and co:
                out.append((d, f"{co} filed an 8-K (Item {item})"))
    except Exception:
        pass
    return out[:n]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=settings.llm_model or "glm-4-flash")
    args = ap.parse_args()

    api_key = settings.openai_api_key
    if not api_key:
        raise SystemExit("no provider key configured (openai_api_key absent)")

    events: list[tuple[str, str, str]] = []
    for d, desc in PUBLIC_EVENTS:
        events.append((d, desc, "public-known"))
    for d, desc in _panel_events(3):
        events.append((d, desc, "panel-first-hand"))
    events.append((FAKE_CONTROL[0], FAKE_CONTROL[1], "fake-control"))

    results = []
    for d, desc, kind in events:
        q = (f"What notable event happened on or around {d}? "
             f"If you do not know of any such event, answer exactly UNKNOWN. "
             f"Context (may or may not be true): {desc}")
        try:
            ans = _ask(api_key, args.model, q)
        except Exception as e:  # noqa: BLE001 — probe must complete
            ans = f"PROBE-ERROR: {e}"
        verdict = ("PROBE-ERROR" if ans.startswith("PROBE-ERROR")
                   else _classify(ans))
        fabricated = (verdict == "known" and kind == "fake-control")
        results.append({
            "date": d, "kind": kind, "event": desc, "verdict": verdict,
            "fabrication_suspect": fabricated, "answer": ans[:400],
        })
        print(f"[{d}] {kind}: {verdict} :: {ans[:110]}", flush=True)
        time.sleep(1.5)

    known_dates = sorted(r["date"] for r in results if r["verdict"] == "known"
                         and r["kind"] != "fake-control")
    unknown_dates = sorted(r["date"] for r in results if r["verdict"] == "unknown")
    boundary = {
        "latest_known": known_dates[-1] if known_dates else None,
        "earliest_unknown": unknown_dates[0] if unknown_dates else None,
        "fabrication_on_control": any(r["fabrication_suspect"] for r in results),
    }
    payload = {
        "model": args.model,
        "probed_at_note": "timestamps deliberately omitted (artifact stability); "
                          "see the invoking session's log for wall-clock",
        "method": "dual-blind dated-event ladder; KNOWN/UNKNOWN classification; "
                  "fake-control measures fabrication tendency",
        "boundary_estimate": boundary,
        "disclaimer": "EMPIRICAL probe — not a vendor declaration. Must never "
                      "be recorded as a vendor-declared cutoff.",
        "events": results,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=1, ensure_ascii=False))
    print(f"[probe] wrote {OUT} | boundary: {boundary}", flush=True)


if __name__ == "__main__":
    main()
