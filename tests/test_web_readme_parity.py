"""web/README.md route parity — the "7/38 rotted" class can never recur.

The 2026-09 audit found 7 of web/README's 38 documented routes had rotted
(pages renamed/removed without the README following). The README was fully
rewritten then — but no guard pinned it, so the same rot could silently
return. This contract pins BOTH directions against the real app surface:

  1. every route the README documents exists under web/src/app/(dashboard)/;
  2. every (dashboard) route with a page.tsx is documented (dynamic
     drill-downs count via their first path segment);
  3. the heading's route count matches the actual directory count.

Hermetic: reads tracked files only.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "web" / "README.md"
DASH = ROOT / "web" / "src" / "app" / "(dashboard)"


def _documented_routes() -> set[str]:
    s = README.read_text(encoding="utf-8")
    routes: set[str] = set()
    for m in re.finditer(r"^\|\s*`/([a-z-]+)(?:/\[?[a-z]+\]?)?`", s, re.M):
        routes.add(m.group(1))
    assert routes, "README route table not found — extraction pattern rotted"
    return routes


def _root_readme_caption_counts() -> tuple[int, int]:
    """Route counts claimed in the ROOT README hero captions (zh, en)."""
    zh = (ROOT / "README.md").read_text(encoding="utf-8")
    en = (ROOT / "README.en.md").read_text(encoding="utf-8")
    m_zh = re.search(r"研究终端漫游</b> · (\d+) 个路由", zh)
    m_en = re.search(r"the public face across (\d+) routes", en)
    assert m_zh and m_en, "root README hero caption pattern rotted"
    return int(m_zh.group(1)), int(m_en.group(1))


def _actual_routes() -> set[str]:
    routes = {
        p.parent.name
        for p in DASH.glob("*/page.tsx")
    }
    # dynamic drill-downs live one level deeper: stock/[ticker]/page.tsx
    routes |= {p.parent.parent.name for p in DASH.glob("*/*/page.tsx")}
    assert routes, "no (dashboard) routes found — directory layout changed?"
    return routes


def test_readme_routes_all_exist() -> None:
    documented = _documented_routes()
    actual = _actual_routes()
    ghosts = sorted(documented - actual)
    assert not ghosts, (
        f"README documents route(s) that no longer exist (the 7/38 rot class): "
        f"{ghosts}"
    )


def test_readme_covers_every_route() -> None:
    documented = _documented_routes()
    actual = _actual_routes()
    # exempted by design: none today — every route earns a README row
    undocumented = sorted(actual - documented)
    assert not undocumented, (
        f"(dashboard) route(s) missing from the README route table: "
        f"{undocumented}"
    )


def test_readme_heading_count_matches() -> None:
    s = README.read_text(encoding="utf-8")
    m = re.search(r"Routes \((\d+) under", s)
    assert m, "README routes heading lost its count"
    claimed = int(m.group(1))
    actual = len(_actual_routes())
    assert claimed == actual, (
        f"README heading claims {claimed} routes, app has {actual}"
    )


def test_root_readme_caption_matches_actual_route_count() -> None:
    """The hero-caption route count must equal the actual (dashboard) route
    count — the caption drifted 38->40->42 by hand twice (rounds 220/223
    missed it); this guard kills the class."""
    zh_n, en_n = _root_readme_caption_counts()
    actual = len(_actual_routes())
    assert zh_n == actual, f"zh caption says {zh_n} routes, actual {actual}"
    assert en_n == actual, f"en caption says {en_n} routes, actual {actual}"
