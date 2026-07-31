"""E3 forward-commit runner - month-end freeze -> fit -> commit (standalone entry).

Thin entry shim over :func:`aionis.eval.forward_commit_runner.main` (mirrors
``scripts/phase_e1_run.py``). Loads cached Phase B/C/D inputs, FREEZES the
forward I_t (Slice 3c), builds arm_e13's extra_features (Pass A), assembles both
arm panels, builds the frozen config, and runs the forward-commit step (Slice 3d).

``PHASE_E3_NO_LEDGER=1`` -> artifacts-only reproducibility rerun (computes the
scores sig, writes nothing to the ledger). Run: ``uv run python scripts/forward_commit.py``.
"""
from __future__ import annotations

from aionis.eval.forward_commit_runner import main

if __name__ == "__main__":
    main()
