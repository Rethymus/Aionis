"""Determinism probe: run the S1 manifest exporter in a fresh process and
print the payload sha8 — two runs with the same fixture must agree."""
import sys
import hashlib
import tempfile
from pathlib import Path

sys.path.insert(0, "scripts")
sys.path.insert(0, "tests")
import export_evidence_html as ex  # noqa: E402
from test_evidence_matrix_manifest import _write_fixture_tree  # noqa: E402

tmp = Path(tempfile.mkdtemp())
fx = _write_fixture_tree(tmp)
out = tmp / "evidence-matrix-v1.json"
m = ex.export_evidence_matrix_manifest(out_path=out, **fx)
print("sha8:", hashlib.sha256(out.read_bytes()).hexdigest()[:8])
print("track_c keys:", sorted(m["claims"]["track_c"].keys()))
