"""E3 forward-commit runner - month-end freeze -> fit -> commit (standalone entry).

Thin entry shim over :func:`aionis.eval.forward_commit_runner.main` (mirrors
``scripts/phase_e1_run.py``). Loads cached Phase B/C/D inputs, FREEZES the
forward I_t (Slice 3c), builds arm_e13's extra_features (Pass A), assembles both
arm panels, builds the frozen config, and runs the forward-commit step (Slice 3d).

AUD-06 hardening (2026-09-01): every invocation is now live-readiness-gated,
exactly like ``scripts/e3_forward_trigger.py`` — the frozen contracts config
(``config/e3_live_contracts.yaml``) supplies the membership-freshness contract
and the pinned provider cutoff. The historical default
(``enforce_live_readiness=False``) left a bare ``python scripts/forward_commit.py``
as an ungated ledger-writing path around the month-end trigger; that bypass is
closed. ``PHASE_E3_NO_LEDGER=1`` keeps the artifacts-only reproducibility
semantics (gated run, throwaway runs dir, no ledger rows).

For the canonical calendar-aware path prefer ``scripts/e3_forward_trigger.py``
(this shim runs for *today's* month-end session without the run-date CLI).
"""
from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from e3_forward_trigger import _load_contracts, _load_provider_cutoff  # noqa: E402

from aionis.eval.forward_commit_runner import main  # noqa: E402

if __name__ == "__main__":
    config_path = _SCRIPTS_DIR.parent / "config" / "e3_live_contracts.yaml"
    membership_contract, provider_policy = _load_contracts(config_path)
    main(
        enforce_live_readiness=True,
        membership_freshness_contract=membership_contract,
        provider_cutoff_policy=provider_policy,
        provider_cutoff=_load_provider_cutoff(config_path),
    )
