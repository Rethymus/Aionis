"""Panel-type drift scanner (protocol channel B tool, round 46).

Checks every committed panel JSON's top-level keys against the TypeScript
contract declarations in web/src/data/aionis/*.ts. Catches the exporter↔
display drift that tsc cannot (a key absent from a type only breaks when a
view dereferences it). Exit 1 on drift so it can gate a round.

Non-hermetic? No — it reads only tracked files (web/src/data/aionis/), so it
IS hermetic and CI-safe, but it is a protocol walk tool, not wired into the
pytest suite (the export-side shape is already pinned by the web-contract
tests; this covers the type-declaration side).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "web" / "src" / "data" / "aionis"


def main() -> int:
    ts_sources = ""
    for p in sorted(DATA.glob("*.ts")):
        ts_sources += p.read_text(encoding="utf-8")

    drift: list[str] = []
    panels = sorted(DATA.glob("*.json"))
    for f in panels:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            drift.append(f"{f.name}: PARSE ERROR {e}")
            continue
        if not isinstance(data, dict):
            continue
        for k in data:
            if not re.search(rf"\b{re.escape(k)}\s*[?:]", ts_sources):
                drift.append(f"{f.name}: top-level key '{k}' not found in any TS type")

    print(f"scanned {len(panels)} panel JSONs")
    if drift:
        print("DRIFT:")
        for d in drift:
            print(" -", d)
        return 1
    print("NO TOP-LEVEL KEY DRIFT")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
