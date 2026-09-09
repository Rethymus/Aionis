"""Export the provenance-chained research dossier HTML artifact (TASK-DSP-D1).

One generator, three stages:

1. **Source-based research** -> the S-registry: every source that backs the
   dossier is registered as ``{id, type, locator, integrity, license, role}``.
   Types: ``panel`` (web/src/data/aionis/*.json, integrity = sha256 of the file
   bytes, computed at generation time), ``ledger`` (specific runs/ledger.jsonl
   lines: the latest ``phase=="sensitivity_horizon"`` exploratory row and, if
   locatable, the ``config_committed`` freeze row; integrity = sha256 of the raw
   JSON line text + line number), ``doc`` (pre-registrations + the data-intake
   rubric), ``artifact`` (the committed G2 atlas evidence page), and
   ``external`` (literature / editorial bookmarks; integrity is honestly
   declared as ``external: self-declared`` — NOT machine-verifiable).

2. **Report generation** -> reports/evidence/research-dossier-v1.html: a single
   self-contained file (inline CSS + inline SVG + tables; zero JS, zero
   external resources, zero font requests, opens directly in a browser).

3. **Modeling & analysis** -> the dossier's analysis sections embed only real
   committed-artifact numbers (metrics / IC series / calibration /
   score diagnostics / the horizon-sweep ledger row), with the frozen chain
   config_sig -> ledger freeze row -> result row -> panel snapshot shown
   explicitly.

Citation closure is a HARD GATE: every number-bearing line must carry at least
one ``[S#]`` citation, every citation must resolve to a registered source, and
every registered source must be cited at least once. ``render()`` raises
``CitationClosureError`` on any violation (never silently).

Byte-stable by construction: no wall-clock reads anywhere (every as-of stamp
comes from a committed panel/ledger field), all sort orders are pinned in code,
numeric rendering is deterministic, and the file is written with LF newlines.
External URLs are rendered with the scheme stripped (still unique locators;
the full URLs live in the shared ks_sources.py literals) so the artifact
stays byte-clean of fetchable resource strings.

Display/derivation-lane script: read-only on panels/docs/ledger (runs/ is
NEVER written), writes ONLY under reports/evidence/, never touches frozen
surfaces or any preregistration.

Usage::

    uv run python scripts/export_research_dossier.py
"""
from __future__ import annotations

import hashlib
import html
import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path

from export_evidence_html import archive_if_changed  # R2-full M3 (move-don't-delete)
from ks_sources import RESEARCH_SOURCES

ROOT = Path(__file__).resolve().parents[1]
PANEL_DIR = ROOT / "web/src/data/aionis"
LEDGER_PATH = ROOT / "runs/ledger.jsonl"
OUT = ROOT / "reports/evidence/research-dossier-v1.html"

ARTIFACT_ID = "research-dossier-v1"
DOSSIER_VERSION = "v1"
GENERATOR_VERSION = "1.0.0"

PANEL_FILES = {
    "metrics": "metrics.json",
    "ic_monthly": "ic_monthly.json",
    "calibration": "calibration_reliability.json",
    "score_diagnostics": "score_diagnostics.json",
    "data_health": "data_health.json",
    "api_catalog": "api_catalog.json",
    "evidence": "evidence.json",
    "provenance": "headline_provenance.json",
}

DOC_FILES = {
    "doc_phase_d": "docs/phase-d-preregistration.md",
    "doc_track_c": "docs/track-c-preregistration.md",
    "doc_rubric": "docs/data-intake-rubric.md",
}

ARTIFACT_ATLAS = "reports/evidence/atlas-claim-v1.html"

# Hardcoded palette — the self-contained artifact must NOT depend on site CSS
# variables. Same light-theme correspondence as export_evidence_html.py (G2):
# single blue accent; direction is encoded by blue-vs-gray lightness
# (colorblind-safe; never red/green).
C_PAPER = "#ffffff"
C_INK = "#171717"
C_BLUE = "#0059ec"
C_TINT = "#e6f0ff"
C_LINE = "#e4e4e7"
C_MUTED = "#55555c"
C_GRAY = "#44474f"

_CSS = """\
:root { color-scheme: light; }
* { box-sizing: border-box; }
body { margin: 0; background: #f5f5f4; color: #171717; line-height: 1.55;
  font-family: ui-sans-serif, system-ui, "Segoe UI", "PingFang SC",
  "Hagino Sans GB", "Microsoft YaHei", sans-serif; }
main { max-width: 920px; margin: 0 auto; padding: 26px 20px 64px; }
section { background: #ffffff; border: 1px solid #e4e4e7; border-radius: 10px;
  padding: 20px 22px; margin: 18px 0; }
h1 { font-size: 1.38rem; margin: 0 0 8px; }
h2 { font-size: 1.02rem; margin: 0 0 12px; }
h3 { font-size: 0.92rem; margin: 14px 0 6px; }
p { margin: 8px 0; }
.sub { color: #55555c; font-size: 0.88rem; }
.accent { color: #0059ec; }
.badge { display: inline-block; border: 1px solid #0059ec; color: #0059ec;
  border-radius: 999px; padding: 1px 10px; font-size: 0.78rem;
  letter-spacing: 0.04em; vertical-align: 2px; }
.cite { color: #0059ec; font-size: 0.76rem; letter-spacing: 0.02em;
  font-variant-numeric: tabular-nums; white-space: nowrap; }
dl.card { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 10px 18px; margin: 0; }
dl.card div { border-top: 1px solid #ececf0; padding-top: 8px; }
dt { font-size: 0.76rem; color: #55555c; letter-spacing: 0.02em; }
dd { margin: 2px 0 0; font-size: 1.02rem; font-variant-numeric: tabular-nums; }
dl.kv { margin: 0; font-size: 0.84rem; }
dl.kv div { display: flex; gap: 12px; border-bottom: 1px solid #ececf0;
  padding: 4px 0; }
dl.kv dt { flex: 0 0 260px; color: #55555c; }
dl.kv dd { margin: 0; font-size: 0.84rem; font-variant-numeric: tabular-nums; }
.tbl { max-height: 460px; overflow: auto; border: 1px solid #ececf0;
  border-radius: 6px; }
table { border-collapse: collapse; width: 100%; font-size: 0.78rem;
  font-variant-numeric: tabular-nums; }
th, td { border-bottom: 1px solid #ececf0; padding: 4px 8px; text-align: right; }
th:first-child, td:first-child { text-align: left; }
td.l, th.l { text-align: left; }
th { color: #55555c; font-weight: 600; background: #fafafa; position: sticky;
  top: 0; }
.loc { font-family: ui-monospace, Consolas, "Courier New", monospace;
  font-size: 0.72rem; word-break: break-all; }
svg { display: block; width: 100%; height: auto; }
.note { font-size: 0.8rem; color: #55555c; }
.na { font-size: 0.86rem; color: #55555c; background: #fafafa;
  border: 1px dashed #c9c9cf; border-radius: 6px; padding: 8px 12px; }
ul.methods { margin: 0; padding-left: 1.25em; }
ul.methods li { margin: 7px 0; font-size: 0.88rem; }
ul.marks { margin: 0; padding-left: 1.25em; }
ul.marks li { margin: 6px 0; font-size: 0.84rem; }
code { background: #f2f2f4; border-radius: 4px; padding: 1px 5px;
  font-family: ui-monospace, Consolas, "Courier New", monospace;
  font-size: 0.86em; }
footer { color: #55555c; font-size: 0.78rem; padding: 0 4px; }
.holds-true { color: #0059ec; font-weight: 600; }
.holds-false { color: #44474f; font-weight: 600; }
"""


class AssemblyError(RuntimeError):
    """Raised when committed surfaces are internally inconsistent."""


class CitationClosureError(RuntimeError):
    """Raised when the [S#] citation closure is violated (hard gate)."""


# ---------------------------------------------------------------------------
# S-registry
# ---------------------------------------------------------------------------


@dataclass
class Source:
    """One registered source: id/type/locator/integrity/license/role."""

    sid: str
    type: str  # panel | ledger | doc | artifact | external
    locator: str
    integrity: str
    license: str
    role: str


@dataclass(frozen=True)
class LedgerRef:
    lineno: int  # 1-based
    sha: str
    raw: str
    rec: dict


