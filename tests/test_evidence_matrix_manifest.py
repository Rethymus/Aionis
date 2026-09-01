"""Contract tests for the R2-full S1 evidence matrix manifest.

Two layers, mirroring the atlas/dossier contract style:

1. Hermetic fixture tests (tmp tree, values constructed in-test and labeled as
   fixtures): five-claim structure, ledger reconciliation gate (mismatch
   raises), byte-stable double-run.
2. The committed real manifest (reports/evidence/evidence-matrix-v1.json) must
   equal a fresh in-memory render of the current inputs — differential values
   bit-identical to runs/results/<sig>/differential.json, ledger sigs
   reconciled, artifact digests matching on-disk recompute.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import export_evidence_html as ex  # noqa: E402

REAL_MATRIX = Path("reports/evidence/evidence-matrix-v1.json")

SIGS = {
    "B": "17245a75d2d4cd17c68f36a9d0f4b4f7f3baf1db31b33b87be79e6e4a11400da",
    "C": "a7fdb48f5942fae146b151143807653fd66c4c5f1601dc7cf9d04a796c1fada1",
    "D": "d31580630ff35326557dda9f50832c7af3625dd6507e47e252ea01800372a12c",
    "E1": "ef321e9ee808804601e012818fa95522d2dc5f0fe8c53771d7f1b412c25ed49f",
}
ROWS = {"B": 28, "C": 30, "D": 34, "E1": 37, "track_c": 49}


def _write_fixture_tree(tmp_path: Path, ledger_sig_override: str | None = None) -> dict:
    """Synthetic labeled fixture — NOT research data (unit-test fixture only)."""
    results = tmp_path / "results"
    ledger_lines: list[str] = []
    for phase, sig in SIGS.items():
        row = ROWS[phase]
        diff = {
            "mean_diff": -0.001, "ci_lo": -0.01, "ci_hi": 0.01,
            "dm_p_mbb": 0.5, "n_months": 125,
            "mean_ic_diff_state_minus_base": -0.001,
        }
        d = results / sig
        d.mkdir(parents=True, exist_ok=True)
        (d / "differential.json").write_text(json.dumps(diff), encoding="utf-8")
        while len(ledger_lines) < row - 1:
            ledger_lines.append("{}")
        ledger_lines.append(json.dumps({"config_sig": ledger_sig_override or sig}))
    # pad to line 49 and add the track_c row
    while len(ledger_lines) < ROWS["track_c"] - 1:
        ledger_lines.append("{}")
    ledger_lines.append(json.dumps({"config_sig": "e14b9d44" + "0" * 56}))
    ledger = tmp_path / "ledger.jsonl"
    ledger.write_text("\n".join(ledger_lines) + "\n", encoding="utf-8")

    metrics = {
        "combined_ic": -0.0088, "p": 0.484, "n_months": 71,
        "ci_lo": -0.0336, "ci_hi": 0.0159, "verdict": "NULL",
        "jt_look1": "NOT_EQUIVALENT", "h6": "PASS", "sesoi": 0.01,
        "ledger_row": 49,
    }
    metrics_path = tmp_path / "metrics.json"
    metrics_path.write_text(json.dumps(metrics), encoding="utf-8")

    art = tmp_path / "artifacts"
    art.mkdir()
    (art / "atlas-claim-v1.html").write_text("<html>fixture-atlas</html>", encoding="utf-8")
    (art / "research-dossier-v1.html").write_text("<html>fixture-dossier</html>", encoding="utf-8")
    return {
        "results_dir": results, "ledger_path": ledger,
        "metrics_path": metrics_path, "artifacts_dir": art,
    }


def test_fixture_manifest_structure_and_byte_stability(tmp_path: Path) -> None:
    fx = _write_fixture_tree(tmp_path)
    out = tmp_path / "matrix.json"
    m1 = ex.export_evidence_matrix_manifest(out_path=out, **fx)
    raw1 = out.read_bytes()
    ex.export_evidence_matrix_manifest(out_path=out, **fx)
    assert raw1 == out.read_bytes(), "double-run must be byte-identical"
    assert m1 == json.loads(raw1)

    assert set(m1["claims"]) == {"B", "C", "D", "E1", "track_c"}
    for phase in ("B", "C", "D", "E1"):
        c = m1["claims"][phase]
        assert c["results_sig"] == SIGS[phase]
        assert c["zero_llm"] is True
        assert c["n_months"] == 125
    tc = m1["claims"]["track_c"]
    assert tc["verdict"] == "NULL" and tc["p_hac"] == 0.484 and tc["n_months"] == 71

    assert len(m1["artifacts"]) == 2
    for a in m1["artifacts"]:
        raw = (fx["artifacts_dir"] / (a["id"] + ".html")).read_bytes()
        assert a["sha256"] == hashlib.sha256(raw).hexdigest()
        assert a["bytes"] == len(raw)


def test_fixture_ledger_mismatch_raises(tmp_path: Path) -> None:
    fx = _write_fixture_tree(tmp_path, ledger_sig_override="f" * 64)
    out = tmp_path / "matrix.json"
    try:
        ex.export_evidence_matrix_manifest(out_path=out, **fx)
    except ValueError as e:
        assert "config_sig" in str(e)
    else:
        raise AssertionError("ledger/config-sig mismatch must raise")


def test_real_manifest_equals_fresh_render_of_current_inputs() -> None:
    """Byte-stable contract: committed manifest == fresh render (no drift)."""
    tmp_unused = Path("runs/tmp_evidence_matrix_fresh.json")
    fresh = ex.export_evidence_matrix_manifest(out_path=tmp_unused)
    try:
        committed = json.loads(REAL_MATRIX.read_text(encoding="utf-8"))
        assert committed == fresh
    finally:
        tmp_unused.unlink(missing_ok=True)
