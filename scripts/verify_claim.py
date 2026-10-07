"""One-command claim-chain verifier — the CLI twin of the /proof page.

For each frozen claim (B/C/D/E1, track_c) this recomputes the four links of
the pre-registration proof chain from the working tree and reports PASS/FAIL
per link:

  1. prereg — docs/<phase>-preregistration.md exists and is tracked;
  2. ledger — the pinned ledger row exists with event confirmatory:* and a
     config sha;
  3. frozen — runs/results/<sig>/ exists for that sha (LOCAL artifact —
     degrades to SKIP on machines without data, honestly reported);
  4. matrix — the committed evidence_matrix.json row for the claim matches
     the ledger row number and (where present) the results sig.

Exit 0 iff no FAIL (SKIP does not fail: the runs/results tree is a research
machine artifact, not part of the repo).

Usage::

    uv run python scripts/verify_claim.py            # all claims
    uv run python scripts/verify_claim.py B D        # subset
    uv run python scripts/verify_claim.py track_c

Bounds: read-only verification over tracked files — 0 ledger writes.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEDGER = ROOT / "runs" / "ledger.jsonl"
RESULTS = ROOT / "runs" / "results"
MATRIX = ROOT / "web" / "src" / "data" / "aionis" / "evidence_matrix.json"

# claim -> (prereg doc, ledger row) — mirrored from the committed matrix.
CLAIMS: dict[str, dict] = {
    "B": {"prereg": "docs/phase-b-preregistration.md", "row": 28},
    "C": {"prereg": "docs/phase-c-preregistration.md", "row": 30},
    "D": {"prereg": "docs/phase-d-preregistration.md", "row": 34},
    "E1": {"prereg": "docs/phase-e-preregistration.md", "row": 37},
    "track_c": {"prereg": "docs/track-c-preregistration.md", "row": 49},
}


def _check_prereg(doc: str) -> tuple[str, str]:
    path = ROOT / doc
    if not path.exists():
        return "FAIL", f"{doc} missing"
    proc = subprocess.run(
        ["git", "ls-files", "--", doc], cwd=str(ROOT),
        capture_output=True, text=True, encoding="utf-8",
    )
    if doc not in proc.stdout:
        return "FAIL", f"{doc} exists but is not tracked"
    return "PASS", f"tracked, {path.stat().st_size:,} bytes"


def _check_ledger(row_n: int) -> tuple[str, str]:
    rows = [json.loads(ln) for ln in
            LEDGER.read_text(encoding="utf-8").splitlines() if ln.strip()]
    if row_n > len(rows) or row_n < 1:
        return "FAIL", f"row #{row_n} out of range (n={len(rows)})"
    d = rows[row_n - 1]
    ev = str(d.get("event", ""))
    sig = d.get("config_sig") or d.get("config_sig_short") or ""
    if "confirmatory" not in ev:
        return "FAIL", f"row #{row_n} event={ev!r} (expected confirmatory:*)"
    if not sig:
        return "FAIL", f"row #{row_n} carries no config sha"
    return "PASS", f"row #{row_n}: {d.get('ts')} event={ev} sig={str(sig)[:12]}…"


def _check_frozen(row_n: int, claim: str) -> tuple[str, str]:
    # Walk-forward claims (matrix row carries no results_sig) never persist
    # a runs/results/<sig>/ dir — their artifacts are the ledger row + the
    # committed panels. That absence is expected, not a broken link.
    m = json.loads(MATRIX.read_text(encoding="utf-8"))
    if not m["claims"].get(claim, {}).get("results_sig"):
        return "SKIP", (f"{claim} is walk-forward: no runs/results/<sig> dir "
                        "by design (ledger row + committed panels are the "
                        "artifacts)")
    rows = [json.loads(ln) for ln in
            LEDGER.read_text(encoding="utf-8").splitlines() if ln.strip()]
    sig = str(rows[row_n - 1].get("config_sig") or "")
    if not RESULTS.exists() or not any(RESULTS.iterdir()):
        return "SKIP", "runs/results absent on this machine (research artifact)"
    if sig and (RESULTS / sig).exists():
        return "PASS", f"runs/results/{sig[:16]}…/ present"
    return ("FAIL", f"runs/results/{sig[:16]}… not found among "
            f"{len(list(RESULTS.iterdir()))} dirs") if sig else (
        "SKIP", "no config_sig on row")


def _check_matrix(claim: str, row_n: int) -> tuple[str, str]:
    m = json.loads(MATRIX.read_text(encoding="utf-8"))
    c = m["claims"].get(claim if claim != "E1" else "E1")
    c = m["claims"].get(claim)
    if c is None:
        return "FAIL", f"claim {claim} absent from evidence_matrix.json"
    if c.get("ledger_row") != row_n:
        return "FAIL", (f"matrix ledger_row={c.get('ledger_row')} "
                        f"!= pinned {row_n}")
    if not (ROOT / c["prereg_doc"]).exists():
        return "FAIL", f"matrix prereg doc {c['prereg_doc']} missing"
    sig = c.get("results_sig")
    return "PASS", (f"ledger_row={row_n} prereg={c['prereg_doc']}"
                    + (f" sig={sig[:12]}…" if sig else " (walk-forward)"))


def verify(claim: str) -> int:
    spec = CLAIMS[claim]
    checks = [
        ("prereg", _check_prereg(spec["prereg"])),
        ("ledger", _check_ledger(spec["row"])),
        ("frozen", _check_frozen(spec["row"], claim)),
        ("matrix", _check_matrix(claim, spec["row"])),
    ]
    print(f"== {claim} ==")
    failed = 0
    for name, (status, detail) in checks:
        mark = {"PASS": "✓", "FAIL": "✗", "SKIP": "–"}[status]
        print(f"  {mark} {name:8s} {status}  {detail}")
        failed += status == "FAIL"
    return failed


def main(argv: list[str]) -> int:
    targets = argv if argv else list(CLAIMS)
    unknown = [t for t in targets if t not in CLAIMS]
    if unknown:
        print(f"unknown claim(s): {unknown}; known: {list(CLAIMS)}")
        return 2
    total = sum(verify(t) for t in targets)
    print(f"\n{'ALL LINKS VERIFIED' if total == 0 else f'{total} FAIL'}"
          f"  ({', '.join(targets)}; SKIP = research-machine artifact)")
    return 0 if total == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