@dataclass
class Assembly:
    sources: list[Source] = field(default_factory=list)
    sid: dict[str, str] = field(default_factory=dict)
    payloads: dict[str, object] = field(default_factory=dict)
    shas: dict[str, str] = field(default_factory=dict)
    ledger_horizon: LedgerRef | None = None
    ledger_freeze: LedgerRef | None = None

    def cite(self, *keys: str) -> str:
        """Citation chips for the given source keys (must all be registered)."""
        chips = []
        for k in keys:
            if k not in self.sid:
                raise AssemblyError(f"cite(): unregistered source key {k!r}")
            chips.append(f'<span class="cite">[{self.sid[k]}]</span>')
        return "".join(chips)

    def cite_opt(self, *keys: str) -> str:
        """Chips for optional co-citations (unregistered keys are skipped)."""
        chips = []
        for k in keys:
            if k in self.sid:
                chips.append(f'<span class="cite">[{self.sid[k]}]</span>')
        return "".join(chips)


def _sha_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _defang_url(url: str) -> str:
    """Scheme-stripped URL locator (deterministic; no fetchable scheme)."""
    u = url.strip()
    for pre in ("https://", "http://"):
        if u.startswith(pre):
            return u[len(pre):]
    return u


def _panel_source(fname: str, sha: str, role: str) -> Source:
    return Source(
        sid="",  # assigned below, in pinned order
        type="panel",
        locator=f"web/src/data/aionis/{fname}",
        integrity=f"sha256:{sha} (file bytes)",
        license="Aionis research artifacts (repo PolyForm-NC)",
        role=role,
    )


def _latest_horizon_ref(ledger_lines: list[str]) -> LedgerRef | None:
    """Latest (pinned: last matching line) phase=sensitivity_horizon row."""
    found: LedgerRef | None = None
    for i, raw in enumerate(ledger_lines):
        try:
            rec = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if (
            isinstance(rec, dict)
            and rec.get("phase") == "sensitivity_horizon"
            and rec.get("event") == "exploratory"
        ):
            found = LedgerRef(
                lineno=i + 1,
                sha=_sha_bytes(raw.encode("utf-8")),
                raw=raw,
                rec=rec,
            )
    return found  # last match = latest ts in the append-only ledger


def _locate_freeze_ref(
    ledger_lines: list[str], provenance: dict
) -> LedgerRef | None:
    """Locate the config_committed row matching the provenance freeze stamp."""
    freeze = provenance.get("freeze")
    if not isinstance(freeze, dict):
        return None
    ts = freeze.get("ts")
    for i, raw in enumerate(ledger_lines):
        try:
            rec = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(rec, dict) and rec.get("event") == "config_committed":
            if rec.get("ts") == ts:
                want_row = freeze.get("ledger_row")
                if isinstance(want_row, int) and want_row != i + 1:
                    raise AssemblyError(
                        "provenance.freeze.ledger_row="
                        f"{want_row} but the config_committed row with ts={ts}"
                        f" is line {i + 1} of runs/ledger.jsonl"
                    )
                return LedgerRef(
                    lineno=i + 1,
                    sha=_sha_bytes(raw.encode("utf-8")),
                    raw=raw,
                    rec=rec,
                )
    return None


def _verify_result_row(ledger_lines: list[str], provenance: dict) -> None:
    """Cross-check headline_provenance against the raw result ledger row."""
    row = provenance.get("ledger_row")
    headline = provenance.get("headline")
    if not (isinstance(row, int) and isinstance(headline, dict)):
        return
    if not (1 <= row <= len(ledger_lines)):
        raise AssemblyError(f"provenance.ledger_row={row} out of range")
    try:
        rec = json.loads(ledger_lines[row - 1])
    except json.JSONDecodeError as e:
        raise AssemblyError(f"ledger result row {row} is not JSON: {e}") from e
    ic = rec.get("combined_ic")
    want = headline.get("combined_ic")
    got = ic.get("mean") if isinstance(ic, dict) else None
    if want is not None and got is not None and got != want:
        raise AssemblyError(
            f"ledger row {row} combined_ic.mean={got!r} != "
            f"headline_provenance.headline.combined_ic={want!r}"
        )


def build_assembly(
    payloads: dict[str, tuple[object, str]],
    ledger_lines: list[str] | None,
) -> Assembly:
    """Pure assembly: payloads {(key: (parsed, sha))} + raw ledger lines.

    Registry order is pinned: panels (PANEL_FILES order) -> ledger rows ->
    docs -> artifact -> external literature/bookmarks. Each present source
    gets id S1..Sn in that order.
    """
    a = Assembly()
    objs = {k: v[0] for k, v in payloads.items()}  # parsed payload objects
    roles = {
        "metrics": "确认性头条读数(逐字嵌入)",
        "ic_monthly": "逐月 combined IC 面板序列",
        "calibration": "walk-forward 校准可靠性(ECE/pooled)",
        "score_diagnostics": "横截面分数诊断(秩自相关等)",
        "data_health": "面板新鲜度/来源健康图",
        "api_catalog": "静态 API 端点目录(license/source/freshness)",
        "evidence": "入账估计证据表(多相/多线)",
        "provenance": "头条冻结链(freeze→result)溯源",
    }
    for key, fname in PANEL_FILES.items():
        if key in payloads:
            obj, sha = payloads[key]
            a.payloads[key] = obj
            a.shas[key] = sha
            a.sources.append(_panel_source(fname, sha, roles[key]))
            a.sid[key] = f"S{len(a.sources)}"
    if ledger_lines:
        a.ledger_horizon = _latest_horizon_ref(ledger_lines)
        if a.ledger_horizon is not None:
            a.sources.append(Source(
                sid="",
                type="ledger",
                locator=(
                    f"runs/ledger.jsonl · line {a.ledger_horizon.lineno} · "
                    "phase=sensitivity_horizon · event=exploratory (latest)"
                ),
                integrity=(
                    f"sha256:{a.ledger_horizon.sha} "
                    f"(line {a.ledger_horizon.lineno} JSON 行文本)"
                ),
                license="Aionis append-only ledger (repo PolyForm-NC)",
                role="horizon 稳健性 sweep(h=10/42)探索行",
            ))
            a.sid["ledger_horizon"] = f"S{len(a.sources)}"
        prov = objs.get("provenance")
        if isinstance(prov, dict):
            a.ledger_freeze = _locate_freeze_ref(ledger_lines, prov)
            if a.ledger_freeze is not None:
                a.sources.append(Source(
                    sid="",
                    type="ledger",
                    locator=(
                        f"runs/ledger.jsonl · line {a.ledger_freeze.lineno} · "
                        f"event=config_committed · phase="
                        f"{a.ledger_freeze.rec.get('phase')}"
                    ),
                    integrity=(
                        f"sha256:{a.ledger_freeze.sha} "
                        f"(line {a.ledger_freeze.lineno} JSON 行文本)"
                    ),
                    license="Aionis append-only ledger (repo PolyForm-NC)",
                    role="config_committed 冻结行(先于任何 OOS 观测)",
                ))
                a.sid["ledger_freeze"] = f"S{len(a.sources)}"
            _verify_result_row(ledger_lines, prov)
    doc_roles = {
        "doc_phase_d": "Phase D 预注册(Relationship 主线;embargo=21 sessions)",
        "doc_track_c": "Track C 预注册(头条主张的治理线)",
        "doc_rubric": "数据接入 7 门(intake rubric)",
    }
    for key, rel in DOC_FILES.items():
        if key in payloads:
            _, sha = payloads[key]
            a.sources.append(Source(
                sid="",
                type="doc",
                locator=rel,
                integrity=f"sha256:{sha} (file bytes)",
                license="Aionis repo docs (repo PolyForm-NC)",
                role=doc_roles[key],
            ))
            a.sid[key] = f"S{len(a.sources)}"
    if "artifact_atlas" in payloads:
        _, sha = payloads["artifact_atlas"]
        a.sources.append(Source(
            sid="",
            type="artifact",
            locator=ARTIFACT_ATLAS,
            integrity=f"sha256:{sha} (file bytes)",
            license="Aionis research artifacts (repo PolyForm-NC)",
            role="G2 自包含证据工件(先例;E3 forward-live 状态陈述)",
        ))
        a.sid["artifact_atlas"] = f"S{len(a.sources)}"
    # External literature — integrity honestly self-declared (not machine-
    # verifiable); locators are bibliographic, rendered scheme-stripped.
    a.sources.append(Source(
        sid="",
        type="external",
        locator=(
            "Harvey, C.R., Liu, Y., Zhu, H. (2016), '...and the Cross-Section "
            "of Expected Returns', Review of Financial Studies 29(1):5-68 · "
            "doi:10.1093/rfs/hhv059 (host academic.oup.com)"
        ),
        integrity="external: self-declared (题录注记,非机器核验)",
        license="外部文献题录 (引用事实;版权归原出版方)",
        role="多重检验文献语境(t>3.0 阈值)",
    ))
    a.sid["ext_hlz"] = f"S{len(a.sources)}"
    # Bookmarks come from the SHARED frozen literals (ks_sources.RESEARCH_SOURCES),
    # NOT from the generated knowledge_shelf.json — the shelf panel embeds this
    # dossier's own content hash, so hashing the shelf here would create a
    # circular dependency with no fixpoint (round-34 integration finding).
    for i, bm in enumerate(RESEARCH_SOURCES):
        a.sources.append(Source(
            sid="",
            type="external",
            locator=(
                f"{_defang_url(str(bm.get('url', '')))} "
                "(scheme 剥离;字面量与 knowledge_shelf.json 同源:ks_sources.py)"
            ),
            integrity="external: self-declared (编辑书签,非机器核验)",
            license="外部站点 link-out (内容版权归原站)",
            role=f"编辑精选外部研究书签: {bm.get('name', '')}",
        ))
        a.sid[f"ext_bookmark_{i}"] = f"S{len(a.sources)}"
    for i, s in enumerate(a.sources, 1):
        s.sid = f"S{i}"
    return a


