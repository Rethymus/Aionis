#!/usr/bin/env python3
"""Track Adaptive amendment #2 — n_estimators 500→100 (feasibility).

Supersedes #52 (sig ffd0c922…): benchmark showed the 500-tree weekly refit is
~16.8s/fit → ~27 min for 285 fits / 3 cores (feasible but slow for interactive
iteration). Reducing to n_estimators=100 (both arms) gives ~3.2s/fit → ~5 min.
The frozen-vs-expanding comparison is **self-contained** (both arms share the
same learner), so it is valid at any n_estimators; 100 is a weaker learner but
the IC_diff estimand is unchanged in kind. The 500-tree faithful run remains
available on request (background, ~27 min).

Default = DRY-RUN; ``--commit`` appends #53. Observes NO OOS.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from track_adaptive_amend1 import (
    LEDGER,
    PHASE,
)
from track_adaptive_amend1 import (  # noqa: E402
    TRACK_ADAPTIVE_CONFIG as _BASE,
)

_C = {**_BASE}
_C["learner"] = {
    **_BASE["learner"],
    "params": {**_BASE["learner"]["params"], "n_estimators": 100},
}
_C["amendment"] = (
    "amend2: n_estimators 500→100 (feasibility ~5min vs ~27min; both arms; "
    "comparison self-contained, valid at any n_estimators). Supersedes #52."
)
_C["supersedes"] = {
    "ledger_row": 52,
    "sig": "ffd0c9227e692fe826faeac964607577f3a9ff3de3384907297bc396887c4659",
    "reason": (
        "500-tree weekly refit = ~16.8s/fit → ~27min; reduced to 100 for "
        "feasibility. The frozen-vs-expanding IC_diff estimand is self-contained "
        "(both arms share the learner), so valid at 100. 500-tree faithful run "
        "available on request."
    ),
}

TRACK_ADAPTIVE_CONFIG = _C


def config_sig(config: dict) -> str:
    return hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()


def build_row(config: dict) -> dict:
    return {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": "config_committed",
        "phase": PHASE,
        "config_sig": config_sig(config),
        "config": config,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--commit", action="store_true")
    args = ap.parse_args()
    row = build_row(TRACK_ADAPTIVE_CONFIG)
    print(f"[track_adaptive amend2] config_sig={row['config_sig']}")
    print(f"[track_adaptive amend2] n_estimators="
          f"{TRACK_ADAPTIVE_CONFIG['learner']['params']['n_estimators']}")
    if not args.commit:
        print("[track_adaptive amend2] DRY-RUN. Re-run with --commit to freeze #53.")
        return 0
    with LEDGER.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, sort_keys=True) + "\n")
    print(f"[track_adaptive amend2] COMMITTED -> {LEDGER}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
