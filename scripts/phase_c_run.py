"""Phase C first confirmatory run — thin wrapper around :mod:`aionis.eval.phase_c`.

Loads the Phase B frozen data (fundamentals / prices / membership) + cached
ALFRED/VIX, builds the surprise bundle, commits the config (sha256 BEFORE any
result — the durable anti-leakage anchor), then runs the confirmatory pipeline
and persists artifacts via ``reporting.results.save_run``.

Run:  uv run python scripts/phase_c_run.py   (background-safe; ~7 arm passes)

This script is intentionally minimal: every testable decision lives in
``aionis.eval.phase_c`` so the hermetic test exercises the real pipeline.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from aionis.config import settings
from aionis.eval.phase_c import (
    BUNDLE_COLS,
    FEATURE_COLS,
    SANITY_COL,
    VIX_KIND,
    build_bundle,
    build_config,
    build_sanity,
    commit_config,
    run_confirmatory,
)
from aionis.features.anomaly_audit import anomaly_summary, price_anomalies
from aionis.ingest.universe import load_pierrebrunelle_membership

CACHE = settings.data_dir / "cache"
LEDGER = "runs/ledger.jsonl"


def _sha(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else ""


def _input_shas(cache: Path) -> dict[str, str]:
    """sha256 anchors over the run's ACTUAL input files (audit P1-2).

    The VIX surprise is built by ``build_bundle`` -> ``vix_surprise_panel`` ->
    ``vix_as_of`` -> ``fetch_vix_vintages``, which reads ``alfred_VIXCLS.json``
    (the self-dated vintage cache) — NOT ``vix_cls.parquet`` (the realized-series
    cache written by ``fetch_vix``, an inspection-only path). The corrected
    anchor is therefore a NEW key (``vix_vintages_sha256``); the legacy
    ``vix_sha256`` (parquet) is kept because the ledger contract is add-only —
    never a silent key swap.
    """
    return {
        "fund_sha256": _sha(cache / "phase_b_fundamentals.parquet"),
        "prices_sha256": _sha(cache / "phase_b_prices.parquet"),
        "membership_sha256": _sha(cache / "universe_pierrebrunelle.parquet"),
        "uv_lock_sha256": _sha(Path("uv.lock")),
        "alfred_cpiaucsl_sha256": _sha(cache / "alfred_CPIAUCSL.json"),
        "alfred_payems_sha256": _sha(cache / "alfred_PAYEMS.json"),
        "vix_sha256": _sha(cache / "vix_cls.parquet"),
        "vix_vintages_sha256": _sha(cache / "alfred_VIXCLS.json"),
    }


def main() -> None:
    import hashlib
    import json
    import os

    # PHASE_C_NO_LEDGER=1 -> reproducibility rerun (pre-reg §9): rebuild the SAME
    # config (H6 -> identical sig + IC) and save_run artifacts, but write NOTHING
    # to the ledger (the confirmatory:first headline is already locked). Used to
    # regenerate dashboard artifacts without polluting the headline.
    artifacts_only = os.environ.get("PHASE_C_NO_LEDGER") == "1"

    fund = pd.read_parquet(CACHE / "phase_b_fundamentals.parquet")
    px = pd.read_parquet(CACHE / "phase_b_prices.parquet")
    mem = load_pierrebrunelle_membership()

    # reliability mechanism ⑥: audit the price panel before trusting the IC
    anoms = price_anomalies(px)
    audit = anomaly_summary(anoms, n_tickers=px.shape[1])
    print(f"[C] fund rows={len(fund)}  prices={px.shape}  membership={mem.shape}",
          flush=True)
    print(f"[C] price anomaly audit: flagged {audit['n_flagged']}/{audit['n_tickers']} "
          f"tickers; by_anomaly={audit['by_anomaly']}", flush=True)

    bundle_broadcast, earnings_long = build_bundle(fund, px, settings.fred_api_key, CACHE)
    sanity_broadcast = build_sanity(px)
    print(f"[C] bundle_broadcast={bundle_broadcast.shape}  "
          f"earnings_long={earnings_long.shape}  sanity={sanity_broadcast.shape}",
          flush=True)

    shas = _input_shas(CACHE)
    bundle_meta = {
        "vix_surprise_kind": VIX_KIND,
        "earnings_eps_num": "net_income",
        "earnings_eps_den": "shares_out",
        "price_anomaly_audit": audit,
        "feature_cols_pinned": FEATURE_COLS,
        "bundle_cols_pinned": BUNDLE_COLS,
        "sanity_col_pinned": SANITY_COL,
    }
    config = build_config(shas, bundle_meta)
    if artifacts_only:
        sig = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()
        print(f"[C] ARTIFACTS-ONLY rerun (no ledger write); sig={sig}", flush=True)
    else:
        sig = commit_config(config, LEDGER)  # HIGH-1: BEFORE any result
        print(f"[C] config_committed sig={sig}  (logged BEFORE result)", flush=True)

    result = run_confirmatory(
        fund, px, mem,
        bundle_broadcast=bundle_broadcast, earnings_long=earnings_long,
        sanity_broadcast=sanity_broadcast, config=config, sig=sig,
        ledger_path=None if artifacts_only else LEDGER, results_base=None,
    )

    d = result["differential_macro_minus_base"]
    pl = result["controls"]["bundle_shuffle_placebo"]
    san = result["controls"]["sanity_mkt_rf"]
    print(
        f"[C] arm_macro(CV-proxy) mean_IC={result['arm_macro_cvproxy']['mean_ic']:.4f} "
        f"t_hac={result['arm_macro_cvproxy']['t_hac']:.3f}", flush=True,
    )
    print(
        f"[C] arm_base (CV-proxy) mean_IC={result['arm_base_cvproxy']['mean_ic']:.4f} "
        f"t_hac={result['arm_base_cvproxy']['t_hac']:.3f}", flush=True,
    )
    print(
        f"[C] differential macro-base: mean={d['mean_diff']:.4f} "
        f"DM p_mbb={d['dm_p_mbb']:.4f} ci_half={d['ci_half']:.4f} "
        f"(publishable={d['publishable_ci_half']}) n={d['n_months']}", flush=True,
    )
    print(
        f"[C] bundle-shuffle placebo: mean={pl['mean_diff']:.4f} "
        f"DM p_mbb={pl['dm_p_mbb']:.4f} (must vanish if signal is real)", flush=True,
    )
    print(
        f"[C] sanity (Mkt-RF): mean={san['mean_diff']:.4f} "
        f"(calibration: priced factor -> limited increment)", flush=True,
    )
    print(f"[C] H6 deterministic (IC + raw scores) = {result['H6_deterministic']}", flush=True)
    loo = result["controls"]["leave_one_out"]
    loo_str = ", ".join(f"{k}={v['mean_diff']:+.4f}" for k, v in loo.items())
    print(f"[C] leave-one-out: {loo_str}", flush=True)
    print(f"[C] logged confirmatory:first (config_sig={sig})", flush=True)
    print("[C] DONE", flush=True)


if __name__ == "__main__":
    main()