def load_payloads(panel_dir: Path | None = None) -> dict[str, tuple[object, str]]:
    """Read the committed panels; a missing file is simply absent (honest).

    Integrity shas are computed over LF-NORMALIZED bytes (the git-blob form)
    so the embedded values are platform-stable — a CRLF Windows checkout and
    a LF CI checkout of the same commit hash identically (round-58 CI-green
    fix; same rationale as the round-34 dossier/shelf LF normalization)."""
    base = PANEL_DIR if panel_dir is None else Path(panel_dir)

    def _lf_sha(fp: Path) -> str:
        return _sha_bytes(fp.read_bytes().replace(b"\r\n", b"\n"))

    payloads: dict[str, tuple[object, str]] = {}
    for key, fname in PANEL_FILES.items():
        fp = base / fname
        if fp.exists():
            b = fp.read_bytes()
            payloads[key] = (json.loads(b.decode("utf-8")), _sha_bytes(b.replace(b"\r\n", b"\n")))
    atlas = ROOT / ARTIFACT_ATLAS
    if atlas.exists():
        payloads["artifact_atlas"] = (None, _lf_sha(atlas))
    for key, rel in DOC_FILES.items():
        fp = ROOT / rel
        if fp.exists():
            payloads[key] = (None, _lf_sha(fp))
    return payloads


def read_ledger_lines(ledger_path: Path | None = None) -> list[str]:
    fp = LEDGER_PATH if ledger_path is None else Path(ledger_path)
    return fp.read_text(encoding="utf-8").splitlines() if fp.exists() else []


def assemble() -> Assembly:
    return build_assembly(load_payloads(), read_ledger_lines())


# ---------------------------------------------------------------------------
# Deterministic formatting helpers (same conventions as G2)
# ---------------------------------------------------------------------------


def _esc(v: object) -> str:
    return html.escape(str(v), quote=True)


def plain(x: object) -> str:
    """Minimal deterministic numeric literal, verbatim-equal to the panel value."""
    if isinstance(x, bool):
        return str(x)
    if isinstance(x, int):
        return str(x)
    f = float(x)
    if f.is_integer() and abs(f) < 1e16:
        return str(int(f))
    return repr(f)


def f4(x: object) -> str:
    return f"{float(x):.4f}"


def _px(v: float) -> str:
    s = f"{v:.2f}"
    return "0.00" if s == "-0.00" else s


def _na(label: str) -> str:
    return (
        f'<p class="na">来源缺失 / source unavailable:{_esc(label)} — '
        "本快照未提供该来源,如实降级呈现,不伪造数据。</p>"
    )


# ---------------------------------------------------------------------------
# Inline SVG figures (adapted from the G2 byte-stable precedent)
# ---------------------------------------------------------------------------


def _forest_svg(metrics: dict | None, evidence: object) -> str | None:
    rows: list[dict[str, object]] = []
    if isinstance(metrics, dict):
        rows.append({
            "lead": f"row {plain(metrics['ledger_row'])}",
            "label": "预注册确认主张(claim)",
            "est": float(metrics["combined_ic"]),
            "lo": float(metrics["ci_lo"]),
            "hi": float(metrics["ci_hi"]),
            "hot": True,
        })
    if isinstance(evidence, list):
        ordered = sorted(
            (e for e in evidence if isinstance(e, dict)),
            key=lambda r: int(r.get("n", 0)),
        )
        for e in ordered:
            if e.get("ci_lo") is None or e.get("ci_hi") is None:
                continue
            rows.append({
                "lead": f"#{int(e.get('n', 0))}",
                "label": str(e.get("result", "")),
                "est": float(e["estimate"]),
                "lo": float(e["ci_lo"]),
                "hi": float(e["ci_hi"]),
                "hot": str(e.get("grade", "")) == "CONFIRMATORY",
            })
    if not rows:
        return None

    vals = [abs(v) for r in rows for v in (r["est"], r["lo"], r["hi"])]
    half = max(math.ceil(max(vals) * 100) / 100, 0.02)
    width, left, rgt = 760, 276, 24
    pw = width - left - rgt
    row_h, top, bot = 30, 48, 52
    height = top + row_h * len(rows) + bot

    def x(v: float) -> float:
        return left + (v + half) / (2 * half) * pw

    def tx(v: float) -> str:
        return f"{v:.2f}".replace("-0.00", "0.00")

    s = [
        f'<svg viewBox="0 0 {width} {height}" role="img" '
        'aria-label="森林图:95% CI 与 SESOI 带对零线">',
    ]
    if metrics is not None:
        s.append(
            f'<text x="{left}" y="16" font-size="11" fill="{C_MUTED}">'
            f"■ SESOI 带实际显著域 ±{plain(metrics['sesoi'])}</text>"
        )
    s.append(
        f'<text x="{left + 215}" y="16" font-size="11" fill="{C_MUTED}">'
        "—— 预注册确认 / CONFIRMATORY</text>"
    )
    s.append(
        f'<text x="{left + 415}" y="16" font-size="11" fill="{C_MUTED}">'
        "—— 其它入账估计</text>"
    )
    y0, bh = top, height - bot - top
    if metrics is not None:
        ses = float(metrics["sesoi"])
        bx0, bx1 = x(-ses), x(ses)
        s.append(
            f'<rect x="{_px(bx0)}" y="{y0}" width="{_px(bx1 - bx0)}" '
            f'height="{bh}" fill="{C_TINT}"/>'
        )
    zx = _px(x(0.0))
    s.append(
        f'<line x1="{zx}" y1="{y0}" x2="{zx}" y2="{y0 + bh}" '
        f'stroke="#a1a1aa" stroke-width="1" stroke-dasharray="4 3"/>'
    )
    for i, r in enumerate(rows):
        cy = top + row_h * i + row_h / 2 + 4
        color = C_BLUE if r["hot"] else C_GRAY
        s.append(
            f'<text x="{left - 8}" y="{_px(cy)}" font-size="12" fill="{C_INK}" '
            f'text-anchor="end">{_esc(str(r["lead"]))} {_esc(str(r["label"]))}</text>'
        )
        s.append(
            f'<line x1="{_px(x(float(r["lo"])))}" y1="{_px(cy - 3)}" '
            f'x2="{_px(x(float(r["hi"])))}" y2="{_px(cy - 3)}" '
            f'stroke="{color}" stroke-width="2.5" stroke-linecap="round"/>'
        )
        s.append(
            f'<circle cx="{_px(x(float(r["est"])))}" cy="{_px(cy - 3)}" r="4" '
            f'fill="{color}" stroke="{C_PAPER}" stroke-width="1.5"/>'
        )
    axis_y = height - bot + 12
    s.append(
        f'<line x1="{left}" y1="{axis_y}" x2="{left + pw}" y2="{axis_y}" '
        f'stroke="{C_LINE}" stroke-width="1"/>'
    )
    ses = float(metrics["sesoi"]) if metrics is not None else None
    ticks = sorted({-half, 0.0, half} | ({-ses, ses} if ses is not None else set()))
    for t in ticks:
        s.append(
            f'<line x1="{_px(x(t))}" y1="{axis_y}" x2="{_px(x(t))}" '
            f'y2="{axis_y + 5}" stroke="{C_LINE}" stroke-width="1"/>'
        )
        s.append(
            f'<text x="{_px(x(t))}" y="{axis_y + 18}" font-size="11" '
            f'fill="{C_MUTED}" text-anchor="middle">{tx(t)}</text>'
        )
    s.append(
        f'<text x="{left + pw}" y="{axis_y + 34}" font-size="11" '
        f'fill="{C_MUTED}" text-anchor="end">横截面月度 rank-IC 差分</text>'
    )
    s.append("</svg>")
    return "\n".join(s)


