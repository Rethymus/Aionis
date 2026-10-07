"""LLM memory probe — an exploratory leakage diagnostic (Glasserman-Lin style).

Methodology anchor (round-221 external research, finding #11):
- Glasserman & Lin (arXiv 2309.17322) define the two look-ahead contamination
  forms in LLM stock prediction (memorized outcomes; post-hoc narratives).
- Didisheim, Fraschini & Somoza (Economics Letters 2025) turn memory into a
  measurable quantity: ask the model to recall historical returns and score
  the recall against ground truth.

This script asks the extraction pool's providers a small set of
**pre-cutoff** questions — "which S&P 500 constituent had the best
single-month return in <month>?" for months <= 2023-02 (the empirically
probed provider cutoff, 2023-03-10 conservative lower bound) — and scores
top-1 nomination against ground truth computed locally from the display
price panel. Purpose: a logged, repeatable diagnostic of how much the pool
*remembers* of training-period winners — context for E3 forward-live, where
post-cutoff months are the clean evaluation. It is NOT a claim, NOT a gate.

Bounds & honesty
----------------
- EXPLORATORY (one ledger row + payload); never wired into any gate.
- Top-1 nomination is a STRICT recall measure: a low hit rate does not prove
  absence of memorization (Didisheim use broader recall metrics); v1 measures
  only whether the model names the true top-1 ticker.
- Ground truth = last-close monthly returns over the display panel's ticker
  set (display-layer data; the same panel the terminal serves).
- Providers without an API key are skipped honestly; a bounded single retry
  per call (project token discipline).

Usage::

    uv run python scripts/llm_memory_probe.py
    PROBE_NO_LEDGER=1 uv run python scripts/llm_memory_probe.py
"""
from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PANEL = ROOT / "data" / "cache" / "display_panel.parquet"
OUT = ROOT / "reports" / "exploratory" / "llm-memory-probe.json"
LEDGER = ROOT / "runs" / "ledger.jsonl"

N_MONTHS = 4
SEED = 0
CUTOFF_YM = "2023-02"          # <= empirical provider cutoff lower bound
SAMPLE_START_YM = "2020-01"    # post-2016 universe start; memorable regime
CALL_SPACING_S = 2.0

# ---------------------------------------------------------------------------
# Pure core (hermetically tested)
# ---------------------------------------------------------------------------

def monthly_winners(
    df: pd.DataFrame, start_ym: str = SAMPLE_START_YM,
    end_ym: str = CUTOFF_YM,
) -> dict[str, dict[str, Any]]:
    """Per calendar month: top-1 ticker by last-close-to-last-close return."""
    px = df[["date", "ticker", "close"]].copy()
    px["date"] = pd.to_datetime(px["date"])
    px = px.sort_values("date")
    px["ym"] = px["date"].dt.strftime("%Y-%m")
    month_end = px.groupby(["ticker", "ym"])["close"].last().reset_index()
    month_end["prev_close"] = month_end.groupby("ticker")["close"].shift(1)
    # shift(1) pairs each month with the ticker's PREVIOUS listed month;
    # the first month per ticker has no prev and drops out below.
    month_end = month_end.dropna(subset=["prev_close"])
    month_end["ret"] = month_end["close"] / month_end["prev_close"] - 1.0
    month_end = month_end[(month_end["ym"] >= start_ym)
                          & (month_end["ym"] <= end_ym)]
    winners: dict[str, dict[str, Any]] = {}
    for ym, grp in month_end.groupby("ym"):
        top = grp.sort_values("ret", ascending=False).iloc[0]
        winners[str(ym)] = {
            "ticker": str(top["ticker"]),
            "ret": float(top["ret"]),
            "n_tickers": int(len(grp)),
        }
    return winners


