"""Track B net-cost runner — mount② exploratory utility (no ledger write).

Evaluates the Track B treatment OOS scores with execution costs applied.
This is an exploratory lens, NOT a confirmatory claim. The runner loads Track B
OOS scores + daily session opens, prints net-cost metrics, and writes ONLY to
runs/ (gitignored). NEVER writes to runs/ledger.jsonl.

Data dependency: requires daily open prices per ticker. If phase_b_prices.parquet
or a sibling daily-opens cache does not contain an 'open' column, the runner
fails-closed with a clear message: "daily opens not found; owner-gated fetch
required."

Run:  uv run python scripts/track_b_net_cost_run.py

Environment variable:
    PHASE_B_NO_LEDGER=1 — reproducibility mode (artifacts only, no ledger write).
        This is the default for exploratory utilities.
"""
from __future__ import annotations

import os
import sys

import pandas as pd
import structlog

from aionis.config import settings

log = structlog.get_logger()

CACHE = settings.data_dir / "cache"
TRACK_B_RESULTS = "runs/track_b_net_cost.parquet"


def main() -> None:
    """Run Track B net-cost evaluation.

    Loads:
      * Track B treatment OOS scores (from aionis.eval.two_arm.run_arm_oos)
      * Daily session opens (wide DataFrame, index=dates, columns=tickers)

    Prints net-cost metrics to console and writes to runs/track_b_net_cost.parquet.
    """
    # Check for daily opens cache
    daily_opens_path = CACHE / "phase_b_daily_opens.parquet"

    if not daily_opens_path.exists():
        # Fall back to phase_b_prices.parquet and check for 'open' column
        prices_path = CACHE / "phase_b_prices.parquet"
        if not prices_path.exists():
            log.error(
                "price_cache_missing",
                path=str(prices_path),
                error="phase_b_prices.parquet not found. Run scripts/phase_b_fetch.py first.",
            )
            print(
                "[ERROR] Price cache not found. Run scripts/phase_b_fetch.py first.",
                file=sys.stderr,
            )
            sys.exit(1)

        prices = pd.read_parquet(prices_path)
        if "open" not in prices.columns:
            log.error(
                "daily_opens_missing",
                path=str(prices_path),
                columns=list(prices.columns),
                error=(
                    "Daily open prices not cached. phase_b_prices.parquet contains "
                    f"{list(prices.columns)} only. Owner-gated fetch required to add "
                    "'open' column (Tiingo/Alpaca EOD provide open)."
                ),
            )
            print(
                f"[ERROR] Daily opens not found in cache. {prices_path} has columns: "
                f"{list(prices.columns)}. Owner-gated fetch required to add 'open' column.",
                file=sys.stderr,
            )
            sys.exit(1)

        # Has 'open' column — use it as session_opens
        session_opens = prices
    else:
        # Use dedicated daily opens cache if available
        session_opens = pd.read_parquet(daily_opens_path)

    print(
        f"[S] loaded session_opens: {session_opens.shape} "
        f"(dates={len(session_opens.index)}, tickers={len(session_opens.columns)})",
        flush=True,
    )

    # Load Track B OOS scores
    # TODO: this should load the actual Track B treatment OOS panel from
    # aionis.eval.two_arm.run_arm_oos. For now, fail-closed with a clear message.
    log.error(
        "oos_panel_not_loaded",
        error=(
            "Track B OOS panel not loaded. This is a TODO — the runner should load "
            "the actual OOS score panel from aionis.eval.two_arm.run_arm_oos or from "
            "a cached parquet file. Current implementation is incomplete."
        ),
    )
    print(
        "[ERROR] Track B OOS panel not loaded. TODO: implement loading from "
        "aionis.eval.two_arm.run_arm_oos or cached parquet.",
        file=sys.stderr,
    )
    sys.exit(1)

    # When OOS panel is available, uncomment the following:
    # oos_panel = pd.read_parquet(CACHE / "track_b_oos_scores.parquet")
    # print(f"[S] loaded OOS panel: {oos_panel.shape}", flush=True)

    # Compute net-cost metrics with default bps=5.0 (S&P 500 liquid scenario)
    # metrics = net_cost_summary(
    #     oos_panel,
    #     session_opens,
    #     bps=5.0,
    #     quantile=0.2,
    # )

    # Print results
    # print(f"[S] Net-cost metrics (bps=5.0):", flush=True)
    # print(f"[S]   gross_sharpe={metrics.gross_sharpe:.3f}", flush=True)
    # print(f"[S]   net_sharpe={metrics.net_sharpe:.3f}", flush=True)
    # print(f"[S]   avg_turnover={metrics.avg_turnover:.4f}", flush=True)
    # print(f"[S]   total_cost_bps={metrics.total_cost_bps:.1f}", flush=True)
    # print(f"[S]   n_rebalance={metrics.n_rebalance}", flush=True)
    # print(f"[S]   gross_max_drawdown={metrics.gross_max_drawdown:.3f}", flush=True)
    # print(f"[S]   gross_annual_volatility={metrics.gross_annual_volatility:.3f}", flush=True)

    # Write to gitignored runs/ directory
    # pd.DataFrame([{
    #     "gross_sharpe": metrics.gross_sharpe,
    #     "net_sharpe": metrics.net_sharpe,
    #     "avg_turnover": metrics.avg_turnover,
    #     "total_cost_bps": metrics.total_cost_bps,
    #     "n_rebalance": metrics.n_rebalance,
    #     "gross_max_drawdown": metrics.gross_max_drawdown,
    #     "gross_annual_volatility": metrics.gross_annual_volatility,
    # }]).to_parquet(TRACK_B_RESULTS)
    # print(f"[S] wrote {TRACK_B_RESULTS}", flush=True)

    print("[S] DONE", flush=True)


if __name__ == "__main__":
    # Check for PHASE_B_NO_LEDGER environment variable
    artifacts_only = os.environ.get("PHASE_B_NO_LEDGER") == "1"

    if artifacts_only:
        print(
            "[S] ARTIFACTS-ONLY mode (no ledger write); net-cost runner is exploratory",
            flush=True,
        )

    main()