def _bars_svg(ic_rows: object, sesoi: float | None) -> str | None:
    if not isinstance(ic_rows, list):
        return None
    rows = sorted(
        (
            r for r in ic_rows
            if isinstance(r, dict) and isinstance(r.get("combined"), int | float)
        ),
        key=lambda r: str(r.get("month", "")),
    )
    if not rows:
        return None
    vals = [abs(float(r["combined"])) for r in rows]
    half = max(math.ceil(max(vals) * 100) / 100, 0.02)
    width, left, rgt = 760, 44, 12
    pw = width - left - rgt
    top, ph, bot = 30, 176, 40
    height = top + ph + bot
    n = len(rows)
    slot = pw / n
    bw = min(12.0, slot * 0.68)

    def xx(i: int) -> float:
        return left + slot * i + slot / 2

    def y(v: float) -> float:
        return top + (half - v) / (2 * half) * ph

    zero = y(0.0)
    s = [
        f'<svg viewBox="0 0 {width} {height}" role="img" '
        f'aria-label="逐月 combined IC 序列条形图({n} 个月)">',
        f'<text x="{left}" y="16" font-size="11" fill="{C_MUTED}">'
        f"combined IC · {n} 个月面板序列(蓝 = 非负 / 灰 = 负"
        + (f" / 浅带 = SESOI ±{plain(sesoi)}" if sesoi is not None else "")
        + ")</text>",
    ]
    if sesoi is not None:
        s.append(
            f'<rect x="{left}" y="{_px(y(sesoi))}" width="{pw}" '
            f'height="{_px(y(-sesoi) - y(sesoi))}" fill="{C_TINT}"/>'
        )
    for i, r in enumerate(rows):
        v = float(r["combined"])
        color = C_BLUE if v >= 0 else C_GRAY
        y_top, y_bot = (y(v), zero) if v >= 0 else (zero, y(v))
        s.append(
            f'<rect x="{_px(xx(i) - bw / 2)}" y="{_px(y_top)}" '
            f'width="{_px(bw)}" height="{_px(max(y_bot - y_top, 0.5))}" '
            f'fill="{color}"/>'
        )
        month = str(r.get("month", ""))
        if month.endswith("-01"):
            s.append(
                f'<text x="{_px(xx(i))}" y="{height - 20}" font-size="10" '
                f'fill="{C_MUTED}" text-anchor="middle">{_esc(month[:4])}</text>'
            )
    s.append(
        f'<line x1="{left}" y1="{_px(zero)}" x2="{left + pw}" y2="{_px(zero)}" '
        f'stroke="#a1a1aa" stroke-width="1"/>'
    )
    for v, lab in ((half, f"+{half:.2f}"), (0.0, "0"), (-half, f"-{half:.2f}")):
        s.append(
            f'<text x="{left - 6}" y="{_px(y(v) + 3)}" font-size="10" '
            f'fill="{C_MUTED}" text-anchor="end">{lab}</text>'
        )
    s.append("</svg>")
    return "\n".join(s)


# ---------------------------------------------------------------------------
# Section builders (each number-bearing line carries [S#] chips)
# ---------------------------------------------------------------------------


def _sec1_summary(a: Assembly) -> list[str]:
    m = a.payloads.get("metrics")
    lines = ["<section>", "<h2>1 · 执行摘要 / Executive summary</h2>"]
    if not isinstance(m, dict):
        lines.append(_na("metrics.json(头条读数)"))
        lines.append("</section>")
        return lines
    c = a.cite
    c_opt = a.cite_opt
    lines.append(
        "<p>预注册两尾主张(每相单一):<em>处理信号(treatment)相对纯基本面基线的"
        "横截面月度 rank-IC <span class=\"accent\">差分</span>与零无差异</em>。"
        "本档案呈现该主张一次确认性测量的完整溯源链:NULL 判定 + 窄置信区间 = "
        "有信息量的结论(纪律的胜利),不是失败。</p>"
    )
    rows = [
        ("combined_ic · 月度 rank-IC 差分", plain(m["combined_ic"])),
        ("95% CI(HAC)", f"[{plain(m['ci_lo'])}, {plain(m['ci_hi'])}]"),
        ("p(HAC)", plain(m["p"])),
        ("n_months · 样本外月数", plain(m["n_months"])),
        ("verdict · 预注册两尾判定", f'<span class="badge">{_esc(m["verdict"])}</span>'),
        ("SESOI · 实际显著域", f"±{plain(m['sesoi'])}"),
        ("config_sig_short · 冻结配置签名", _esc(m["config_sig_short"])),
        ("ledger_row · 结果账本行", plain(m["ledger_row"])),
        ("jt_look1 · J-T 等价门(如实呈现)", _esc(m["jt_look1"])),
        ("h6 · 确定性校验", _esc(m["h6"])),
    ]
    cells = "".join(
        f"<div><dt>{k}</dt><dd>{v} {c('metrics')}{c_opt('provenance')}</dd></div>"
        for k, v in rows
    )
    lines.append(f'<dl class="card">{cells}</dl>')
    lines.append(
        f'<p class="note">latest_month={_esc(m.get("latest_month"))} · '
        f'n_picks_total={plain(m.get("n_picks_total"))} · '
        f'面板 snapshot_ts={_esc(m.get("snapshot_ts"))} '
        f"{c('metrics')};数字逐字取自 metrics.json,不重算、不四舍五入。</p>"
    )
    lines.append("</section>")
    return lines


def _sec2_design(a: Assembly) -> list[str]:
    c = a.cite
    c_opt = a.cite_opt
    lines = ["<section>", "<h2>2 · 研究设计与门禁 / Research design and gates</h2>"]
    cites = [k for k in ("doc_phase_d", "doc_track_c", "doc_rubric") if k in a.sid]
    if cites:
        lines.append(f'<p class="sub">治理文档:{c(*cites)}</p>')
    else:
        lines.append(_na("预注册/治理文档"))
    if "doc_track_c" in a.sid:
        lines.append(
            "<p><strong>预注册设计(Track C,头条主张的治理线):</strong>"
            "双区域条件化 rank-IC,chronological walk-forward;config_committed "
            "先于任何样本外观测入 ledger;修订走累积 amend(新签名 = 新账本行,"
            "绝不静默覆盖)。"
            f'{c("doc_track_c")}{c_opt("provenance")}</p>'
        )
    if "doc_phase_d" in a.sid:
        lines.append(
            "<p><strong>防泄漏交叉验证:</strong>PurgedGroupKFold + "
            "embargo=21 sessions(group=月),标签无泄漏;13D/基本面按 filed "
            f'date 的 PIT 契约。{c("doc_phase_d")}</p>'
        )
    if "doc_rubric" in a.sid:
        lines.append(
            "<p><strong>7 门数据摄入(全部必须过关):</strong>license 许可 / "
            "PIT 时点 / no-revision 无修订 / snapshot 快照 / exploratory-only "
            f'仅探索 / selection-honesty 选择诚实 / politeness 礼貌限速。'
            f'{c("doc_rubric")}</p>'
        )
    m = a.payloads.get("metrics")
    if isinstance(m, dict):
        lines.append(
            "<p><strong>确定性(H6):</strong>"
            f'h6={_esc(m["h6"])} — n_jobs=1、种子全固定、版本锁定;IC 序列与'
            f'原始分数跨重跑位级一致。{c("metrics")}</p>'
        )
    lines.append("</section>")
    return lines


