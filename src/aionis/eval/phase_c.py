"""Phase C first confirmatory run — world-state surprise BUNDLE vs fundamentals-only.

Mirrors :mod:`scripts.phase_b_run`'s anti-leakage discipline but swaps the arm
axis: Phase B varied fundamental *timing* (filed vs period-end+lag); Phase C fixes
``align_on="end_lag"`` for BOTH arms and varies the *feature set* — ``arm_base``
is Phase B's frozen fundamentals-only baseline; ``arm_macro`` adds the world-state
surprise bundle {CPI/NFP macro-surprise (date-broadcast) + VIX-surprise
(date-broadcast) + earnings-surprise (per-(ticker, date))}. The two arms share
prices / universe / folds / learner / fundamental timing, so the rank-IC
differential isolates the bundle's contribution (phase-c-preregistration §1).

Anti-leakage anchors (same as Phase B, enforced not aspirational):
  * HIGH-1 — ``config_committed`` is written to the ledger BEFORE any result.
  * HIGH-2 — the bundle-shuffle placebo perturbs ``arm_macro`` ONLY (``arm_base``
    stays real); both reuse the shared folds.
  * HIGH-3 — the CV scheme is part of the pre-committed config; individual-arm ICs
    are CV-proxy, the differential is the OOS claim.
  * HIGH-4 — ``config_sig`` covers versions + frozen params + bundle column names
    + all input shas, so same sig => bit-identical reruns.
  * MEDIUM-7 — H6 compares both the IC series AND the raw score arrays.

The orchestration lives here (importable + unit-testable); ``scripts/phase_c_run``
is a thin wrapper that loads the real cached data and calls :func:`run_confirmatory`.
"""
from __future__ import annotations

import datetime
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from aionis.eval.metrics import diebold_mariano_mbb
from aionis.eval.multiple_testing import harvey_liu_haircut
from aionis.eval.phase_c_controls import (
    shuffle_date_broadcast,
    shuffle_earnings_across_tickers,
)
from aionis.eval.rank_ic import rank_ic_monthly, rank_ic_summary
from aionis.eval.two_arm import compute_shared_folds, run_arm_oos
from aionis.features.earnings_surprise import (
    earnings_surprise_as_of,
    earnings_surprise_long,
)
from aionis.features.macro_surprise import macro_surprise_date_broadcast
from aionis.features.selection_panel import fama_french_daily
from aionis.features.vix_surprise import vix_surprise_panel

# --- frozen protocol constants (mirror Phase B; pinned for H6 determinism) ----

HORIZON = 21
N_SPLITS = 5
EMBARGO = 21
VIX_KIND = "ar"  # AR(p) residual surprise (not the simple delta) — pre-reg §8
PUBLISH_CI_HALF = 0.015  # pre-reg §7 publishability gate on the differential
Z95 = 1.959963985

FEATURE_COLS = [
    "mktcap", "pb_ratio", "roa",
    "fund_assets", "fund_revenue", "fund_net_income",
    "fund_equity", "fund_shares_out", "fund_long_term_debt",
]
BUNDLE_COLS = [
    "macro_cpi_surprise", "macro_nfp_surprise", "vix_surprise", "earnings_surprise",
]
SANITY_COL = "ff_mkt_rf"  # the "already-priced" calibration anchor (pre-reg §5 #3)
# Multiple-testing family: Phase B (1) + Phase C bundle (1) = 2 confirmatory
# claims; 5/20 bracket conservative exploratory breadth.
N_TRIALS_GRID = (1, 2, 5, 20)


# --- small helpers -----------------------------------------------------------


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else ""


def _versions() -> dict:
    import arch
    import lightgbm
    import purgedcv

    return {
        "lightgbm": lightgbm.__version__,
        "purgedcv": purgedcv.__version__,
        "arch": arch.__version__,
    }


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")


