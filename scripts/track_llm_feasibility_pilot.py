"""Track LLM Phase-0 feasibility pilot — leakage-safe, 0 ledger, no OOS observation.

Measures the two gates that decide whether Track LLM (an EDGAR-10-K-derived LLM
filings-tone feature as a 42nd column on the frozen Track-C learner) is worth a
frozen pre-registration:

  G1. CIK resolution rate for the ACTUAL US OOS universe (local; no network).
      The binding PIT-coverage constraint: a ticker must resolve to a SEC CIK to
      have a 10-K to extract from. cik_resolver's known ~60% gap is a HISTORICAL
      universe (1996-2025) concern; this measures the rate for the OOS window.
  G2. Projected one-time token cost for the 10-K MD&A extraction backfill, from
      resolution x annual filing rate x a per-call token estimate. Calibrate the
      per-call estimate with --measure-llm (needs creds).

Anti-leakage contract (this is the load-bearing part):
  - This pilot observes NO out-of-sample rank-IC, writes NO ledger row, freezes
    NO config. It only measures data-availability + projected cost.
  - Track LLM itself remains PROPOSED until owner GO + ``config_committed``
    (sha256 to ledger BEFORE any OOS IC is observed).
  - CIK resolution is a STATIC lookup over a cached snapshot; no look-ahead.

Usage::

    uv run python scripts/track_llm_feasibility_pilot.py            # G1 + G2 (local)
    uv run python scripts/track_llm_feasibility_pilot.py --measure-llm 8  # +G3/G4 (creds)
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from aionis.ingest.cik_resolver import resolve_ciks
from aionis.ingest.universe import normalize_ticker

# --- named constants (no magic numbers) --------------------------------------

_OOS_PATH = Path("runs/track_c_confirmatory_oos_scores.parquet")
_TRAIN_YEARS_DEFAULT = 5  # 2016-2020 expanding-window train (Track-C aligned)
# 10-K MD&A excerpt: <=2000 tok in (truncated section) + ~100 tok JSON out.
_TOKENS_PER_10K_DEFAULT = 2100
_COVERAGE_GATE = 0.90  # min CIK resolution rate for a green G1 gate
_UNRESOLVED_SAMPLE_N = 20


def _load_oos_us(oos_path: Path = _OOS_PATH) -> pd.DataFrame:
    """US rows from the confirmatory OOS scores parquet, with normalized ticker + year.

    Raises if the parquet is absent (the pilot is meaningless without the OOS
    universe it would extend).
    """
    if not oos_path.exists():
        raise FileNotFoundError(
            f"OOS scores not found at {oos_path}; run the confirmatory pipeline first."
        )
    df = pd.read_parquet(oos_path)
    df["date"] = pd.to_datetime(df["date"])
    us = df[df["region"] == "us"].copy()
    us["ticker_norm"] = us["ticker"].map(normalize_ticker)
    us["year"] = us["date"].dt.year
    return us


def measure_cik_resolution(oos_us: pd.DataFrame, cmap: dict[str, int]) -> dict:
    """G1: CIK resolution rate for the US OOS universe (pure; no network).

    ``cmap`` is ``{NORMALIZED_TICKER: CIK}`` (e.g. from ``cik_resolver.resolve_ciks``).
    Returns per-year + overall resolution, the total ticker-years (each ~= one
    10-K filing), and a capped sample of unresolved tickers.
    """
    per_year: list[dict] = []
    ticker_years = 0
    for year, sub in oos_us.groupby("year"):
        tickers = sorted(set(sub["ticker_norm"]))
        n_resolved = sum(1 for t in tickers if t in cmap)
        per_year.append(
            {
                "year": int(year),
                "n_distinct": len(tickers),
                "n_resolved": n_resolved,
                "rate": round(n_resolved / len(tickers), 4) if tickers else 0.0,
            }
        )
        ticker_years += n_resolved  # resolved ticker-years ~= annual 10-Ks
    all_tickers = sorted(set(oos_us["ticker_norm"]))
    n_all = len(all_tickers)
    n_resolved_all = sum(1 for t in all_tickers if t in cmap)
    unresolved = [t for t in all_tickers if t not in cmap][:_UNRESOLVED_SAMPLE_N]
    return {
        "window": f"{int(oos_us['year'].min())}-{int(oos_us['year'].max())}",
        "n_distinct_tickers": n_all,
        "n_resolved": n_resolved_all,
        "resolution_rate": round(n_resolved_all / n_all, 4) if n_all else 0.0,
        "ticker_years_resolved": int(ticker_years),
        "per_year": per_year,
        "unresolved_sample": unresolved,
    }


def project_token_cost(
    resolution: dict,
    *,
    tokens_per_10k: int = _TOKENS_PER_10K_DEFAULT,
    train_years: int = _TRAIN_YEARS_DEFAULT,
    train_universe: int | None = None,
) -> dict:
    """G2: projected one-time token cost for the 10-K MD&A extraction backfill.

    OOS-window filings are counted exactly from ``resolution['ticker_years_resolved']``
    (each resolved ticker-year ~= one 10-K). Train-window filings are estimated as
    ``train_universe x train_years`` (default train_universe = the OOS distinct
    count, a conservative large-cap floor). Cost is one-time: an idempotent
    accession-keyed cache means re-runs make zero LLM calls.
    """
    oos_filings = int(resolution["ticker_years_resolved"])
    t_universe = train_universe if train_universe is not None else resolution["n_distinct_tickers"]
    train_filings = int(t_universe) * int(train_years)
    total_filings = oos_filings + train_filings
    total_tokens = total_filings * int(tokens_per_10k)
    return {
        "tokens_per_10k": int(tokens_per_10k),
        "oos_filings": oos_filings,
        "train_filings": train_filings,
        "train_universe_assumed": int(t_universe),
        "train_years": int(train_years),
        "total_filings": total_filings,
        "total_tokens": int(total_tokens),
        "tokens_millions": round(total_tokens / 1_000_000, 2),
        "one_time": True,  # idempotent cache; re-runs cost zero LLM tokens
    }


def summarize(resolution: dict, projection: dict) -> dict:
    """Combine G1 + G2 into a gate verdict (green/amber/red) + recommendation."""
    rate = resolution["resolution_rate"]
    g1 = "green" if rate >= _COVERAGE_GATE else ("amber" if rate >= 0.70 else "red")
    # Token gate: green if projected < 20M (tractable), amber < 50M, red above.
    mtok = projection["tokens_millions"]
    g2 = "green" if mtok < 20 else ("amber" if mtok < 50 else "red")
    return {
        "g1_cik_resolution": {"gate": g1, "rate": rate, "threshold": _COVERAGE_GATE},
        "g2_token_cost": {"gate": g2, "tokens_millions": mtok},
        "verdict": (
            "FEASIBLE — both gates green; proceed to PROPOSED prereg + owner GO."
            if g1 == "green" and g2 == "green"
            else "REVIEW — at least one gate amber/red; scope down or reconsider."
        ),
        "note": (
            "PIT-coverage + projected-cost only. Does NOT measure real per-call "
            "token cost or temp=0 stability; run --measure-llm with creds to "
            "calibrate. No OOS rank-IC observed; no ledger; Track LLM PROPOSED."
        ),
    }


def _measure_llm_sample(n: int) -> dict:  # pragma: no cover - needs creds + network
    """G3/G4: real per-call token cost + temp=0 stability on ``n`` sampled 10-K excerpts.

    Needs provider creds in ``.env`` and network. Samples ``n`` resolved CIKs,
    fetches one recent 10-K MD&A excerpt each (polite, via http_policy), calls the
    GLM router twice at temperature=0 with the frozen filings-tone prompt, and
    reports mean prompt/completion tokens + the agreement rate between the two
    calls. Intended to CALIBRATE ``tokens_per_10k`` and confirm determinism.
    """
    raise NotImplementedError(
        "G3/G4 real-LLM measurement is implemented at freeze time (needs creds + "
        "the frozen extraction prompt). Run the local G1+G2 pilot without "
        "--measure-llm for the coverage + projected-cost verdict."
    )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--oos", type=Path, default=_OOS_PATH, help="OOS scores parquet")
    ap.add_argument(
        "--measure-llm",
        type=int,
        default=0,
        help="also run real-LLM G3/G4 on N sample tickers (needs creds)",
    )
    ap.add_argument("--tokens-per-10k", type=int, default=_TOKENS_PER_10K_DEFAULT)
    ap.add_argument("--train-years", type=int, default=_TRAIN_YEARS_DEFAULT)
    args = ap.parse_args()

    oos_us = _load_oos_us(args.oos)
    # resolve_ciks reads the cached SEC snapshot (one-time polite fetch if absent).
    cmap = resolve_ciks(sorted(set(oos_us["ticker_norm"])))
    resolution = measure_cik_resolution(oos_us, cmap)
    projection = project_token_cost(
        resolution, tokens_per_10k=args.tokens_per_10k, train_years=args.train_years
    )
    summary = summarize(resolution, projection)
    out = {"g1_resolution": resolution, "g2_projection": projection, "summary": summary}
    print(json.dumps(out, indent=2))

    if args.measure_llm:
        _measure_llm_sample(args.measure_llm)  # pragma: no cover


if __name__ == "__main__":
    main()
