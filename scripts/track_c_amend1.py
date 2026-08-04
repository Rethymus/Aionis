#!/usr/bin/env python3
"""Track C amendment #47 — A-share cninfo fundamentals -> exploratory-only (G1).

Owner authorized disposition (B) 2026-08-03: cninfo = CSRC public-filing portal, but
its anti-bot measures + commercial data-product licensing differ from EDGAR's open
API. Conservative G1 disposition: A-share cninfo fundamentals demoted to
exploratory-only (no-redistribute; polite scraping; NO anti-bot evasion). Track C
headline claim narrows to US-rank-IC (confirmatory) + A-share exploratory conditioning.

Appends a NEW config_committed row (#47) to runs/ledger.jsonl with an ``amends`` note;
the frozen #46 row is unchanged (durable-registry / append-only). Reuses the tested
config_sig mechanism from track_c_commit (sha256(json.dumps(config, sort_keys=True))).

Default = DRY-RUN; --commit appends. Observes NO OOS.
"""

from __future__ import annotations

import argparse
import copy
import json
from datetime import datetime, timezone

from track_c_commit import LEDGER, PHASE, TRACK_C_CONFIG, config_sig

AMENDMENT_NOTE = (
    "#46 -> A-share cninfo fundamentals demoted to exploratory-only: G1 disposition "
    "(cninfo anti-bot + commercial data-product licensing differ from EDGAR open API; "
    "conservative). Claim narrows to US-rank-IC + A-share-exploratory-conditioning."
)


def build_amendment() -> dict:
    cfg = copy.deepcopy(TRACK_C_CONFIG)
    cfg["claim"] = (
        "US S&P500 cross-sectional monthly rank-IC (confirmatory) + A-share CSI300 "
        "exploratory conditioning via regime_state interaction; cn_fundamentals "
        "exploratory-only (amendment #47, G1 cninfo disposition); null-favored"
    )
    cfg["feature_cols"]["cn_fundamentals_13"] = (
        "EXPLORATORY-ONLY (amendment #47): mirror us_fundamentals_13 via cninfo as-filed "
        "PDF (rollysys/use_cninfo MIT fetch + Aionis PyMuPDF parse); G1 disposition = "
        "public-filing + no-redistribute (cninfo anti-bot/commercial-licensing differ "
        "from EDGAR open API) -> exploratory, NOT confirmatory headline"
    )
    cfg["a_share_cninfo_disposition"] = (
        "exploratory-only; no-redistribute; polite scraping (>=2s); NO anti-bot evasion"
    )
    return cfg


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--commit", action="store_true", help="append the row (default: dry-run)")
    args = ap.parse_args()

    cfg = build_amendment()
    sig = config_sig(cfg)
    row = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": "config_committed",
        "phase": PHASE,
        "config_sig": sig,
        "amends": AMENDMENT_NOTE,
        "config": cfg,
    }
    print(f"[track_c-amend1] config_sig={sig}")
    print(f"[track_c-amend1] amends={AMENDMENT_NOTE[:90]}...")
    print(f"[track_c-amend1] claim now: {cfg['claim'][:90]}...")

    if not args.commit:
        print("[track_c-amend1] DRY-RUN (no append). Re-run with --commit to append ledger #47.")
        return 0

    with LEDGER.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, sort_keys=True) + "\n")
    print(f"[track_c-amend1] COMMITTED -> {LEDGER} (amendment row, #47)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
