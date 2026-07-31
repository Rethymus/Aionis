"""E3 forward-score runner - accumulate forward IC series and save results (standalone entry).

Thin entry shim over :func:`aionis.eval.forward_score_runner.main` (mirrors
``scripts/forward_commit.py`` and ``scripts/phase_e1_run.py``).

Reads ``forward_outcome_scored`` ledger rows, accumulates the differential IC
series (e13 - base), applies rank-ic_summary + diebold_mariano_mbb inference,
and persists forward results under ``runs/forward/<config_sig>/`` (Slice 4e).

Run: ``uv run python scripts/forward_score.py <config_sig>``.
"""
from __future__ import annotations

from aionis.eval.forward_score_runner import main

if __name__ == "__main__":
    main()