def _sec3_sources(a: Assembly) -> list[str]:
    c = a.cite
    c_opt = a.cite_opt
    lines = ["<section>", "<h2>3 · 数据来源与可溯源性 / Data sources and provenance</h2>"]
    cat = a.payloads.get("api_catalog")
    if isinstance(cat, dict) and isinstance(cat.get("endpoints"), list):
        eps = [e for e in cat["endpoints"] if isinstance(e, dict)]
        lines.append(
            "<p><strong>静态 API 目录:</strong>"
            f'{plain(len(eps))} 个端点,全部 status=available;每个端点登记 '
            "license + source + freshness(as_of)。"
            f'{c("api_catalog")}</p>'
        )
        fresh: dict[str, int] = {}
        for e in eps:
            fresh[str(e.get("freshness"))] = fresh.get(str(e.get("freshness")), 0) + 1
        lic: dict[str, int] = {}
        for e in eps:
            lic[str(e.get("license"))] = lic.get(str(e.get("license")), 0) + 1
        asof: dict[str, int] = {}
        for e in eps:
            raw = e.get("as_of")
            k = "未标注" if raw is None else str(raw)[:7]
            asof[k] = asof.get(k, 0) + 1
        rows = [
            ("<tr><td class=\"l\">freshness</td><td class=\"l\">"
             f"{_esc(k)}</td><td>{plain(v)}</td>"
             f'<td class="l">{c("api_catalog")}</td></tr>')
            for k, v in sorted(fresh.items())
        ]
        rows += [
            ("<tr><td class=\"l\">license</td><td class=\"l\">"
             f"{_esc(k)}</td><td>{plain(v)}</td>"
             f'<td class="l">{c("api_catalog")}</td></tr>')
            for k, v in sorted(lic.items(), key=lambda kv: (-kv[1], kv[0]))
        ]
        rows += [
            ("<tr><td class=\"l\">as_of(年-月)</td><td class=\"l\">"
             f"{_esc(k)}</td><td>{plain(v)}</td>"
             f'<td class="l">{c("api_catalog")}</td></tr>')
            for k, v in sorted(asof.items())
        ]
        thead = (
            "<tr><th class=\"l\">分组</th><th class=\"l\">取值</th>"
            "<th>端点数</th><th class=\"l\">S#</th></tr>"
        )
        lines.append(
            f'<div class="tbl"><table><thead>{thead}</thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div>'
        )
        lines.append(
            f'<p class="note">source 字段多为端点级唯一描述(细节见 api_catalog '
            f'面板),故按 license / freshness / as_of 分组计数呈现。'
            f'{c("api_catalog")}</p>'
        )
        lines.append(
            "<p><strong>实时价格边界:</strong>live quotes 为独立的 display-only "
            "Worker,绝不进入研究管线(端点细节见 api_catalog 面板)。"
            f'{c("api_catalog")}</p>'
        )
    else:
        lines.append(_na("api_catalog.json"))
    dh = a.payloads.get("data_health")
    if isinstance(dh, dict) and isinstance(dh.get("panels"), list):
        s = dh.get("summary")
        if isinstance(s, dict):
            lines.append(
                "<p><strong>面板新鲜度三类</strong>(frozen = 由冻结 OOS 工件派生,"
                "daily 通道刻意不推进它们;cadence = 按来源发布节奏):"
                f'共 {plain(s.get("n_panels"))} 个面板 — frozen '
                f'{plain(s.get("n_frozen"))} / daily {plain(s.get("n_daily"))} / '
                f'cadence {plain(s.get("n_cadence"))}。{c("data_health")}</p>'
            )
        else:
            lines.append(_na("data_health.summary"))
        lines.append(
            f'<p class="note">frozen 面板刻意不推进——用更新数据重算它们 = '
            f'rerun-to-significance,被契约禁止。'
            f'{c("data_health")}{c_opt("api_catalog")}</p>'
        )
    else:
        lines.append(_na("data_health.json"))
    lines.append("</section>")
    return lines


def _sec4_analysis(a: Assembly) -> list[str]:
    c = a.cite
    c_opt = a.cite_opt
    m = a.payloads.get("metrics")
    prov = a.payloads.get("provenance")
    lines = ["<section>", "<h2>4 · 建模与分析 / Modeling and analysis</h2>"]
    lines.append("<h3>冻结链 / frozen chain(config_sig → freeze → result → panel)</h3>")
    if isinstance(prov, dict) and isinstance(m, dict):
        fr = prov.get("freeze") if isinstance(prov.get("freeze"), dict) else {}
        ct = prov.get("contract") if isinstance(prov.get("contract"), dict) else {}
        chain = [
            ("config_sig_short", _esc(prov.get("config_sig_short"))),
            ("config_sig_source", _esc(prov.get("config_sig_source"))),
            ("freeze(config_committed)",
             f"row {plain(fr.get('ledger_row'))} @ {_esc(fr.get('ts'))} · "
             f"event {_esc(fr.get('event'))} · sig {_esc(fr.get('config_sig_short'))}"),
            ("result(confirmatory:first)",
             f"row {plain(prov.get('ledger_row'))} @ {_esc(prov.get('result_ts'))} · "
             f"event {_esc(prov.get('result_event'))}"),
            ("contract", f"freeze_before_result={plain(bool(ct.get('freeze_before_result')))} — "
                         f"{_esc(ct.get('note'))}"),
            ("panel snapshot", f"metrics @ {_esc(m.get('snapshot_ts'))} · "
                               f"provenance @ {_esc(prov.get('snapshot_ts'))}"),
        ]
        freeze_cites = c("provenance", "metrics") + c_opt("ledger_freeze")
        cells = "".join(
            f"<div><dt>{k}</dt><dd>{v} {freeze_cites}</dd></div>"
            for k, v in chain
        )
        lines.append(f'<dl class="kv">{cells}</dl>')
    else:
        lines.append(_na("headline_provenance.json / metrics.json(冻结链)"))
    lines.append("<h3>合并 IC 森林图(95% CI vs SESOI 带 vs 零线)</h3>")
    svg = _forest_svg(m if isinstance(m, dict) else None, a.payloads.get("evidence"))
    if svg is not None:
        lines.append(svg)
        lines.append(
            '<p class="note">蓝 = 预注册确认/CONFIRMATORY,灰 = 其它入账估计;'
            f"读数见 evidence 面板与头条卡。{c_opt('metrics', 'evidence')}</p>"
        )
    else:
        lines.append(_na("metrics.json 与 evidence.json(森林图)"))
    lines.append("<h3>逐月 combined IC(面板全序列)</h3>")
    ic = a.payloads.get("ic_monthly")
    bars = _bars_svg(ic, float(m["sesoi"]) if isinstance(m, dict) else None)
    if bars is not None and isinstance(ic, list):
        n_rows = sum(
            1 for r in ic
            if isinstance(r, dict) and isinstance(r.get("combined"), int | float)
        )
        lines.append(bars)
        lines.append(
            f'<p class="note">{plain(n_rows)} 个月(面板实有 combined 记录;'
            f"方向编码:蓝 = 非负 / 灰 = 负,非红绿)。"
            f"{c('ic_monthly')}{c_opt('metrics')}</p>"
        )
    else:
        lines.append(_na("ic_monthly.json(逐月 IC 序列图)"))
    lines.append("<h3>校准汇总(walk-forward Platt)</h3>")
    cal = a.payloads.get("calibration")
    if isinstance(cal, dict) and isinstance(cal.get("regions"), dict):
        lines.append(
            f'<p>method={_esc(cal.get("method"))} · walk_forward='
            f'{plain(bool(cal.get("walk_forward")))} · min_train_months='
            f'{plain(cal.get("min_train_months"))}。{c("calibration")}</p>'
        )
        reg_rows = []
        for name in sorted(cal["regions"]):
            r = cal["regions"][name]
            if not isinstance(r, dict):
                continue
            reg_rows.append(
                f"<tr><td class=\"l\">{_esc(name)}</td>"
                f"<td>{fmt_num(r.get('n_months'))}</td>"
                f"<td>{fmt_num(r.get('pooled_ece'))}</td>"
                "<td>"
                f"{fmt_num(len(r['series']) if isinstance(r.get('series'), list) else None)}"
                "</td>"
                f'<td class="l">{c("calibration")}</td></tr>'
            )
        thead = (
            "<tr><th class=\"l\">region</th><th>n_months(walk-forward)</th>"
            "<th>pooled ECE</th><th>series 长度</th><th class=\"l\">S#</th></tr>"
        )
        lines.append(
            f'<div class="tbl"><table><thead>{thead}</thead>'
            f'<tbody>{"".join(reg_rows)}</tbody></table></div>'
        )
        lines.append(
            f'<p class="note">仅 2 参数显示映射被 refit;冻结 LightGBM 学习器'
            f'从不触碰——非研究主张。{c("calibration")}</p>'
        )
    else:
        lines.append(_na("calibration_reliability.json"))
    lines.append("<h3>score 诊断摘要(横截面分数)</h3>")
    sd = a.payloads.get("score_diagnostics")
    if isinstance(sd, list) and sd:
        rows = [r for r in sd if isinstance(r, dict)]
        ras = [float(r["rank_autocorr"]) for r in rows if r.get("rank_autocorr") is not None]
        months = sorted({str(r.get("month", "")) for r in rows})
        regions = sorted({str(r.get("region", "")) for r in rows})
        lines.append(
            f'<p>{plain(len(rows))} 行(region×month) · months {plain(len(months))} '
            f'({_esc(months[0] if months else "—")} … '
            f'{_esc(months[-1] if months else "—")}) · regions '
            f'{" / ".join(_esc(x) for x in regions)}。{c("score_diagnostics")}</p>'
        )
        lines.append(
            "<p>rank 自相关(非空 "
            f'{plain(len(ras))} 行):min {f4(min(ras)) if ras else "—"} · '
            f'max {f4(max(ras)) if ras else "—"} · 缺失 '
            f'{plain(len(rows) - len(ras))} 行(如实呈现,不插补)。'
            f'{c("score_diagnostics")}</p>'
        )
    else:
        lines.append(_na("score_diagnostics.json"))
    lines.append("<h3>horizon 稳健性(探索性 sweep,h=10 / h=42)</h3>")
    lh = a.ledger_horizon
    if lh is not None:
        rec = lh.rec
        results = rec.get("results") if isinstance(rec.get("results"), dict) else {}
        hz_rows = []
        for h in sorted(results, key=lambda z: str(z)):
            block = results[h]
            if not isinstance(block, dict):
                continue
            for ph in ("B", "C", "D", "E1"):
                r = block.get(ph)
                if not isinstance(r, dict):
                    continue
                holds = bool(r.get("null_holds"))
                mark = (
                    '<span class="holds-true">成立</span>' if holds
                    else '<span class="holds-false">不成立</span>'
                )
                hz_rows.append(
                    f"<tr><td>h={_esc(h)}</td><td class=\"l\">{_esc(ph)}</td>"
                    f"<td class=\"l\">{_esc(r.get('arm_enhanced'))}</td>"
                    f"<td>{fmt_num(r.get('mean_diff'))}</td>"
                    f"<td>{fmt_num(r.get('ci_lo'))}</td>"
                    f"<td>{fmt_num(r.get('ci_hi'))}</td>"
                    f"<td>{mark}</td>"
                    f'<td class="l">{c("ledger_horizon")}</td></tr>'
                )
        thead = (
            "<tr><th>horizon</th><th class=\"l\">相</th><th class=\"l\">enhanced 臂</th>"
            "<th>mean_diff</th><th>ci_lo</th><th>ci_hi</th>"
            "<th>null_holds</th><th class=\"l\">S#</th></tr>"
        )
        lines.append(
            f'<div class="tbl"><table><thead>{thead}</thead>'
            f'<tbody>{"".join(hz_rows)}</tbody></table></div>'
        )
        lines.append(
            "<p>判定准则(账本行原文):"
            f'{_esc(rec.get("null_criterion"))};frozen_confirmatory_horizon='
            f'{plain(rec.get("frozen_confirmatory_horizon"))}。'
            f'账本行 ts={_esc(rec.get("ts"))}。{c("ledger_horizon")}</p>'
        )
        lines.append(
            f'<p class="note">状态:EXPLORATORY(h≠21 = changed config),'
            f'无 confirmatory 行写入;数值为 4 位小数定长渲染,完整精度见账本行'
            f'原文。{c("ledger_horizon")}</p>'
        )
    else:
        lines.append(_na("runs/ledger.jsonl 的 sensitivity_horizon 探索行"))
    lines.append("</section>")
    return lines


