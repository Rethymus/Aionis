"""Hermetic tests for scripts/evidence_refresh.py.

The script's whole value is its ORDER (three out-of-order incidents: the
2026-09-09 license cascade, rounds 182 and 215). These tests pin the order
invariants and the plan surface WITHOUT running any real export (that needs
the gitignored data/ tree — see the local-artifact contract tests for the
exporters themselves).
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "evidence_refresh.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("evidence_refresh", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def er():
    return _load_module()


def test_step_order_invariants(er) -> None:
    """The canonical order is load-bearing; pin it."""
    steps = list(er.STEP_NAMES)
    assert steps.index("export_terminal_data") < steps.index("export_evidence_html"), (
        "terminal panels must render before the atlas reads them"
    )
    assert steps.index("export_evidence_html") < steps.index("export_research_dossier"), (
        "the atlas must exist before the dossier embeds its sha256"
    )
    assert steps.index("export_research_dossier") < steps.index("export_phase_dossier_meta")
    assert steps.index("shelf_matrix_repin") == len(steps) - 1, (
        "the shelf+matrix re-pin hashes the artifacts above — it must be LAST"
    )


def test_gate_covers_the_evidence_chain(er) -> None:
    """--check must run the same evidence gates the nightly lane gates on."""
    joined = " ".join(er.GATE_TESTS)
    for required in (
        "test_web_terminal_data",
        "test_knowledge_shelf_panel_contract",
        "test_research_dossier_pipeline",
        "test_evidence_matrix_manifest",
    ):
        assert required in joined, f"gate missing {required}"


def test_dry_run_prints_ordered_plan(er, capsys) -> None:
    # Call main() with --dry-run via sys.argv manipulation (hermetic: no exports).
    argv_backup = sys.argv
    try:
        sys.argv = ["evidence_refresh.py", "--dry-run"]
        rc = er.main()
    finally:
        sys.argv = argv_backup
    assert rc == 0
    out = capsys.readouterr().out
    lines = [ln for ln in out.splitlines() if ln.strip()]
    assert lines[: len(er.STEP_NAMES)] == list(er.STEP_NAMES)


def test_run_refresh_executes_steps_in_plan_order(monkeypatch) -> None:
    """run_refresh must call the exporters in STEP_NAMES order (mocked)."""
    er = _load_module()
    called: list[str] = []

    class _Fake:
        def __init__(self, name: str, rc: int = 0):
            self._name, self._rc = name, rc

        def __call__(self, *a, **k):
            called.append(self._name)
            if self._name == "export_research_dossier.main":
                return self._rc
            return None

    fake_terminal = type("M", (), {"main": _Fake("export_terminal_data"),
                                   "export_knowledge_shelf": _Fake("export_knowledge_shelf")})
    fake_evidence = type(
        "M", (),
        {"main": _Fake("export_evidence_html"),
         "export_evidence_matrix_manifest": _Fake("export_evidence_matrix_manifest")})
    fake_dossier = type("M", (), {"main": _Fake("export_research_dossier.main"),
                                  "export_phase_dossier_meta": _Fake("export_phase_dossier_meta")})

    import types
    mods = {
        "export_terminal_data": types.ModuleType("export_terminal_data"),
        "export_evidence_html": types.ModuleType("export_evidence_html"),
        "export_research_dossier": types.ModuleType("export_research_dossier"),
    }
    mods["export_terminal_data"].main = fake_terminal.main  # type: ignore[attr-defined]
    mods["export_terminal_data"].export_knowledge_shelf = fake_terminal.export_knowledge_shelf  # type: ignore[attr-defined]
    mods["export_evidence_html"].main = fake_evidence.main  # type: ignore[attr-defined]
    mods["export_evidence_html"].export_evidence_matrix_manifest = (
        fake_evidence.export_evidence_matrix_manifest  # type: ignore[attr-defined]
    )
    mods["export_research_dossier"].main = fake_dossier.main  # type: ignore[attr-defined]
    mods["export_research_dossier"].export_phase_dossier_meta = (
        fake_dossier.export_phase_dossier_meta  # type: ignore[attr-defined]
    )
    for name, mod in mods.items():
        monkeypatch.setitem(sys.modules, name, mod)

    rc = er.run_refresh(check=False)
    assert rc == 0
    expected = [
        "export_terminal_data",
        "export_evidence_html",
        "export_research_dossier.main",
        "export_phase_dossier_meta",
        "export_knowledge_shelf",
        "export_evidence_matrix_manifest",
    ]
    assert called == expected, f"execution order drifted: {called}"
