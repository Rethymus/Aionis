"""RES-02 baseline-FF5 runner — BASELINE-FF5-001 purged cross-fitted CV.

Exploratory baseline enhancement (owner-gated, ``tasks/active/TASK-RES-02-
baseline-ff5.md``): the frozen Phase B nine numeric-fundamental columns plus
the eleven STOCK-SPECIFIC FF5/DFF exposure and interaction columns
(``aionis.features.ff5``). Evidence strength identical to frozen B/C/D/E1:
5-fold PurgedGroupKFold (group=month, embargo=21 sessions), frozen LightGBM,
n_jobs=1, seed 0.

Pipeline: cached Phase B prices/fundamentals/universe -> ensure FF5 + DFF
snapshots (politeness >=2s, fail closed) -> daily returns -> month-end rolling
exposures -> filed-date-PIT stock features -> loading interactions -> PIT
broadcast to the session grid -> RD-13 per-month diagnostics (fail closed;
market-wide raw factor columns are structurally excluded) -> purged cross-fit.

LEDGER DISCIPLINE (inviolable): this runner NEVER appends to
``runs/ledger.jsonl`` — the ledger row is the owner's, written only AFTER
authorizing the trial and BEFORE any result is observed (config_committed
BEFORE result). The runner therefore refuses to run unless a
``config_committed`` row for BASELINE-FF5-001 with the EXACT config sig
already exists. For H6 reproducibility checks: ``RES_02_NO_LEDGER=1`` runs
without any ledger requirement (sig-match guard applied when the row exists).

Real-data run (NOT hermetic — never run in CI/tests):
    uv run python scripts/res_02_baseline_ff5_run.py
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from aionis.config import settings
from aionis.eval.learner import FROZEN_PARAMS
from aionis.eval.rank_ic import rank_ic_monthly, rank_ic_summary
from aionis.eval.two_arm import compute_shared_folds, run_arm_oos
from aionis.features.alignment import nyse_sessions
from aionis.features.ff5 import (
    ALL_FEATURE_COLS,
    BETA_MIN_OBS,
    BETA_WINDOW,
    asset_growth_from_filings,
    broadcast_monthly_exposures,
    build_ff5_interactions,
    rd13_diagnostics,
    rd13_filter_columns,
    rolling_factor_exposures,
    verdict_rollup,
)
from aionis.ingest.ff5 import fetch_ff5_daily_snapshot
from aionis.ingest.fundamentals import _DEFAULT_END_LAG, pit_align
from aionis.ingest.macro_dff import dff_daily_changes, fetch_dff_vintages
from aionis.ingest.universe import load_pierrebrunelle_membership

CACHE = settings.data_dir / "cache"
HORIZON = 21
N_SPLITS = 5
EMBARGO = 21
TRIAL_ID = "BASELINE-FF5-001"
CV_SCHEME = (
    "5-fold PurgedGroupKFold (group=month, embargo=21 sessions) over the "
    "resolvable window; evidence strength identical to frozen B/C/D/E1"
)

# Frozen Phase B numeric fundamentals (unchanged — the differential anchor).
FROZEN_FEATURE_COLS = [
    "mktcap", "pb_ratio", "roa",
    "fund_assets", "fund_revenue", "fund_net_income",
    "fund_equity", "fund_shares_out", "fund_long_term_debt",
]
# The eleven stock-specific columns (aionis.features.ff5) — RD-13-gated.
NEW_FEATURE_COLS = list(ALL_FEATURE_COLS)

FUND_METRICS = ["assets", "equity", "net_income", "shares_out", "long_term_debt"]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else ""


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")


def _versions() -> dict:
    import arch
    import lightgbm
    import purgedcv

    return {
        "lightgbm": lightgbm.__version__,
        "purgedcv": purgedcv.__version__,
        "arch": arch.__version__,
    }


def _ledger() -> list[dict]:
    ledger_path = Path("runs/ledger.jsonl")
    if not ledger_path.exists():
        return []
    rows = []
    for line in ledger_path.read_text().splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def _load_cached() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    fund = pd.read_parquet(CACHE / "phase_b_fundamentals.parquet")
    px = pd.read_parquet(CACHE / "phase_b_prices.parquet")
    mem = load_pierrebrunelle_membership()
    return fund, px, mem


def _daily_returns(px: pd.DataFrame) -> pd.DataFrame:
    """Per-ticker daily decimal returns from the wide adjusted-close panel."""
    rets = px.pct_change()
    rets = rets.iloc[1:]
    return rets.dropna(axis=1, how="all")


def _month_ends(sessions: pd.DatetimeIndex) -> pd.DatetimeIndex:
    """The last session of each calendar month (the exposure computation grid)."""
    ends = sessions.to_series().groupby(sessions.to_period("M")).max()
    return pd.DatetimeIndex(ends)


def _stock_features(
    fund: pd.DataFrame,
    px: pd.DataFrame,
    month_ends: pd.DatetimeIndex,
    tickers: list[str],
) -> pd.DataFrame:
    """PIT stock features at month-ends: (date, ticker) frame of
    mktcap / pb_ratio / roa / fund_* / asset_growth (all filed-date aligned)."""
    panels = pit_align(fund, month_ends, tickers, metrics=FUND_METRICS)
    close = px.reindex(month_ends)[tickers]

    def wide_to_mi(wide: pd.DataFrame, name: str) -> pd.DataFrame:
        wide.index.name = "date"
        wide.columns.name = "ticker"
        return wide.stack().to_frame(name)

    parts: list[pd.DataFrame] = []
    for metric in FUND_METRICS:
        parts.append(wide_to_mi(panels[metric], f"fund_{metric}"))

    sh = panels["shares_out"].reindex(index=month_ends, columns=tickers)
    eq = panels["equity"].reindex(index=month_ends, columns=tickers)
    ni = panels["net_income"].reindex(index=month_ends, columns=tickers)
    ass = panels["assets"].reindex(index=month_ends, columns=tickers)
    mktcap = close * sh
    pb = (close * sh / eq).where((sh > 0) & (eq > 0))
    roa = (ni / ass).where(ass > 0)
    parts.append(wide_to_mi(mktcap, "mktcap"))
    parts.append(wide_to_mi(pb, "pb_ratio"))
    parts.append(wide_to_mi(roa, "roa"))

    growth = asset_growth_from_filings(fund, month_ends, tickers)
    parts.append(wide_to_mi(growth, "asset_growth"))

    joined = pd.concat(parts, axis=1)
    return joined.sort_index()


def build_config(
    passing_cols: list[str],
    ff5_sha: str,
    dff_sha: str,
    analysis_start: str = "2015-07-01",
) -> dict:
    """The complete frozen config for this trial; its sha256 is the anchor the
    owner commits to the ledger BEFORE any result is observed.

    ``analysis_start`` is the earliest month-end exposure date (2015-07-01 —
    DFF vintages begin 2015-01-01 + a 126-session beta warm-up; owner decision
    2026-08-03 option A). It is part of the frozen config so the window is
    auditable in the ledger row.
    """
    return {
        "trial_id": TRIAL_ID,
        "mode": "exploratory",  # FF5 G3 (no vintages) -> snapshot-frozen exploratory
        "analysis_start": analysis_start,
        "feature_cols": FROZEN_FEATURE_COLS + passing_cols,
        "frozen_feature_cols": FROZEN_FEATURE_COLS,
        "new_feature_cols": passing_cols,
        "horizon": HORIZON,
        "n_splits": N_SPLITS,
        "embargo_sessions": EMBARGO,
        "cv_scheme": CV_SCHEME,
        "frozen_params": FROZEN_PARAMS,
        "end_lag_months": _DEFAULT_END_LAG,
        "beta_window_days": BETA_WINDOW,
        "beta_min_obs": BETA_MIN_OBS,
        "versions": _versions(),
        "fund_sha256": _sha(CACHE / "phase_b_fundamentals.parquet"),
        "prices_sha256": _sha(CACHE / "phase_b_prices.parquet"),
        "membership_sha256": _sha(CACHE / "universe_pierrebrunelle.parquet"),
        "ff5_daily_snapshot_sha256": ff5_sha,
        "dff_alfred_cache_sha256": dff_sha,
        "uv_lock_sha256": _sha(Path("uv.lock")),
    }


def _config_sig(config: dict) -> str:
    return hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()


def _require_owner_commit(config: dict, sig: str) -> None:
    """config_committed BEFORE result: abort unless the owner's ledger row
    for BASELINE-FF5-001 carries the exact sig."""
    rows = _ledger()
    for r in rows:
        if r.get("event") != "config_committed":
            continue
        cfg = r.get("config") or {}
        if cfg.get("trial_id") != TRIAL_ID:
            continue
        if r.get("config_sig") == sig:
            print(f"[RES-02] owner config_committed row found (sig={sig})", flush=True)
            return
    raise SystemExit(
        f"[RES-02] ABORT: no config_committed ledger row for {TRIAL_ID} with the "
        f"exact config sig {sig}. The owner must authorize the trial and append "
        "the config_committed row (config_committed BEFORE result) before this "
        "runner may observe anything. Use RES_02_NO_LEDGER=1 only for H6 "
        "reproducibility checks."
    )


def main() -> None:
    artifacts_only = os.environ.get("RES_02_NO_LEDGER") == "1"
    if settings.fred_api_key is None:
        raise SystemExit("[RES-02] ABORT: FRED_API_KEY missing (DFF ALFRED fetch requires it)")

    fund, px, mem = _load_cached()
    print(f"[RES-02] fund rows={len(fund)}  prices={px.shape}  membership={mem.shape}", flush=True)
    tickers = [c for c in px.columns if isinstance(c, str) and c.isupper()]

    # --- snapshot-first data (G3/G4): FF5 daily + DFF ALFRED vintages --------
    ff5, ff5_sha = fetch_ff5_daily_snapshot(CACHE)
    print(f"[RES-02] FF5 daily snapshot rows={len(ff5)} sha256={ff5_sha}", flush=True)
    vintages = fetch_dff_vintages(settings.fred_api_key, CACHE)
    dff_sha = _sha(CACHE / "alfred_DFF.json")
    print(f"[RES-02] DFF vintages={len(vintages)} cache sha256={dff_sha}", flush=True)

    # --- session grid + month-end exposure dates -----------------------------
    sessions = nyse_sessions(px.index.min(), px.index.max())
    month_ends = _month_ends(sessions)
    print(f"[RES-02] sessions={len(sessions)} month_ends={len(month_ends)}", flush=True)

    # --- ANALYSIS WINDOW (owner decision 2026-08-03, option A) ---------------
    # DFF vintages only exist from 2015-01-01 (FRED ALFRED earliest vintage,
    # verified). The first valid month-end exposure is 2015-07-31 (2015-01-02
    # + 126-observation beta minimum warm-up + month-end). Sessions before that
    # month-end get NO broadcast value (broadcast_monthly_exposures yields NaN
    # before the first month-end — structurally expected), and RD-13 fail-closes
    # ANY month with ALL_MISSING. The analysis window therefore starts the day
    # AFTER the first month-end (2015-08-01): from there every session carries a
    # broadcast value. IMPORTANT: month_ends must be computed from the FULL
    # session grid (before the window filter) so the first month-end (2015-07-31)
    # still produces the exposure that fills August via the broadcast.
    # Option B (drop DFF) is NOT selected — the owner approved A; RD-13 still
    # auto-excludes any column that fails within the window.
    analysis_start = pd.Timestamp("2015-08-01")
    month_ends = _month_ends(sessions)
    sessions = sessions[sessions >= analysis_start]
    print(
        f"[RES-02] ANALYSIS WINDOW: {analysis_start.date()} -> "
        f"{sessions.max().date()}  sessions={len(sessions)} month_ends={len(month_ends)}",
        flush=True,
    )

    # --- daily returns + factor frame (ΔDFF as-of, one-day lagged) -----------
    rets = _daily_returns(px)
    dff_chg = dff_daily_changes(rets.index, vintages)
    factors = ff5.set_index("date").join(dff_chg, how="left")
    factors.index = pd.DatetimeIndex(factors.index).normalize()
    print(f"[RES-02] returns={rets.shape} factors={factors.shape}", flush=True)

    # --- A: rolling exposures (stock-specific, 252d window, min 126 obs) -----
    exposures = rolling_factor_exposures(rets, factors, month_ends)
    print(f"[RES-02] exposures={exposures.shape}", flush=True)

    # --- PIT stock features at month-ends ------------------------------------
    stock = _stock_features(fund, px, month_ends, tickers)
    print(f"[RES-02] stock features={stock.shape}", flush=True)

    # --- B: loading × stock-feature interactions -----------------------------
    interactions = build_ff5_interactions(exposures, stock)
    monthly = exposures.join(interactions)
    print(f"[RES-02] monthly feature panel={monthly.shape}", flush=True)

    # --- PIT broadcast to the session grid (no same-month future) ------------
    broadcast = broadcast_monthly_exposures(monthly, sessions)
    print(f"[RES-02] broadcast panel={broadcast.shape}", flush=True)

    # --- RD-13 per-month cross-sectional variation gate (fail closed) --------
    diag = rd13_diagnostics(broadcast)
    passing, failing = rd13_filter_columns(diag, NEW_FEATURE_COLS)
    print("\n[RES-02] RD-13 verdict rollup:")
    print(verdict_rollup(diag, NEW_FEATURE_COLS).to_string(index=False))
    if failing:
        print("[RES-02] RD-13 FAIL-CLOSED columns (excluded from config):")
        for col, reasons in failing.items():
            shown = reasons[:3]
            suffix = "..." if len(reasons) > 3 else ""
            print(f"  {col}: {len(reasons)} failing months -> {shown}{suffix}")
    if not passing:
        raise SystemExit(
            "[RES-02] BLOCKED: every new column failed RD-13 — STOP per "
            "TASK-RES-02 失败处理 (needs owner design input); no config written."
        )

    # --- frozen config + owner ledger gate (config_committed BEFORE result) ---
    config = build_config(passing, ff5_sha, dff_sha, analysis_start=str(analysis_start.date()))
    sig = _config_sig(config)
    n_cols = len(config["feature_cols"])
    print(f"[RES-02] config sig={sig}  feature_cols={n_cols}", flush=True)
    if os.environ.get("RES_02_SIG_ONLY") == "1":
        print(
            "[RES-02] RES_02_SIG_ONLY=1 — sig printed; EXITING BEFORE any "
            "out-of-sample metric (config_committed-before-result discipline)",
            flush=True,
        )
        # The exact ledger row the owner must append (copy-paste ready).
        print(
            "\n[RES-02] LEDGER ROW (append to runs/ledger.jsonl):\n"
            + json.dumps(
                {
                    "event": "config_committed",
                    "phase": "baseline_ff5",
                    "config_sig": sig,
                    "config": config,
                },
                indent=2,
            ),
            flush=True,
        )
        return
    if not artifacts_only:
        _require_owner_commit(config, sig)
    else:
        print("[RES-02] RES_02_NO_LEDGER=1 reproducibility mode", flush=True)

    # --- purged cross-fitted CV (same evidence strength as frozen B/C/D/E1) --
    folds, ref = compute_shared_folds(px, mem, HORIZON, N_SPLITS, EMBARGO)
    print(f"[RES-02] shared folds={len(folds)}  ref rows={len(ref)}", flush=True)
    ef = broadcast.reset_index()  # [date, ticker, <new cols>] — left join, columns only
    panel = run_arm_oos(
        px, fund, mem, HORIZON, config["feature_cols"], "filed", folds, ref,
        extra_features=ef,
    )
    ic = rank_ic_monthly(panel, "score", "y_fwd_ret")
    summary = rank_ic_summary(ic)
    print(
        f"[RES-02] BASELINE-FF5-001 CV-proxy mean_IC={summary['mean_ic']:.4f} "
        f"ci_half={summary['ci_half']:.4f} t_hac={summary['t_hac']:.3f} "
        f"n_months={summary['n']}", flush=True
    )

    # --- H6 determinism (IC series AND raw scores bit-identical) -------------
    panel2 = run_arm_oos(
        px, fund, mem, HORIZON, config["feature_cols"], "filed", folds, ref,
        extra_features=ef,
    )
    ic2 = rank_ic_monthly(panel2, "score", "y_fwd_ret")
    det_ok = bool(
        np.array_equal(ic.to_numpy(), ic2.to_numpy())
        and _scores_equal(panel, panel2)
    )
    print(f"[RES-02] H6 deterministic (IC + raw scores) = {det_ok}", flush=True)

    print(
        "\n[RES-02] DONE — exploratory only. The owner must now append the "
        f"trial registry entry for {TRIAL_ID} (evals/trials/) and, if this "
        "config is frozen, the config_committed ledger row (already required "
        "for the run above). No ledger row was written by this runner.",
        flush=True,
    )


def _scores_equal(a: pd.DataFrame, b: pd.DataFrame) -> bool:
    sa = a.set_index(["date", "ticker"])["score"].sort_index()
    sb = b.set_index(["date", "ticker"])["score"].sort_index()
    if not sa.index.equals(sb.index):
        return False
    return np.array_equal(sa.to_numpy(), sb.to_numpy())


if __name__ == "__main__":
    sys.exit(main())