def fmt_num(x: object) -> str:
    """Table cell for measured floats/ints; None renders as an em-dash."""
    if x is None:
        return "—"
    if isinstance(x, bool):
        return plain(x)
    if isinstance(x, int):
        return plain(x)
    if isinstance(x, float):
        return f4(x)
    return _esc(x)


def _sec5_evidence(a: Assembly) -> list[str]:
    c = a.cite
    c_opt = a.cite_opt
    lines = ["<section>", "<h2>5 · 证据与文献语境 / Evidence and literature context</h2>"]
    ev = a.payloads.get("evidence")
    if isinstance(ev, list) and ev:
        rows = [e for e in ev if isinstance(e, dict)]
        ordered = sorted(rows, key=lambda r: int(r.get("n", 0)))
        ns = [int(r.get("n", 0)) for r in ordered]
        missing = sorted(set(range(min(ns), max(ns) + 1)) - set(ns)) if ns else []
        body = []
        for e in ordered:
            body.append(
                f"<tr><td>{fmt_num(e.get('n'))}</td>"
                f"<td class=\"l\">{_esc(e.get('result'))}</td>"
                f"<td>{fmt_num(e.get('estimate'))}</td>"
                f"<td>{fmt_num(e.get('ci_lo'))}</td>"
                f"<td>{fmt_num(e.get('ci_hi'))}</td>"
                f"<td>{fmt_num(e.get('p'))}</td>"
                f"<td>{fmt_num(e.get('n_months'))}</td>"
                f"<td class=\"l\">{_esc(e.get('grade'))}</td>"
                f'<td class="l">{c("evidence")}</td></tr>'
            )
        thead = (
            "<tr><th>#</th><th class=\"l\">result</th><th>estimate</th>"
            "<th>ci_lo</th><th>ci_hi</th><th>p</th><th>n_months</th>"
            "<th class=\"l\">grade</th><th class=\"l\">S#</th></tr>"
        )
        lines.append(
            f'<div class="tbl"><table><thead>{thead}</thead>'
            f'<tbody>{"".join(body)}</tbody></table></div>'
        )
        miss_txt = (
            f"编号缺 {plain(missing[0])}(面板如实缺号)" if missing else "编号连续"
        )
        lines.append(
            f'<p class="note">{plain(len(ordered))} 行(面板实有;{miss_txt};'
            f"CI 缺失以 — 如实呈现,不入森林图)。{c('evidence')}</p>"
        )
    else:
        lines.append(_na("evidence.json"))
    if "ext_hlz" in a.sid:
        m = a.payloads.get("metrics")
        p_txt = plain(m["p"]) if isinstance(m, dict) and "p" in m else "—"
        lines.append(
            "<p><strong>多重检验文献语境:</strong>Harvey-Liu-Zhu(2016)对因素"
            "文献的多重检验审计以 t&gt;3.0 为更高的显著门槛;本研究引用该阈值"
            f'仅作外部文献坐标——headline p(HAC)={p_txt} 的 NULL 判定不因外部'
            f'阈值调整(两尾预注册判定优先)。{c("ext_hlz")}{c_opt("metrics")}</p>'
        )
    bm_indices = [
        int(k[len("ext_bookmark_"):])
        for k in a.sid if k.startswith("ext_bookmark_")
    ]
    if bm_indices:
        lines.append(
            '<p><strong>编辑精选外部研究书签</strong>(与 knowledge_shelf 面板'
            'research_sources 同源字面量 ks_sources.py;链接为 scheme 剥离的'
            '纯文本,完整 URL 见字面量文件;每条各自标注引用号):</p>'
        )
        items = []
        for i in sorted(bm_indices):
            key = f"ext_bookmark_{i}"
            if i >= len(RESEARCH_SOURCES):
                continue
            bm = RESEARCH_SOURCES[i]
            if not isinstance(bm, dict):
                continue
            src = next(s for s in a.sources if s.sid == a.sid[key])
            items.append(
                f"<li><strong>{_esc(bm.get('name'))}</strong> · "
                f"{_esc(bm.get('org'))} — {_esc(bm.get('desc_zh'))} "
                f'<code class="loc">{_esc(src.locator)}</code> '
                f'{c(key)}</li>'
            )
        lines.append(f'<ul class="marks">{"".join(items)}</ul>')
    else:
        lines.append(_na("ks_sources.py(外部研究书签)"))
    lines.append("</section>")
    return lines


