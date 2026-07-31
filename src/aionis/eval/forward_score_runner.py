"""E3 Slice 4e - forward score runner (main entry).

Standalone runner that reads forward_outcome_scored rows, accumulates the
forward IC series, and persists the forward results artifacts.

Mirrors the pattern of ``scripts.phase_e1_run.py`` and
``scripts.forward_commit.py`` (thin shim over a library function).
"""
from __future__ import annotations

from pathlib import Path

import structlog

from aionis.eval.forward_score import accumulate_forward_ic_series
from aionis.reporting.forward_ledger import EVENT_SCORED, read_forward_rows
from aionis.reporting.forward_results import save_forward_run
from aionis.reporting.results import DEFAULT_RUNS_DIR

log = structlog.get_logger()


def main(
    *,
    config_sig: str,
    runs_dir: Path | str | None = None,
    prices_path: Path | str | None = None,
    force: bool = False,
) -> None:
    """Run forward scoring: accumulate IC series and save forward results.

    Args:
        config_sig: the config signature to process.
        runs_dir: override the runs directory (for hermetic tests).
        prices_path: REQUIRED path to prices parquet (not used in this slice,
            but kept for API compatibility with the scoring pipeline).
        force: if True, allow rewriting existing forward artifacts (mirrors
            save_run's idempotent overwrites).

    Workflow:
        1. Read ``forward_outcome_scored`` rows for the given config_sig.
        2. Call ``accumulate_forward_ic_series`` to build the differential IC series.
        3. Call ``save_forward_run`` to persist artifacts.
        4. Print structured ``[E3-score]`` lines for monitoring.

    I9: forward artifacts are written ONLY under ``runs/forward/``; the
    published-null dirs ``runs/results/<sig>/`` are never touched.
    """
    if runs_dir is None:
        runs_dir = DEFAULT_RUNS_DIR
    else:
        runs_dir = Path(runs_dir)

    # Log start
    print(f"[E3-score] START config_sig={config_sig}", flush=True)

    # Step 1: Read scored rows
    scored_rows = read_forward_rows(
        runs_dir=runs_dir,
        config_sha256=config_sig,
        event=EVENT_SCORED,
    )

    if not scored_rows:
        print(
            f"[E3-score] NO_SCORED_ROWS config_sig={config_sig} - nothing to accumulate",
            flush=True,
        )
        return

    print(
        f"[E3-score] READ_SCORED_ROWS config_sig={config_sig} n_rows={len(scored_rows)}",
        flush=True,
    )

    # Step 2: Accumulate forward IC series
    result = accumulate_forward_ic_series(
        config_sha256=config_sig,
        runs_dir=runs_dir,
    )

    ic_forward = result["ic_forward"]
    summary = result["summary"]
    n_months = result["n_months"]
    publishable = result["publishable_ci_half"]

    print(
        f"[E3-score] ACCUMULATED config_sig={config_sig} n_months={n_months} "
        f"mean_diff={summary['mean_diff']:.4f} ci_half={summary['ci_half']:.4f} "
        f"publishable_ci_half={publishable}",
        flush=True,
    )

    # Step 3: Save forward results
    # Note: save_forward_run is always idempotent (mirrors save_run),
    # so the force flag is only for CLI consistency.
    forward_dir = save_forward_run(
        config_sig,
        ic_forward=ic_forward,
        summary=summary,
        config={},  # Config is loaded from the ledger rows in production
        runs_dir=runs_dir,
        h6_deterministic=True,  # E3 is H6-deterministic by design
    )

    print(
        f"[E3-score] SAVED config_sig={config_sig} dir={forward_dir} "
        f"n_ic_forward={len(ic_forward)}",
        flush=True,
    )

    print(
        f"[E3-score] DONE config_sig={config_sig} n_months={n_months} "
        f"mean_diff={summary['mean_diff']:.4f}",
        flush=True,
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="E3 forward score runner: accumulate IC series and save forward results."
    )
    parser.add_argument(
        "config_sig",
        help="Config signature (sha256 of the frozen config).",
    )
    parser.add_argument(
        "--runs-dir",
        type=Path,
        default=None,
        help="Override the runs directory (for hermetic tests).",
    )
    parser.add_argument(
        "--prices-path",
        type=Path,
        default=None,
        help="Path to prices parquet (kept for API compatibility, not used in this slice).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow rewriting existing forward artifacts (idempotent by default).",
    )

    args = parser.parse_args()

    main(
        config_sig=args.config_sig,
        runs_dir=args.runs_dir,
        prices_path=args.prices_path,
        force=args.force,
    )