def sample_months(
    winners: dict[str, dict[str, Any]], n: int = N_MONTHS, seed: int = SEED,
) -> list[str]:
    """Deterministic seeded month sample (chronological order for the log).

    Equal-stride positions over the sorted months, offset by seed within the
    first stride — same winners/n/seed always yields the same sample.
    """
    keys = sorted(winners)
    if n >= len(keys):
        return keys
    stride = len(keys) / n
    offset = seed % max(1, int(stride))
    picked = sorted({keys[min(int(i * stride + offset), len(keys) - 1)]
                     for i in range(n)})
    return picked[:n]


def build_question(ym: str) -> tuple[str, str]:
    year, month = int(ym[:4]), int(ym[5:7])
    system = (
        "You answer factual market-history questions from memory only, "
        "without tools. Reply with a single JSON object {\"ticker\": ...} "
        "where the value is one US stock ticker, or \"unknown\" if you are "
        "not confident. No explanations."
    )
    user = (
        f"From memory: which S&P 500 constituent company had the LARGEST "
        f"single-month stock return in {year}-{month:02d}? "
        f"Answer with just the ticker."
    )
    return system, user


REFUSAL_TOKENS = ("unknown", "not sure", "i don't know", "cannot", "no data", "n/a")


def score_answer(raw: str, truth_ticker: str, error: str | None = None) -> dict[str, Any]:
    """Parse the answer into THREE honest states, then score top-1 nomination.

    - ``no_answer``: transport/API error or empty response (NOT a refusal —
      an errored call says nothing about the model's memory);
    - ``refusal``: an explicit "unknown"-class answer (honest abstention);
    - otherwise an answered nomination, scored ``hit`` iff the truth ticker.
    """
    answer = (raw or "").strip()
    if error or not answer:
        return {"raw": answer[:200], "parsed_ticker": None,
                "status": "no_answer", "refusal": False, "hit": False,
                "error": error}
    tick: str | None = None
    try:
        obj = json.loads(answer)
        if isinstance(obj, dict):
            tick = str(obj.get("ticker") or "").strip() or None
    except (json.JSONDecodeError, ValueError):
        tick = None
    refusal = tick is None or any(tok in (tick or "").lower() for tok in REFUSAL_TOKENS)
    hit = bool(tick and not refusal and (
        tick.upper() == truth_ticker.upper()
        or f"({truth_ticker.upper()})" in answer.upper()))
    return {"raw": answer[:200], "parsed_ticker": tick,
            "status": "refusal" if refusal else "answered",
            "refusal": refusal, "hit": hit, "error": None}


