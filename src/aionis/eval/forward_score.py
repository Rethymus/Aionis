"""E3 Slice 4 - forward scoring + accumulation core.

Implements the per-prediction realized-return fetch (4a), the reveal+score pipeline (4b),
and the forward IC series accumulator with differential inference (4c).

Consumes verified seams (does not modify them):
  * aionis.reporting.forward_ledger.reveal_forward_outcome (I1-gated, idempotent)
  * aionis.reporting.forward_ledger.read_forward_rows
  * aionis.eval.rank_ic.rank_ic_monthly / rank_ic_summary
  * aionis.eval.metrics.diebold_mariano_mbb
  * aionis.eval.phase_e1.differential (pattern mirror)

Slice 4 scope: scoring+accumulation CORE. The writer (4d) + runner (4e) + invariant suite (4f)
are the NEXT pass — do NOT implement them here.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
from scipy.stats import spearmanr

from aionis.reporting import forward_ledger as FL


def fetch_realized_forward_returns(
    predict_ts: str,
    target_t: str,
    tickers: list[str],
    *,
    prices_path: Path | str,
) -> pd.DataFrame:
    """Load cached wide price parquet and compute forward returns for given tickers.

    For each ticker in ``tickers``, computes ``y = price[target_t]/price[predict_ts] - 1``.
    Returns a LONG frame ``[ticker, y_fwd_ret]`` with tickers that have prices at BOTH
    endpoints (no imputation; missing tickers are dropped).

    PIT note: Prices are unrevised PIT snapshots cached by Phase B (``phase_b_prices.parquet``).
    ``predict_ts`` and ``target_t`` are NYSE session timestamps. This function does NOT look
    beyond ``target_t`` — it only slices the price parquet at the two timestamps.
    """
    prices = pd.read_parquet(prices_path)

    # Normalize timestamps to pd.Timestamp for indexing
    # Strip timezone info for comparison with price index (which is typically timezone-naive)
    predict_dt = pd.Timestamp(predict_ts).tz_localize(None)
    target_dt = pd.Timestamp(target_t).tz_localize(None)

    # Ensure both timestamps exist in the price index
    if predict_dt not in prices.index or target_dt not in prices.index:
        return pd.DataFrame(columns=["ticker", "y_fwd_ret"])

    # Extract prices at the two timestamps
    price_predict = prices.loc[predict_dt, tickers]
    price_target = prices.loc[target_dt, tickers]

    # Build result frame with tickers that have BOTH prices
    valid_mask = price_predict.notna() & price_target.notna()
    valid_tickers = [t for t, v in zip(tickers, valid_mask, strict=True) if v]

    if not valid_tickers:
        return pd.DataFrame(columns=["ticker", "y_fwd_ret"])

    y_fwd = price_target[valid_tickers] / price_predict[valid_tickers] - 1.0

    return pd.DataFrame({
        "ticker": valid_tickers,
        "y_fwd_ret": y_fwd.to_numpy(dtype=float),
    })


def reveal_and_score_forward_month(
    commit_row: dict,
    *,
    prices_path: Path | str,
    runs_dir: Path | str,
    now: str | None = None,
) -> dict:
    """Reveal and score ONE forward month for both arms.

    Extracts ``predict_ts, target_t, config_sha256`` from the commit row, loads the
    scores parquet (LONG ``[ticker, arm, score]``), and for EACH arm (``arm_base``,
    ``arm_e13``): fetches realized returns (4a) → joins on ticker → computes the
    ``ic_point`` (Spearman across tickers at predict_ts), then calls
    :func:`reveal_forward_outcome` with the computed IC.

    The I1 gate (now < target_t) is checked BEFORE attempting to compute IC, since
    computing IC requires fetching returns which may fail if timestamps don't exist.

    Returns a dict mapping arm name to the reveal result dict.
    """
    from datetime import timezone

    predict_ts = commit_row["predict_ts"]
    target_t = commit_row["target_t"]
    config_sha256 = commit_row["config_sha256"]

    # Parse timestamps for I1 gate check
    target_dt = pd.Timestamp(target_t)
    now_dt = pd.Timestamp(now) if now else pd.Timestamp.now(tz=timezone.utc)

    # Check I1 gate ONCE for both arms (before any computation)
    if now_dt < target_dt:
        # Both arms refused by I1 gate
        return {
            "arm_base": {
                "revealed": False,
                "reason": (
                    f"before_target_t: wall-clock now={now_dt.isoformat(timespec='seconds')} "
                    f"< target_t={target_t}; the forward outcome has not realized yet (I1). "
                    "Reveal refused."
                ),
                "predict_ts": predict_ts,
                "target_t": target_t,
                "config_sha256": config_sha256,
            },
            "arm_e13": {
                "revealed": False,
                "reason": (
                    f"before_target_t: wall-clock now={now_dt.isoformat(timespec='seconds')} "
                    f"< target_t={target_t}; the forward outcome has not realized yet (I1). "
                    "Reveal refused."
                ),
                "predict_ts": predict_ts,
                "target_t": target_t,
                "config_sha256": config_sha256,
            },
        }

    # Load scores parquet
    scores_path = Path(runs_dir) / commit_row["scores_path"]
    scores = pd.read_parquet(scores_path)

    results = {}

    for arm in ("arm_base", "arm_e13"):
        # Extract scores for this arm
        arm_scores = scores[scores["arm"] == arm][["ticker", "score"]]

        # Fetch realized returns for tickers in this arm
        tickers = arm_scores["ticker"].tolist()
        fwd_ret = fetch_realized_forward_returns(
            predict_ts=predict_ts,
            target_t=target_t,
            tickers=tickers,
            prices_path=prices_path,
        )

        if len(fwd_ret) == 0:
            # No valid returns → cannot compute IC
            results[arm] = {
                "revealed": False,
                "reason": (
                    f"no_valid_returns: no tickers with prices at both "
                    f"predict_ts and target_t for arm={arm}"
                ),
            }
            continue

        # Join scores with realized returns
        merged = arm_scores.merge(fwd_ret, on="ticker", how="inner")

        if len(merged) < 2:
            # Need at least 2 tickers to compute rank correlation
            results[arm] = {
                "revealed": False,
                "reason": (
                    f"insufficient_tickers: only {len(merged)} tickers with "
                    f"valid scores and returns for arm={arm}"
                ),
            }
            continue

        # Compute Spearman rank-IC
        ic_point, _ = spearmanr(merged["score"], merged["y_fwd_ret"])

        # Call reveal_forward_outcome (handles idempotency I2)
        reveal_result = FL.reveal_forward_outcome(
            target_t=target_t,
            ic_point=float(ic_point),
            arm=arm,
            predict_ts=predict_ts,
            config_sha256=config_sha256,
            runs_dir=runs_dir,
            now=now,
        )

        results[arm] = reveal_result

    return results


def accumulate_forward_ic_series(
    *,
    config_sha256: str,
    runs_dir: Path | str,
) -> dict:
    """Accumulate forward IC series and compute differential inference.

    Reads ``forward_outcome_scored`` rows for the given config, builds per-arm
    monthly IC Series (index=predict_ts month, value=ic_point), aligns arms on
    common months, computes the differential ``ic_forward = ic_e13 - ic_base``,
    and applies ``rank_ic_summary`` + ``diebold_mariano_mbb`` for inference.

    Mirrors the pattern from :func:`eval.phase_e1.differential`.

    Returns a dict with:
        * ``ic_forward``: pd.Series of differential IC (e13 - base)
        * ``summary``: dict with keys from differential (
          mean_diff, se_hac, ci_half, ci_lo, ci_hi, dm_stat, dm_p_mbb,
          dm_flag, n_months, publishable_ci_half)
        * ``n_months``: int number of common months
        * ``publishable_ci_half``: bool whether CI half-width < 0.015
    """
    import numpy as np

    from aionis.eval.metrics import diebold_mariano_mbb
    from aionis.eval.phase_e1 import PUBLISH_CI_HALF
    from aionis.eval.rank_ic import rank_ic_summary

    # Read scored rows
    scored_rows = FL.read_forward_rows(
        runs_dir=runs_dir,
        config_sha256=config_sha256,
        event=FL.EVENT_SCORED,
    )

    if not scored_rows:
        return {
            "ic_forward": pd.Series(name="ic_diff", dtype=float),
            "summary": {
                "mean_diff": float("nan"),
                "se_hac": float("nan"),
                "ci_half": float("nan"),
                "ci_lo": float("nan"),
                "ci_hi": float("nan"),
                "dm_stat": float("nan"),
                "dm_p_mbb": 1.0,
                "dm_flag": "degenerate",
                "n_months": 0,
                "publishable_ci_half": False,
            },
            "n_months": 0,
            "publishable_ci_half": False,
        }

    # Build per-arm IC series
    # Group by (predict_ts, arm) and extract ic_point
    df = pd.DataFrame(scored_rows)

    # Filter to only the two arms we care about
    df = df[df["arm"].isin(["arm_base", "arm_e13"])].copy()

    # Parse predict_ts to month-end for indexing
    df["month"] = pd.to_datetime(df["predict_ts"]).dt.to_period("M")

    # Build series per arm
    ic_base = df[df["arm"] == "arm_base"].groupby("month")["ic_point"].first()
    ic_e13 = df[df["arm"] == "arm_e13"].groupby("month")["ic_point"].first()

    # Align on common months
    common_months = ic_base.index.intersection(ic_e13.index)

    if len(common_months) == 0:
        return {
            "ic_forward": pd.Series(name="ic_diff", dtype=float),
            "summary": {
                "mean_diff": float("nan"),
                "se_hac": float("nan"),
                "ci_half": float("nan"),
                "ci_lo": float("nan"),
                "ci_hi": float("nan"),
                "dm_stat": float("nan"),
                "dm_p_mbb": 1.0,
                "dm_flag": "degenerate",
                "n_months": 0,
                "publishable_ci_half": False,
            },
            "n_months": 0,
            "publishable_ci_half": False,
        }

    # Extract aligned series
    s_base = ic_base.loc[common_months].to_numpy(dtype=float)
    s_e13 = ic_e13.loc[common_months].to_numpy(dtype=float)

    # Compute differential
    ic_forward = pd.Series(s_e13 - s_base, index=common_months, name="ic_diff")

    # Apply rank_ic_summary (NW-HAC inference on differential)
    summ = rank_ic_summary(ic_forward)

    # Apply diebold_mariano_mbb (-s_e13, -s_base) → DM on negative ICs = loss comparison
    # (higher IC → lower loss, so we negate to treat as losses)
    groups = np.arange(len(common_months))
    dm = diebold_mariano_mbb(-s_e13, -s_base, groups=groups, horizon=1)

    mean_diff = float(summ["mean_ic"])
    ci_half = float(summ["ci_half"])

    return {
        "ic_forward": ic_forward,
        "summary": {
            "mean_diff": mean_diff,
            "se_hac": float(summ["se_hac"]),
            "ci_half": ci_half,
            "ci_lo": mean_diff - ci_half,
            "ci_hi": mean_diff + ci_half,
            "dm_stat": dm["stat"],
            "dm_p_mbb": dm["p_value"],
            "dm_flag": dm["flag"],
            "n_months": len(common_months),
            "publishable_ci_half": bool(ci_half < PUBLISH_CI_HALF),
        },
        "n_months": len(common_months),
        "publishable_ci_half": bool(ci_half < PUBLISH_CI_HALF),
    }
