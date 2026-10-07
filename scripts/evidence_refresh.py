"""Evidence-cascade refresh — the single ordered entrypoint for interactive sessions.

Why this exists
---------------
The evidence chain is sha-interlocked: the dossier embeds the atlas file's
sha256, the knowledge shelf + evidence matrix pin artifact sha256s, and the
contract tests pin ALL of it against a fresh render. Running the exporters
out of order therefore produces a consistent-looking tree that only the
contract tests reject. That class bit three times before being named
(2026-09-09 license cascade, round 182, round 215) — each time a human ran
the exporters from memory instead of via the lane.

``scripts/ops_local_refresh.py`` already encodes the canonical order for the
nightly lane, but it is fused to fetching (75 minutes). This script is the
lane's export tail, extracted verbatim in the same order, for mid-day
interactive edits of exporters/docs/panels:

    1. export_terminal_data        (panels + api_catalog + data_health)
    2. export_evidence_html        (atlas-claim HTML — BEFORE the dossier,
                                    which embeds its sha256)
    3. export_research_dossier     (research-dossier-v1 HTML)
    4. export_phase_dossier_meta   (phase dossier metadata)
    5. shelf + evidence matrix     (re-pin: knowledge_shelf + matrix manifest,
                                    always LAST — it hashes the artifacts
                                    produced above)
    6. contract gate (--check)     (the same evidence gate subset the lane
                                    runs BEFORE push)

Differences vs the nightly lane (documented, deliberate):
- single export_terminal_data pass (the lane's second pass exists only to
  pick up ``stakes_pct_parse`` output between passes; interactive edits
  don't fetch new stakes rows);
- no fetching, no ledger writes, no commits, no pushes.

Usage::

    uv run python scripts/evidence_refresh.py            # render steps 1-5
    uv run python scripts/evidence_refresh.py --check    # + evidence gate tests
    uv run python scripts/evidence_refresh.py --dry-run  # print the plan only

Bounds: display lane — 0 ledger rows / 0 frozen configs / 0 OOS metrics.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

# The evidence contract tests the nightly lane gates on before push
# (ops_local_refresh.py GATE_TEST/_2/_3/_TESTS_EV, minus the ledger-append
# deselect which is a fetch-time concern, not an export concern).
GATE_TESTS: tuple[str, ...] = (
    "tests/test_web_terminal_data.py",
    "tests/test_knowledge_shelf_panel_contract.py",
    "tests/test_research_dossier_pipeline.py",
    "tests/test_evidence_matrix_manifest.py",
    "tests/test_evidence_matrix_panel_contract.py",
)

# Order is the contract — see module docstring. Tests assert the invariants:
# terminal_data < evidence_html < research_dossier < phase_meta < re_pin.
STEP_NAMES: tuple[str, ...] = (
    "export_terminal_data",
    "export_evidence_html",
    "export_research_dossier",
    "export_phase_dossier_meta",
    "shelf_matrix_repin",
)


def run_refresh(check: bool = False) -> int:
    """Execute the cascade in canonical order; return a process exit code."""
    import export_evidence_html
    import export_research_dossier
    import export_terminal_data

    for step in STEP_NAMES:
        print(f"[evidence-refresh] {step} ...", flush=True)
        if step == "export_terminal_data":
            export_terminal_data.main()
        elif step == "export_evidence_html":
            export_evidence_html.main()
        elif step == "export_research_dossier":
            rc = export_research_dossier.main()
            if rc:
                return rc
        elif step == "export_phase_dossier_meta":
            export_research_dossier.export_phase_dossier_meta()
        elif step == "shelf_matrix_repin":
            # Always LAST: hashes the artifacts rendered above.
            export_terminal_data.export_knowledge_shelf()
            export_evidence_html.export_evidence_matrix_manifest()

    if check:
        print(f"[evidence-refresh] gate: {' '.join(GATE_TESTS)}", flush=True)
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", *GATE_TESTS],
            cwd=str(ROOT),
        )
        if proc.returncode:
            return proc.returncode

    print("[evidence-refresh] done", flush=True)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Re-render the evidence cascade in the canonical order.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="run the evidence contract-gate tests after rendering",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the ordered plan without executing anything",
    )
    args = parser.parse_args()
    if args.dry_run:
        plan = list(STEP_NAMES) + (["gate: " + " ".join(GATE_TESTS)] if args.check else [])
        print("\n".join(plan))
        return 0
    return run_refresh(check=args.check)


if __name__ == "__main__":
    raise SystemExit(main())