def summarize(per_provider: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for provider, rows in per_provider.items():
        refusals = sum(1 for r in rows if r.get("status") == "refusal")
        no_answer = sum(1 for r in rows if r.get("status") == "no_answer")
        hits = sum(1 for r in rows if r["hit"])
        answered = len(rows) - refusals - no_answer
        out[provider] = {
            "n_questions": len(rows),
            "refusals": refusals,
            "no_answer_api": no_answer,
            "top1_hits": hits,
            "hit_rate_answered": (hits / answered) if answered else None,
        }
    return out


# ---------------------------------------------------------------------------
# Network layer (small, honest degradation)
# ---------------------------------------------------------------------------

def _run_pool(months: list[str], winners: dict[str, dict[str, Any]],
              ) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    import sys
    sys.path.insert(0, str(ROOT))
    from aionis.extraction.llm_client import OpenAICompatClient
    from aionis.extraction.providers import build_providers

    per_provider: dict[str, list[dict[str, Any]]] = {}
    tokens: dict[str, dict[str, int]] = {}
    skipped: dict[str, str] = {}
    for p in build_providers(only_enabled=True):
        if not p.api_key:
            skipped[p.name] = "no api key in settings"
            continue
        client = OpenAICompatClient(p)
        tokens[p.name] = {"prompt": 0, "completion": 0}
        rows: list[dict[str, Any]] = []
        for ym in months:
            truth = winners[ym]["ticker"]
            system, user = build_question(ym)
            raw, err = "", None
            for _attempt in (1, 2):  # bounded single retry (token discipline)
                try:
                    raw = client._chat(system, user)  # noqa: SLF001 — probe is
                    # deliberately thin over the client's JSON-mode chat.
                    break
                except Exception as exc:  # noqa: BLE001 — log & bounded retry
                    err = str(exc)[:120]
                    time.sleep(CALL_SPACING_S)
            usage = getattr(client, "last_usage", {})
            tokens[p.name]["prompt"] += int(usage.get("prompt_tokens", 0) or 0)
            tokens[p.name]["completion"] += int(usage.get("completion_tokens", 0) or 0)
            row = score_answer(raw, truth, error=err)
            row.update({"month": ym, "truth_ticker": truth,
                        "truth_ret": round(winners[ym]["ret"], 4)})
            rows.append(row)
            time.sleep(CALL_SPACING_S)
        per_provider[p.name] = rows
    return per_provider, {"tokens": tokens, "skipped_providers": skipped}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--no-run", action="store_true",
                        help="compute ground truth + print plan; no LLM calls")
    args = parser.parse_args()

    if not PANEL.exists():
        print("[probe] display panel absent on this machine — nothing to do")
        return 0
    winners = monthly_winners(pd.read_parquet(PANEL))
    months = sample_months(winners)
    print(f"[probe] {len(winners)} pre-cutoff months with winners; "
          f"sampled {len(months)}: {months}")
    for ym in months:
        w = winners[ym]
        print(f"  {ym}: {w['ticker']} ({w['ret']:+.1%}, {w['n_tickers']} tickers)")
    if args.no_run:
        return 0

    per_provider, meta = _run_pool(months, winners)
    if not per_provider:
        print(f"[probe] no provider available (skipped: {meta.get('skipped_providers')})")
        return 0

    summary = summarize(per_provider)
    payload = {
        "as_of": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "kind": "llm-memory-probe",
        "exploratory": True,
        "method": (
            "Top-1 nomination recall: per pre-cutoff month (<=2023-02), each "
            "extraction-pool provider is asked (JSON mode, temperature 0.1) "
            "to name the S&P 500 constituent with the largest monthly "
            "return; ground truth = last-close returns over the display "
            "panel. Glasserman-Lin (arXiv 2309.17322) contamination forms; "
            "Didisheim et al. (Econ. Letters 2025) memory-measurement idea."
        ),
        "months": months,
        "n_months": len(months),
        "results": per_provider,
        "summary": summary,
        "token_usage": meta["tokens"],
        "skipped_providers": meta["skipped_providers"],
        "caveats": [
            "top-1 nomination is a STRICT recall measure — a low hit rate "
            "does not prove absence of memorization (broader recall metrics "
            "per Didisheim et al. are future work)",
            "ground truth covers the display panel's ticker set for that "
            "month (winner among listed names with consecutive month-ends)",
            "EXPLORATORY diagnostic for E3 forward-live context; not a "
            "claim, not a gate; provider answers are themselves model "
            "output and are logged verbatim (first 200 chars)",
        ],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    for prov, s in summary.items():
        print(f"[probe] {prov}: hits {s['top1_hits']}/{s['n_questions']} "
              f"(refusals {s['refusals']}, api-no-answer {s['no_answer_api']}, "
              f"hit-rate-on-answered {s['hit_rate_answered']})")
    print(f"[probe] wrote {OUT}")

    if not os.environ.get("PROBE_NO_LEDGER"):
        entry = {
            "ts": payload["as_of"],
            "event": "exploratory",
            "phase": "llm_memory_probe",
            "n_months": len(months),
            "summary": summary,
            "notes": (
                "Pre-cutoff top-1 winner-recall probe over the extraction "
                "pool (Glasserman-Lin / Didisheim methodology). EXPLORATORY "
                "leakage diagnostic for E3 context; strict top-1 caveat "
                "applies; not a claim, not a gate. Payload: "
                "reports/exploratory/llm-memory-probe.json"
            ),
        }
        with open(LEDGER, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
        print(f"[probe] appended exploratory row to {LEDGER}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
