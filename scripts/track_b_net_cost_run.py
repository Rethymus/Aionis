"""Track B net-cost runner — mount② exploratory utility (no ledger write).

Loads the Track B treatment OOS score panel (``oos_state.parquet`` persisted by
``aionis.reporting.results.save_run``) and computes the after-cost per-period Sharpe
(linear-bps slippage on monthly turnover). Exploratory lens, NOT a confirmatory claim.
Writes ONLY to ``runs/`` (gitignored); NEVER to ``runs/ledger.jsonl``.

The cost model is turnover-based and does NOT require daily open prices.
``long_short_returns`` subsamples a daily panel to month-end cross-sections automatically
(rebalance="monthly"), so the daily ``oos_state.parquet`` is a valid input.

Usage::

    uv run python scripts/track_b_net_cost_run.py                   # latest run, bps=5
    uv run python scripts/track_b_net_cost_run.py --bps 10          # scenario sensitivity
    uv run python scripts/track_b_net_cost_run.py --run-sig <sig>   # specific run
    PHASE_B_NO_LEDGER=1 uv run python scripts/track_b_net_cost_run.py   # explicit artifacts-only
"""
from __future__ import annotations

import argparse
import glob
import os
import sys

import pandas as pd
import structlog

from aionis.eval.net_cost import NetCostMetrics, net_cost_summary

log = structlog.get_logger()

OUT_PATH = "runs/track_b_net_cost.parquet"


def _latest_oos_state() -> str | None:
    """Most recently modified treatment OOS panel under runs/results/."""
    paths = sorted(glob.glob("runs/results/*/oos_state.parquet"), key=os.path.getmtime)
    return paths[-1] if paths else None


def _infer_freq(n_dates: int, span_days: int) -> str:
    """Coarse frequency label for the loaded panel (informational only)."""
    if span_days <= 0:
        return "unknown"
    per_day = n_dates / span_days
    if per_day > 0.5:
        return "daily"
    if per_day > 0.1:
        return "weekly"
    return "monthly"


def _print_metrics(m: NetCostMetrics, bps: float, quantile: float) -> None:
    print(f"[S] net-cost (bps={bps}, quantile={quantile}):", flush=True)
    print(f"[S]   gross_sharpe  (per-period)  = {m.gross_sharpe:.4f}", flush=True)
    print(f"[S]   net_sharpe    (per-period)  = {m.net_sharpe:.4f}", flush=True)
    print(f"[S]   avg_turnover  (one-way)     = {m.avg_turnover:.4f}", flush=True)
    print(f"[S]   total_cost_bps (cumulative) = {m.total_cost_bps:.1f}", flush=True)
    print(f"[S]   n_rebalance                 = {m.n_rebalance}", flush=True)
    print(f"[S]   gross_max_drawdown          = {m.gross_max_drawdown:.4f}", flush=True)
    print(f"[S]   gross_annual_volatility     = {m.gross_annual_volatility:.4f}", flush=True)


def main() -> None:
    """Run Track B net-cost evaluation on the persisted treatment OOS panel."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--bps",
        type=float,
        default=5.0,
        help="slippage bps per dollar traded (default 5 = S&P 500 liquid scenario)",
    )
    ap.add_argument("--quantile", type=float, default=0.2, help="leg size fraction (default 0.2)")
    ap.add_argument(
        "--run-sig",
        default=None,
        help="specific runs/results/<sig> (default: most recent run)",
    )
    args = ap.parse_args()

    if args.run_sig:
        panel_path = f"runs/results/{args.run_sig}/oos_state.parquet"
    else:
        panel_path = _latest_oos_state() or ""

    if not panel_path or not os.path.exists(panel_path):
        print(
            "[ERROR] No oos_state.parquet found under runs/results/. "
            "Run scripts/track_b_a_run.py first to persist the Track B treatment OOS panel.",
            file=sys.stderr,
        )
        sys.exit(1)

    oos_panel = pd.read_parquet(panel_path)
    dates = pd.to_datetime(oos_panel["date"])
    n_dates = int(oos_panel["date"].nunique())
    span_days = int((dates.max() - dates.min()).days)
    freq = _infer_freq(n_dates, span_days)

    log.info(
        "net_cost_panel_loaded",
        path=panel_path,
        shape=list(oos_panel.shape),
        n_dates=n_dates,
        n_tickers=int(oos_panel["ticker"].nunique()),
        span_days=span_days,
        inferred_freq=freq,
    )
    print(
        f"[S] panel: {panel_path}  shape={oos_panel.shape} n_dates={n_dates} "
        f"n_tickers={oos_panel['ticker'].nunique()} inferred_freq={freq}",
        flush=True,
    )
    print("[S] long_short_returns subsamples to month-end (rebalance=monthly)", flush=True)

    metrics = net_cost_summary(oos_panel, bps=args.bps, quantile=args.quantile)
    _print_metrics(metrics, args.bps, args.quantile)

    # Write to gitignored runs/ (NEVER to ledger).
    out = pd.DataFrame(
        [
            {
                "bps": args.bps,
                "quantile": args.quantile,
                "panel": panel_path,
                "gross_sharpe": metrics.gross_sharpe,
                "net_sharpe": metrics.net_sharpe,
                "avg_turnover": metrics.avg_turnover,
                "total_cost_bps": metrics.total_cost_bps,
                "n_rebalance": metrics.n_rebalance,
                "gross_max_drawdown": metrics.gross_max_drawdown,
                "gross_annual_volatility": metrics.gross_annual_volatility,
            }
        ]
    )
    out.to_parquet(OUT_PATH)
    print(f"[S] wrote {OUT_PATH}", flush=True)
    print("[S] DONE", flush=True)


if __name__ == "__main__":
    if os.environ.get("PHASE_B_NO_LEDGER") == "1":
        print("[S] ARTIFACTS-ONLY (exploratory; never writes ledger)", flush=True)
    main()