def _sec6_limits(a: Assembly) -> list[str]:
    c = a.cite
    c_opt = a.cite_opt
    m = a.payloads.get("metrics")
    lines = ["<section>", "<h2>6 · 局限与边界 / Limitations and boundaries</h2>"]
    lines.append("<ul class=\"methods\">")
    if isinstance(m, dict):
        lines.append(
            "<li><strong>NULL 判定的诚实呈现:</strong>"
            f'verdict={_esc(m["verdict"])}(两尾预注册判定规则)——零结果 + 窄 CI '
            "是预期内且有信息量的结果(纪律的胜利),不是失败;本档案不修饰该读数。"
            f'{c("metrics")}</li>'
        )
        lines.append(
            "<li><strong>等价性门(如实):</strong>"
            f'jt_look1={_esc(m["jt_look1"])} —— 不宣称等价,只呈现门读数。'
            f'{c("metrics")}</li>'
        )
    else:
        lines.append(_na("metrics.json(NULL/jt 读数)"))
    lh = a.ledger_horizon
    if lh is not None:
        lines.append(
            "<li><strong>探索 vs 确认分离:</strong>horizon sweep(h=10/42)为 "
            "EXPLORATORY(改 horizon = 改配置),无 confirmatory 行写入;"
            "evidence 面板的 grade 列同样区分 CV-proxy / 探索 / 确认。"
            f'{c("ledger_horizon")}{c_opt("evidence")}</li>'
        )
    if "artifact_atlas" in a.sid:
        lines.append(
            "<li><strong>E3 forward-live 状态(如实):</strong>forward-live "
            "已实现;E3 契约已冻结(业主 2026-08-03 裁决,provider_cutoff 为经验"
            "探针边界),2026-08-31 月末截面影子链 READINESS PASS(证据在 "
            "reports/audits/),headline 判定待影子样本(业主门)——本档案不宣称"
            f'已完成的活体验证,与 G2 工件陈述一致。{c("artifact_atlas")}</li>'
        )
    if "data_health" in a.sid:
        lines.append(
            "<li><strong>面板新鲜度边界:</strong>frozen 面板由冻结 OOS 工件派生"
            "且刻意不推进;所有 as-of 戳取自面板/账本字段,本档案无运行时时钟。"
            f'{c("data_health")}{c_opt("api_catalog")}</li>'
        )
    lines.append(
        "<li><strong>语态边界:</strong>本档案呈现测量与设计,不构成投资建议,"
        "不含任何收益承诺。</li>"
    )
    lines.append("</ul></section>")
    return lines


def _sregistry_block(a: Assembly, html_text_before: str) -> str:
    """Section 7: the full S-registry table + machine-check conclusions."""
    cited = re.findall(r"\[(S\d+)\]", html_text_before)
    n_cited_refs = len(cited)
    uniq = sorted(set(cited), key=lambda s: int(s[1:]))
    rows = []
    for s in a.sources:
        rows.append(
            f"<tr><td>{_esc(s.sid)}</td><td class=\"l\">{_esc(s.type)}</td>"
            f"<td class=\"l loc\">{_esc(s.locator)}</td>"
            f"<td class=\"l loc\">{_esc(s.integrity)}</td>"
            f"<td class=\"l\">{_esc(s.license)}</td>"
            f"<td class=\"l\">{_esc(s.role)}</td></tr>"
        )
    thead = (
        "<tr><th>S#</th><th class=\"l\">type</th><th class=\"l\">locator</th>"
        "<th class=\"l\">integrity</th><th class=\"l\">license</th>"
        "<th class=\"l\">role</th></tr>"
    )
    return (
        "<section>",
        "<h2>7 · 引用完整性自检 / Citation-integrity self-check</h2>",
        "<p>下表是本档案的完整来源登记表(S-registry),含 machine-check 结论。",
        "<!-- s-registry -->",
        f'<div class="tbl"><table><thead>{thead}</thead>'
        f'<tbody>{"".join(rows)}</tbody></table></div>',
        '<p class="note">登记表说明:panel / ledger / doc / artifact 的 '
        "integrity 为生成时现算的 sha256;external 条目如实标注 "
        "self-declared(不可机器核验)。</p>",
        f'<p class="note">机检结论(生成器内置,违反即 raise 不静默):'
        f'S-registry 共 {plain(len(a.sources))} 条;正文 [S#] 引用 '
        f'{plain(n_cited_refs)} 处、覆盖 {plain(len(uniq))} 条;每条来源被引 '
        f"≥1 次;孤儿引用(引用无来源)0 条;含数字而无引用的正文行 0 行。"
        f"external 条目的 URL 以 scheme 剥离形态呈现(零外部资源约束),完整 "
        f"URL 在 ks_sources.py 字面量内(与 knowledge_shelf 面板同源)。</p>",
        "<!-- /s-registry -->",
        "</section>",
    )


# ---------------------------------------------------------------------------
# Citation-closure hard gate
# ---------------------------------------------------------------------------

_CITE_RE = re.compile(r"\[(S\d+)\]")
_STRUCTURAL_LINE_RE = re.compile(
    r"^\s*<h[1-6]>"  # section ordinals in headings
    r"|\bv\d+\b"  # artifact / generator version strings
    r"|\d+\.\d+\.\d+"  # generator semver
)


def check_citation_closure(html_text: str, sources: list) -> None:
    """Hard gate: raise unless citations <-> registry and numbers <-> citations.

    Scans the rendered body for (a) citations that resolve to no registered
    source, (b) registered sources never cited, and (c) digit-bearing content
    lines without any [S#] chip. Excluded from (c): <head>, inline <svg>
    rendering geometry, the S-registry declaration table itself (between the
    pinned ``<!-- s-registry -->`` markers), and structural version/heading
    patterns pinned in the allowlist regex.
    """
    ids = {s.sid for s in sources}
    cited = set(_CITE_RE.findall(html_text))
    orphans = sorted(cited - ids, key=lambda s: int(s[1:]))
    if orphans:
        raise CitationClosureError(f"引用无来源 / citations without source: {orphans}")
    unreferenced = sorted(ids - cited, key=lambda s: int(s[1:]))
    if unreferenced:
        raise CitationClosureError(
            f"来源从未被引用 / sources never cited: {unreferenced}"
        )
    body = html_text.split("<body>", 1)[1].split("</body>", 1)[0]
    body = re.sub(r"<svg.*?</svg>", "", body, flags=re.S)
    body = re.sub(r"<!-- s-registry -->.*?<!-- /s-registry -->", "", body, flags=re.S)
    violations = []
    for line in body.splitlines():
        if "[S" in line or not re.search(r"\d", line):
            continue
        if _STRUCTURAL_LINE_RE.search(line):
            continue
        violations.append(line.strip()[:120])
    if violations:
        raise CitationClosureError(
            f"数字无引用 / numbers without citation ({len(violations)} lines): "
            f"{violations[:5]}"
        )


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------


def _head() -> list[str]:
    return [
        "<!DOCTYPE html>",
        '<html lang="zh-CN">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f'<meta name="generator" content="aionis export_research_dossier.py '
        f"{GENERATOR_VERSION} (dossier {DOSSIER_VERSION})\">",
        f"<title>Aionis 溯源研究档案 · Research Dossier ({ARTIFACT_ID})</title>",
        "<!--",
        f"  Aionis provenance-chained research dossier — {ARTIFACT_ID}",
        f"  dossier version: {DOSSIER_VERSION}",
        "  byte-stable artifact — regenerate with: "
        "`uv run python scripts/export_research_dossier.py`",
        f"  generator version: {GENERATOR_VERSION}",
        "  self-contained: zero JS, zero external resources, zero font requests",
        "  (system font stack only). All numbers are verbatim values from",
        "  committed panels / the runs ledger; external bookmarks are rendered",
        "  scheme-stripped (full URLs in the shared ks_sources.py literals).",
        "  Citation closure ([S#] registry) is enforced at render time.",
        "-->",
        "<style>",
        _CSS.rstrip(),
        "</style>",
        "</head>",
    ]


