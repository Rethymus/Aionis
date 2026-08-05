"""EXPLORATORY bps-cost sensitivity sweep of the Track B treatment L-S lens.

Sister script to :mod:`scripts.track_b_net_cost_run` (mount②). That runner fixes
``bps=5`` (S&P 500 liquid scenario); this script sweeps a grid of per-dollar-traded
slippage assumptions to show how the after-cost per-period Sharpe decays as costs
rise. Exploratory economic-validity lens — NOT a confirmatory claim, NOT a changed
research config (the underlying OOS score panel is unchanged; only the SCENARIO
cost assumption varies). Writes ONLY to ``runs/`` (gitignored); NEVER to
``runs/ledger.jsonl``.

Reuses :func:`aionis.eval.net_cost.net_cost_summary` per bps (no wheel reinvention);
the cost model is turnover-based and does NOT require daily open prices
(``long_short_returns`` subsamples the daily ``oos_state.parquet`` to month-end,
``rebalance="monthly"``).

The decay curve strengthens the null-favored narrative: if the gross-null L-S
Sharpe collapses to ~0 well before realistic costs, the "no tradable alpha"
conclusion is robust to cost assumption — independent of the rank-IC null itself.

Usage::

    uv run python scripts/track_b_net_cost_sweep_run.py              # default grid, latest run
    uv run python scripts/track_b_net_cost_sweep_run.py --bps 0,2,5,10,20,50
    uv run python scripts/track_b_net_cost_sweep_run.py --run-sig <sig>
    PHASE_B_NO_LEDGER=1 uv run python scripts/track_b_net_cost_sweep_run.py
"""
from __future__ import annotations

import argparse
import glob
import os
import sys

import pandas as pd
import structlog

from aionis.eval.net_cost import net_cost_summary

log = structlog.get_logger()

OUT_PATH = "runs/track_b_net_cost_sweep.parquet"

# Default grid: 0 (gross) -> realistic S&P 500 -> stressed. 1 bps = 0.01%.
DEFAULT_BPS_GRID = (0.0, 1.0, 2.0, 5.0, 10.0, 20.0, 50.0)


def _latest_oos_state() -> str | None:
    """Most recently modified treatment OOS panel under runs/results/."""
    paths = sorted(glob.glob("runs/results/*/oos_state.parquet"), key=os.path.getmtime)
    return paths[-1] if paths else None


def _parse_bps(s: str) -> tuple[float, ...]:
    """Parse a comma-separated bps list into a sorted tuple of non-negative floats."""
    vals: list[float] = []
    for tok in s.split(","):
        tok = tok.strip()
        if not tok:
            continue
        v = float(tok)
        if v < 0:
            raise ValueError(f"Negative bps rejected ({v}); must be non-negative scenario.")
        vals.append(v)
    if not vals:
        raise ValueError("Empty bps grid.")
    return tuple(sorted(set(vals)))


def _print_table(rows: list[dict]) -> None:
    print("\n=== bps-cost sensitivity sweep (exploratory; gross -> net Sharpe decay) ===",
          flush=True)
    print(f"{'bps':>5} | {'gross_sharpe':>12} | {'net_sharpe':>10} | "
          f"{'avg_turnover':>12} | {'total_cost_bps':>14} | {'n_rebal':>7}", flush=True)
    print("-" * 75, flush=True)
    gross0 = rows[0]["gross_sharpe"] if rows else float("nan")
    for r in rows:
        print(f"{r['bps']:>5.1f} | {r['gross_sharpe']:>12.4f} | {r['net_sharpe']:>10.4f} | "
              f"{r['avg_turnover']:>12.4f} | {r['total_cost_bps']:>14.1f} | "
              f"{r['n_rebalance']:>7}", flush=True)
    # break-even bps: the bps at which net_sharpe crosses 0 (linear interp between grid pts)
    be = _break_even_bps(rows)
    if be is None:
        print("[S] break-even bps (net_sharpe == 0): not crossed within the grid "
              "(strategy retains positive net Sharpe across all assumed costs)", flush=True)
    else:
        print(f"[S] break-even bps (net_sharpe == 0): ~{be:.2f} bps per dollar traded", flush=True)
    if gross0 and rows:
        print(f"[S] reference: gross_sharpe {gross0:.4f} is identical across bps by construction "
              "(costs affect net only)", flush=True)