def append_ledger(entry: dict, ledger_path: str | Path) -> None:
    with open(ledger_path, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")


def _scores_equal(a: pd.DataFrame, b: pd.DataFrame) -> bool:
    sa = a.set_index(["date", "ticker"])["score"].sort_index()
    sb = b.set_index(["date", "ticker"])["score"].sort_index()
    if not sa.index.equals(sb.index):
        return False
    return np.array_equal(sa.to_numpy(), sb.to_numpy())


# --- bundle construction (networked: macro via cached ALFRED, VIX via FRED) ---


def build_bundle(
    fund: pd.DataFrame, px: pd.DataFrame, fred_api_key: str, cache_dir: Path,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Assemble the surprise bundle the runner injects into ``arm_macro``.

    Returns ``(bundle_broadcast, earnings_long)``:
      * ``bundle_broadcast`` — date-indexed frame ``[macro_cpi_surprise,
        macro_nfp_surprise, vix_surprise]`` (date-broadcast, via ``macro=``).
      * ``earnings_long`` — long ``[date, ticker, earnings_surprise]`` (per-(ticker,
        date), via ``extra_features=``).

    Macro surprises come from the cached ALFRED vintages (cache hit -> no HTTP);
    VIX-surprise from ``vix_as_of`` (fetches VIXCLS vintages on first call);
    earnings-surprise is a pure transform of the PIT fundamentals (no new data).
    """
    sessions = pd.DatetimeIndex(sorted(px.index)).normalize()
    macro_cpi = macro_surprise_date_broadcast(
        "CPIAUCSL", sessions, fred_api_key, cache_dir, name="macro_cpi_surprise",
    )
    macro_nfp = macro_surprise_date_broadcast(
        "PAYEMS", sessions, fred_api_key, cache_dir, name="macro_nfp_surprise",
    )
    vix = vix_surprise_panel(sessions, kind=VIX_KIND, cache_dir=cache_dir).rename("vix_surprise")
    bundle_broadcast = pd.concat([macro_cpi, macro_nfp, vix], axis=1)

    surprise_long = earnings_surprise_long(fund)
    wide = earnings_surprise_as_of(surprise_long, sessions, list(px.columns))
    earnings_long = (
        wide.stack().rename("earnings_surprise").reset_index()
        .rename(columns={"level_0": "date", "level_1": "ticker"})
    )
    earnings_long["date"] = pd.to_datetime(earnings_long["date"]).dt.normalize()
    return bundle_broadcast, earnings_long


def build_sanity(px: pd.DataFrame) -> pd.DataFrame:
    """FF5 ``Mkt-RF`` as a date-broadcast calibration anchor (pre-reg §5 #3).

    A widely-known, already-priced factor added to its own arm SHOULD show only a
    limited IC increment over ``arm_base`` — calibrating that the test can detect
    'priced -> no increment', so a bundle null is consistent with efficient pricing
    rather than a dead test.
    """
    ff = fama_french_daily(str(px.index.min().date()), str(px.index.max().date()))
    return ff[[SANITY_COL]].copy()


# --- config + ledger anchor --------------------------------------------------


def build_config(shas: dict, bundle_meta: dict) -> dict:
    """The complete frozen config (HIGH-4). Its sha256 is the durable anchor."""
    cfg = {
        "phase": "C",
        "feature_cols": FEATURE_COLS,
        "bundle_cols": BUNDLE_COLS,
        "sanity_col": SANITY_COL,
        "vix_kind": VIX_KIND,
        "horizon": HORIZON,
        "n_splits": N_SPLITS,
        "embargo_sessions": EMBARGO,
        "frozen_params": _frozen_params(),
        "publish_ci_half": PUBLISH_CI_HALF,
        "multiple_testing_family_n": 2,
        "n_trials_grid": list(N_TRIALS_GRID),
        "versions": _versions(),
    }
    cfg.update(shas)
    cfg.update(bundle_meta)
    return cfg


def _frozen_params() -> dict:
    from aionis.eval.learner import FROZEN_PARAMS

    return FROZEN_PARAMS


def commit_config(config: dict, ledger_path: str | Path) -> str:
    """HIGH-1: write ``config_committed`` to the ledger BEFORE any result."""
    sig = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()
    append_ledger(
        {"ts": _now(), "event": "config_committed", "phase": "C",
         "config_sig": sig, "config": config},
        ledger_path,
    )
    return sig


# --- differential + multiple-testing ----------------------------------------


def differential(ic_a: pd.Series, ic_b: pd.Series) -> dict:
    """rank-IC differential ``ic_a - ic_b`` with HAC CI + moving-block-bootstrap DM.

    The CI half-width (Newey-West HAC SE of the mean differential, ``1.96 * se``)
    is the pre-reg §7 publishability gate. DM is on the loss differential
    (``-ic`` so higher IC = lower loss), one cluster per month.
    """
    common = ic_a.index.intersection(ic_b.index)
    s = ic_a.loc[common].to_numpy(dtype=float)
    b = ic_b.loc[common].to_numpy(dtype=float)
    diff = pd.Series(s - b, index=common, name="ic_diff")
    summ = rank_ic_summary(diff)
    groups = np.arange(len(common))
    dm = diebold_mariano_mbb(-s, -b, groups, horizon=1)
    mean_diff = float(summ["mean_ic"])
    ci_half = float(summ["ci_half"])
    return {
        "n_months": int(len(common)),
        "mean_diff": mean_diff,
        "se_hac": float(summ["se_hac"]),
        "ci_half": ci_half,
        "ci_lo": mean_diff - ci_half,
        "ci_hi": mean_diff + ci_half,
        "dm_stat": dm["stat"],
        "dm_p_mbb": dm["p_value"],
        "dm_flag": dm["flag"],
        "publishable_ci_half": bool(ci_half < PUBLISH_CI_HALF),
    }


def haircut_table(summary: dict) -> dict:
    """Harvey-Liu haircut on the arm's IC t-stat across the trial grid.

    A non-positive t-stat already fails the one-sided skill test (no correction
    needed); a positive one is shrunk by Bonferroni over ``n_trials``.
    """
    se = float(summary.get("se_hac") or 1e-12)
    sharpe = float(summary["mean_ic"]) / se
    n = int(summary.get("n", 0))
    out: dict[int, dict] = {}
    for nt in N_TRIALS_GRID:
        if sharpe > 0:
            h = harvey_liu_haircut(sharpe, nt, n)
            out[nt] = {"haircut_sharpe": float(h["haircut_sharpe"]),
                       "survives": bool(h["survives_bonferroni"])}
        else:
            out[nt] = {"haircut_sharpe": sharpe, "survives": False}
    return out


# --- the orchestrator (pure compute on injected data + bundle) ---------------


def _arm_ic(
    fund: pd.DataFrame, px: pd.DataFrame, mem: pd.DataFrame,
    folds, ref, feature_cols: list[str], align_on: str, params: dict,
    *, horizon: int, macro: pd.DataFrame | None = None,
    extra: pd.DataFrame | None = None,
) -> tuple[pd.Series, dict, pd.DataFrame]:
    panel = run_arm_oos(
        px, fund, mem, horizon, feature_cols, align_on, folds, ref, params,
        macro=macro, extra_features=extra,
    )
    ic = rank_ic_monthly(panel, "score", "y_fwd_ret")
    return ic, rank_ic_summary(ic), panel


def run_confirmatory(
    fund: pd.DataFrame, px: pd.DataFrame, mem: pd.DataFrame,
    *,
    bundle_broadcast: pd.DataFrame, earnings_long: pd.DataFrame,
    sanity_broadcast: pd.DataFrame, config: dict, sig: str,
    feature_cols: list[str] | None = None, bundle_cols: list[str] | None = None,
    sanity_col: str = SANITY_COL, horizon: int = HORIZON,
    n_splits: int = N_SPLITS, embargo: int = EMBARGO, params: dict | None = None,
    ledger_path: str | Path | None = None, results_base: str | Path | None = None,
) -> dict:
    """Run the full Phase C confirmatory pipeline on injected data + bundle.

    No network — every fetchable (macro/VIX/earnings/FF) is pre-built by the
    caller (:func:`build_bundle` / :func:`build_sanity` in ``main``; synthetic
    frames in the hermetic test). Order: shared folds -> arm_base + arm_macro ->
    differential -> H6 re-run -> bundle-shuffle placebo + sanity + leave-one-out ->
    multiple-testing haircut -> (``save_run`` if ``results_base``) ->
    (``confirmatory:first`` ledger row if ``ledger_path``, AFTER ``config_committed``).
    """
    from aionis.reporting import results

    feature_cols = FEATURE_COLS if feature_cols is None else feature_cols
    bundle_cols = BUNDLE_COLS if bundle_cols is None else bundle_cols
    params = _frozen_params() if params is None else params

    folds, ref = compute_shared_folds(px, mem, horizon, n_splits, embargo)

    # --- headline (CV-proxy individual-arm ICs; the differential is the OOS claim)
    ic_b, sum_b, pan_b = _arm_ic(
        fund, px, mem, folds, ref, feature_cols, "end_lag", params, horizon=horizon,
    )
    ic_m, sum_m, pan_m = _arm_ic(
        fund, px, mem, folds, ref, feature_cols + bundle_cols, "end_lag", params,
        horizon=horizon, macro=bundle_broadcast, extra=earnings_long,
    )
    diff = differential(ic_m, ic_b)

    # --- H6 determinism (IC series AND raw scores, both arms)
    ic_b2, _, pan_b2 = _arm_ic(
        fund, px, mem, folds, ref, feature_cols, "end_lag", params, horizon=horizon,
    )
    ic_m2, _, pan_m2 = _arm_ic(
        fund, px, mem, folds, ref, feature_cols + bundle_cols, "end_lag", params,
        horizon=horizon, macro=bundle_broadcast, extra=earnings_long,
    )
    h6 = bool(
        np.array_equal(ic_m.to_numpy(), ic_m2.to_numpy())
        and np.array_equal(ic_b.to_numpy(), ic_b2.to_numpy())
        and _scores_equal(pan_m, pan_m2) and _scores_equal(pan_b, pan_b2)
    )

    # --- controls (HIGH-2: arm_macro perturbed, arm_base REAL, shared folds)
    ic_p, _, _ = _arm_ic(
        fund, px, mem, folds, ref, feature_cols + bundle_cols, "end_lag", params,
        horizon=horizon, macro=shuffle_date_broadcast(bundle_broadcast),
        extra=shuffle_earnings_across_tickers(earnings_long),
    )
    placebo = differential(ic_p, ic_b)
    ic_s, sum_s, _ = _arm_ic(
        fund, px, mem, folds, ref, feature_cols + [sanity_col], "end_lag", params,
        horizon=horizon, macro=sanity_broadcast,
    )
    sanity = differential(ic_s, ic_b)

    # --- leave-one-out attribution (exploratory, NOT a gate; pre-reg §5 #5)
    loo: dict[str, dict] = {}
    for drop in bundle_cols:
        keep_macro = (
            bundle_broadcast.drop(columns=[drop])
            if drop in bundle_broadcast.columns else bundle_broadcast
        )
        keep_cols = [c for c in feature_cols + bundle_cols if c != drop]
        keep_extra = None if drop == "earnings_surprise" else earnings_long
        ic_l, _, _ = _arm_ic(
            fund, px, mem, folds, ref, keep_cols, "end_lag", params, horizon=horizon,
            macro=keep_macro, extra=keep_extra,
        )
        loo[drop] = differential(ic_l, ic_b)

    mt = {"arm_macro": haircut_table(sum_m), "arm_base": haircut_table(sum_b)}
    controls = {
        "bundle_shuffle_placebo": placebo,
        "sanity_mkt_rf": sanity,
        "leave_one_out": loo,
    }

    # save_run artifacts (base=None -> the default project runs dir, matching
    # Phase B; passing an explicit base hermetically redirects for tests).
    results.save_run(
        sig, ic_state=ic_m, ic_base=ic_b, summary_state=sum_m, summary_base=sum_b,
        differential=diff, controls=controls, config=config,
        h6_deterministic=h6, base=results_base,
    )

    result = {
        "config_sig": sig,
        "arm_macro_cvproxy": sum_m,
        "arm_base_cvproxy": sum_b,
        "sanity_arm_cvproxy": sum_s,
        "differential_macro_minus_base": diff,
        "H6_deterministic": h6,
        "controls": controls,
        "multiple_testing_haircut": mt,
        "n_trials_grid": list(N_TRIALS_GRID),
        "notes": (
            "Individual-arm ICs are CV-proxy (5-fold, not forward-OOS); the §1 "
            "DIFFERENTIAL is the OOS claim. Controls perturb arm_macro only "
            "(arm_base real, shared folds). Bundle-shuffle placebo scrambles every "
            "bundle component's alignment; sanity adds the priced Mkt-RF; "
            "leave-one-out is exploratory attribution (NOT a gate). ic_state=arm_macro, "
            "ic_base=arm_base in the saved artifacts (Phase B-named files reused)."
        ),
    }
    if ledger_path is not None:
        append_ledger(
            {"ts": _now(), "event": "confirmatory:first", "phase": "C", **result},
            ledger_path,
        )
    return result