def render(a: Assembly) -> str:
    """Pure renderer: Assembly in, closure-checked byte-stable HTML out."""
    parts = _head()
    parts.append("<body>")
    parts.append("<main>")
    parts.append(
        "<section>",
    )
    parts.append(
        f"<h1>Aionis 溯源研究档案 · Research Dossier "
        f'<span class="badge">{ARTIFACT_ID}</span></h1>'
    )
    parts.append(
        '<p class="sub">来源研究 → 报告生成 → 建模与分析,全程 [S#] 可溯源。'
        "One pre-registered two-tailed claim per phase — cross-sectional "
        "monthly rank-IC on S&amp;P 500 point-in-time constituents。</p>"
    )
    parts.append("</section>")
    parts.extend(_sec1_summary(a))
    parts.extend(_sec2_design(a))
    parts.extend(_sec3_sources(a))
    parts.extend(_sec4_analysis(a))
    parts.extend(_sec5_evidence(a))
    parts.extend(_sec6_limits(a))
    parts.extend(_sregistry_block(a, "\n".join(parts)))
    parts.append(
        "<footer>",
    )
    parts.append(
        f"Aionis — falsifiable, anti-leakage research harness. 溯源研究档案 "
        f"{ARTIFACT_ID}(dossier {DOSSIER_VERSION},generator "
        f"{GENERATOR_VERSION}):零 JS、零外部资源、零字体请求;字节稳定(无运行时"
        "时钟、排序写死、LF 换行);浏览器直开即读。配色:浅色卡面、单蓝强调 "
        "#0059ec(WCAG AA),方向编码蓝/灰明度差,非红绿。",
    )
    parts.append("</footer>")
    parts.append("</main>")
    parts.append("</body>")
    parts.append("</html>")
    out = "\n".join(parts) + "\n"
    check_citation_closure(out, a.sources)
    return out


def main() -> int:
    if not (ROOT / "runs/results").exists():
        print(
            "[export-research-dossier] SKIP: frozen runs/results tree absent "
            "(fresh checkout; tracked HTML retains last-committed value)"
        )
        return 0
    a = assemble()
    out = render(a)
    archive_if_changed(OUT, out.encode("utf-8"))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="\n") as f:
        f.write(out)
    digest = hashlib.sha256(OUT.read_bytes()).hexdigest()
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes) sha256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


# ---------------------------------------------------------------------------
# R2-full S2 — per-phase meta dossiers (B / D / E1)
#
# Meta-only self-contained cards for the phases that do not have the full
# Track-C citation-closed dossier. Every value is machine-read from the frozen
# per-phase artifacts (differential.json / ic parquets / meta.json /
# controls.json) and the ledger — zero hand-typed numbers, zero wall clock,
# byte-stable double-run. Honest limitation, disclosed in the card itself: a
# meta card carries the claim's numbers and reconciliation, not the full [S#]
# provenance chain (that depth exists for the headline Track C claim).
#
# NOTE: pandas (`pd`) is imported lazily inside _ic_summary — this module's
# header deliberately stays stdlib-only so the ledger probe paths in tests do
# not pay the pandas import cost.

_META_PHASES: tuple[dict, ...] = (
    {"phase": "B", "ledger_row": 28, "prereg": "docs/phase-b-preregistration.md"},
    {"phase": "D", "ledger_row": 34, "prereg": "docs/phase-d-preregistration.md"},
    {"phase": "E1", "ledger_row": 37, "prereg": "docs/phase-e-preregistration.md"},
)


def _phase_dossier_html(phase, ledger_row, prereg, results_dir, ledger_lines):
    import pandas as pd

    rec = json.loads(ledger_lines[ledger_row - 1])
    sig = str(rec.get("config_sig", ""))
    rdir = results_dir / sig
    if not rdir.is_dir():
        raise ValueError(f"results dir missing for {phase}: {rdir}")
    diff = json.loads((rdir / "differential.json").read_text(encoding="utf-8"))

    def _ic_summary(name):
        p = rdir / name
        if not p.exists():
            return {"present": False}
        df = pd.read_parquet(p)
        out = {"present": True, "rows": int(len(df)),
               "columns": [str(c) for c in df.columns]}
        num = df.select_dtypes(include="number")
        if num.shape[1]:
            col = num.columns[0]
            out["first_col"] = str(col)
            out["mean"] = float(num[col].mean())
            out["min"] = float(num[col].min())
            out["max"] = float(num[col].max())
        return out

    meta = json.loads((rdir / "meta.json").read_text(encoding="utf-8"))
    controls = json.loads((rdir / "controls.json").read_text(encoding="utf-8"))

    rows = "".join(
        f"<tr><th>{_esc(k)}</th><td>{_esc(v)}</td></tr>"
        for k, v in (
            ("phase", phase),
            ("ledger_row", ledger_row),
            ("config_sig", sig),
            ("H6_deterministic", meta.get("h6_deterministic", "—")),
            ("mean_diff", repr(diff.get("mean_diff"))),
            ("ci_lo", repr(diff.get("ci_lo"))),
            ("ci_hi", repr(diff.get("ci_hi"))),
            ("dm_p_mbb", repr(diff.get("dm_p_mbb"))),
            ("n_months", diff.get("n_months", "—")),
            ("controls", ", ".join(sorted(controls.keys())) or "—"),
            ("ic_state", json.dumps(_ic_summary("ic_state.parquet"), sort_keys=True)),
            ("ic_base", json.dumps(_ic_summary("ic_base.parquet"), sort_keys=True)),
            ("preregistration", prereg),
        )
    )
    return (
        '<!DOCTYPE html>\n<html lang="zh-CN"><head><meta charset="utf-8">'
        f"<title>Aionis — {phase} meta dossier</title>\n"
        "<style>body{font-family:system-ui,sans-serif;max-width:860px;margin:2rem auto;"
        "padding:0 1rem;color:#1f2328}table{border-collapse:collapse}th,td{border:1px solid #ccc;"
        "padding:4px 10px;text-align:left}th{background:#f6f8fa}</style></head>\n<body>\n"
        f"<h1>{_esc(phase)} — research dossier (meta)</h1>\n"
        '<p class="note">meta-only 卡：承载该相主张的机读数值与账本对账；'
        "完整 [S#] 引用闭合的溯源深度在头条 Track C 档案中。"
        "Meta-only card: claim numbers + ledger reconciliation; the full [S#] "
        "closed provenance chain covers the headline Track C claim.</p>\n"
        f"<table>{rows}</table>\n"
        "<p>byte-stable artifact — regenerate with "
        "<code>scripts/export_research_dossier.py</code> (phase meta export).</p>\n"
        "</body></html>\n"
    )


def export_phase_dossier_meta(
    results_dir=None,
    ledger_path=None,
    out_dir=None,
):
    """Write research-dossier-<phase>-v1.html for B / D / E1 (meta-only).

    Returns the written-artifact summary list. Raises on ledger/results-dir
    reconciliation failures (export-time gate). Skips honestly (no-op) when
    the frozen runs/results tree is absent — a fresh checkout has no research
    artifacts; the tracked HTMLs retain their last-committed values.
    """
    results_dir = ROOT / "runs/results" if results_dir is None else Path(results_dir)
    sentinel = results_dir / (
        "17245a75d2d4cd17c68f36a9d0f4b4f7f3baf1db31b33b87be79e6e4a11400da"
    )
    if not sentinel.exists():
        print(
            "[export-research-dossier] SKIP phase dossiers: frozen runs/results "
            "tree absent (fresh checkout; tracked HTMLs retain last-committed values)"
        )
        return []
    ledger_path = ROOT / "runs/ledger.jsonl" if ledger_path is None else Path(ledger_path)
    out_dir = ROOT / "reports/evidence" if out_dir is None else Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ledger_lines = ledger_path.read_text(encoding="utf-8").splitlines()

    written = []
    for spec in _META_PHASES:
        html_out = _phase_dossier_html(
            spec["phase"], spec["ledger_row"], spec["prereg"],
            results_dir, ledger_lines,
        )
        fp = out_dir / f"research-dossier-{spec['phase'].lower()}-v1.html"
        archive_if_changed(fp, html_out.encode("utf-8"))
        fp.write_text(html_out, encoding="utf-8", newline="\n")
        written.append({
            # canonical repo location (out_dir is an injectable test seam)
            "id": f"research-dossier-{spec['phase'].lower()}-v1",
            "path": f"reports/evidence/{fp.name}",
            "bytes": fp.stat().st_size,
            "sha256": hashlib.sha256(fp.read_bytes()).hexdigest(),
        })
        print(f"wrote {fp} ({fp.stat().st_size} bytes) sha256={written[-1]['sha256']}")
    return written