def _break_even_bps(rows: list[dict]) -> float | None:
    """First bps at which net_sharpe crosses from positive to non-positive (linear interp).

    Returns ``None`` if net_sharpe stays positive across the whole grid. If net_sharpe
    is already non-positive at bps=0 (gross itself <= 0), returns 0.0.
    """
    ordered = sorted(rows, key=lambda r: r["bps"])
    if not ordered:
        return None
    if ordered[0]["net_sharpe"] <= 0:
        return float(ordered[0]["bps"])
    for prev, cur in zip(ordered, ordered[1:], strict=False):
        if prev["net_sharpe"] > 0 and cur["net_sharpe"] <= 0:
            slope = (cur["net_sharpe"] - prev["net_sharpe"]) / (cur["bps"] - prev["bps"])
            if slope == 0:
                return float(cur["bps"])
            return float(prev["bps"] - prev["net_sharpe"] / slope)
    return None


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--bps",
        default=",".join(str(b) for b in DEFAULT_BPS_GRID),
        help=f"comma-separated non-negative bps grid (default: {DEFAULT_BPS_GRID})",
    )
    ap.add_argument("--quantile", type=float, default=0.2, help="leg size fraction (default 0.2)")
    ap.add_argument("--run-sig", default=None, help="specific runs/results/<sig> (default: latest)")
    args = ap.parse_args()

    bps_grid = _parse_bps(args.bps)
    if args.run_sig:
        panel_path = f"runs/results/{args.run_sig}/oos_state.parquet"
    else:
        panel_path = _latest_oos_state() or ""

    if not panel_path or not os.path.exists(panel_path):
        print(f"[ERROR] No oos_state.parquet found ({panel_path or 'none'}). "
              "Run scripts/track_b_a_run.py first to persist the Track B treatment OOS panel.",
              file=sys.stderr)
        sys.exit(1)

    oos_panel = pd.read_parquet(panel_path)
    print(f"[S] panel: {panel_path}  shape={oos_panel.shape}  "
          f"n_dates={oos_panel['date'].nunique()}  n_tickers={oos_panel['ticker'].nunique()}",
          flush=True)
    print(f"[S] bps grid: {bps_grid}  quantile={args.quantile}", flush=True)
    print("[S] long_short_returns subsamples to month-end (rebalance=monthly)", flush=True)

    rows: list[dict] = []
    for bps in bps_grid:
        m = net_cost_summary(oos_panel, bps=bps, quantile=args.quantile)
        rows.append({
            "bps": bps,
            "quantile": args.quantile,
            "gross_sharpe": m.gross_sharpe,
            "net_sharpe": m.net_sharpe,
            "avg_turnover": m.avg_turnover,
            "total_cost_bps": m.total_cost_bps,
            "n_rebalance": m.n_rebalance,
            "gross_max_drawdown": m.gross_max_drawdown,
            "gross_annual_volatility": m.gross_annual_volatility,
            "panel": panel_path,
        })
        print(f"[S]   bps={bps:>5.1f}  net_sharpe={m.net_sharpe:+.4f}  "
              f"avg_turnover={m.avg_turnover:.4f}  total_cost_bps={m.total_cost_bps:.1f}",
              flush=True)

    _print_table(rows)

    out = pd.DataFrame(rows)
    out.to_parquet(OUT_PATH)
    print(f"\n[S] wrote {OUT_PATH} ({len(rows)} rows)", flush=True)
    print("[S] DONE (exploratory; never writes ledger)", flush=True)


if __name__ == "__main__":
    if os.environ.get("PHASE_B_NO_LEDGER") == "1":
        print("[S] ARTIFACTS-ONLY (exploratory; never writes ledger)", flush=True)
    main()
