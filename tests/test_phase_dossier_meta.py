"""Contract tests for the R2-full S2 per-phase meta dossiers (B / D / E1).

1. Hermetic fixture: tmp results tree + ledger -> export -> three byte-stable
   files carrying the fixture values; ledger mismatch raises.
2. Real contract: the committed reports/evidence/research-dossier-{b,d,e1}-v1.html
   must equal a fresh render of the current frozen artifacts (byte-stable).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import export_research_dossier as erd  # noqa: E402

SIGS = {
    "B": "17245a75d2d4cd17c68f36a9d0f4b4f7f3baf1db31b33b87be79e6e4a11400da",
    "D": "d31580630ff35326557dda9f50832c7af3625dd6507e47e252ea01800372a12c",
    "E1": "ef321e9ee808804601e012818fa95522d2dc5f0fe8c53771d7f1b412c25ed49f",
}
ROWS = {"B": 28, "D": 34, "E1": 37}


def _write_fixture_tree(tmp_path: Path, wrong_sig: str | None = None) -> dict:
    """Synthetic labeled fixture — NOT research data (unit-test fixture only)."""
    results = tmp_path / "results"
    ledger_lines: list[str] = []
    for phase, sig in SIGS.items():
        row = ROWS[phase]
        # results dirs always land under the REAL sig; ledger_sig_override
        # corrupts only the LEDGER line (that is what the missing-dir gate
        # reconciles against).
        d = results / sig
        d.mkdir(parents=True, exist_ok=True)
        (d / "differential.json").write_text(
            json.dumps({"mean_diff": -0.001, "ci_lo": -0.01, "ci_hi": 0.01,
                        "dm_p_mbb": 0.5, "n_months": 125}),
            encoding="utf-8",
        )
        (d / "meta.json").write_text(
            json.dumps({"h6_deterministic": True, "config_sig": sig}),
            encoding="utf-8",
        )
        (d / "controls.json").write_text(json.dumps({"placebo": {}, "lag_shift": {}}),
                                         encoding="utf-8")
        while len(ledger_lines) < row - 1:
            ledger_lines.append("{}")
        use = wrong_sig if (wrong_sig and phase == "B") else sig
        ledger_lines.append(json.dumps({"config_sig": use}))
    ledger = tmp_path / "ledger.jsonl"
    ledger.write_text("\n".join(ledger_lines) + "\n", encoding="utf-8")
    return {"results_dir": results, "ledger_path": ledger}


def test_fixture_phase_dossiers_byte_stable(tmp_path: Path) -> None:
    fx = _write_fixture_tree(tmp_path)
    out = tmp_path / "out"
    w1 = erd.export_phase_dossier_meta(out_dir=out, **fx)
    raws1 = {w["id"]: (out / (w["id"] + ".html")).read_bytes() for w in w1}
    w2 = erd.export_phase_dossier_meta(out_dir=out, **fx)
    for w in w2:
        assert (out / (w["id"] + ".html")).read_bytes() == raws1[w["id"]]
    assert {w["id"] for w in w1} == {
        "research-dossier-b-v1", "research-dossier-d-v1", "research-dossier-e1-v1",
    }
    b = raws1["research-dossier-b-v1"].decode("utf-8")
    assert "mean_diff" in b and "placebo" in b and "preregistration" in b


def test_fixture_results_dir_missing_raises(tmp_path: Path) -> None:
    fx = _write_fixture_tree(tmp_path, wrong_sig="e" * 64)
    try:
        erd.export_phase_dossier_meta(out_dir=tmp_path / "out", **fx)
    except ValueError as e:
        assert "results dir missing" in str(e)
    else:
        raise AssertionError("results-dir mismatch must raise")


def test_real_phase_dossiers_equal_fresh_render(tmp_path: Path) -> None:
    """LOCAL-ARTIFACT contract: the phase dossiers embed per-phase frozen
    metrics read from the gitignored runs/results tree — a fresh CI checkout
    lacks it and this test skips (it runs on the research machine)."""
    import pytest

    if not any(
        (Path("runs/results") / s / "differential.json").exists()
        for s in SIGS.values()
    ):
        pytest.skip(
            "local-artifact contract: phase dossiers read the gitignored "
            "frozen runs/results tree (research machine only)"
        )
    for phase, sig in SIGS.items():
        fp = Path(f"reports/evidence/research-dossier-{phase.lower()}-v1.html")
        committed = fp.read_text(encoding="utf-8")
        prereg = (
            f"docs/phase-{phase.lower() if phase != 'E1' else 'e'}-preregistration.md"
        )
        fresh = erd._phase_dossier_html(
            phase, ROWS[phase], prereg,
            Path("runs/results"),
            Path("runs/ledger.jsonl").read_text(encoding="utf-8").splitlines(),
        )
        assert committed == fresh, f"{phase} dossier drifted"
        assert f"<td>{sig}</td>" in committed
