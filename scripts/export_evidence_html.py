"""Export the standalone self-contained evidence HTML artifact (TASK-DISP-G2).

Reads the committed display panels (web/src/data/aionis/{metrics,ic_monthly,
evidence,headline_provenance}.json) and renders reports/evidence/atlas-claim-v1.html:
a single-file, zero-JS, zero-external-resource research evidence page (inline
CSS + inline SVG + data table, system font stack only — no font requests).

Byte-stable by construction: no wall-clock reads anywhere, every as-of stamp
comes from a panel field, all sort orders are pinned in code, numeric rendering
is deterministic, and the file is written with LF newlines. Missing panels
degrade honestly (an explicit "panel unavailable" notice; nothing fabricated).

Display/derivation-lane script: read-only on the panels, writes ONLY under
reports/evidence/, never touches runs/ or any frozen surface.

Usage::

    uv run python scripts/export_evidence_html.py
"""
from __future__ import annotations

import hashlib
import html
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PANEL_DIR = ROOT / "web/src/data/aionis"
OUT = ROOT / "reports/evidence/atlas-claim-v1.html"

ARTIFACT_ID = "atlas-claim-v1"
GENERATOR_VERSION = "1.0.0"

PANEL_FILES = {
    "metrics": "metrics.json",
    "ic_monthly": "ic_monthly.json",
    "evidence": "evidence.json",
    "provenance": "headline_provenance.json",
}

# Hardcoded palette — the self-contained artifact must NOT depend on site CSS
# variables. Correspondence with web/src/app/globals.css light-theme tokens:
#   paper #ffffff  = --card (#ffffff)
#   ink   #171717  = --ink / --card-foreground (#171717)
#   blue  #0059ec  = --blue-text (#0059ec) — the single accent color
#   tint  #e6f0ff  = --blue-tint (#e6f0ff)
#   line  #e4e4e7  ~= --line (#0000001f composited on white)
#   muted #55555c  ~= neutral-600 secondary text
#   gray  #44474f  = negative-direction marks. Direction is encoded by
#                    lightness + blue-vs-gray (colorblind-safe; never red/green).
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
main { max-width: 880px; margin: 0 auto; padding: 26px 20px 64px; }
section { background: #ffffff; border: 1px solid #e4e4e7; border-radius: 10px;
  padding: 20px 22px; margin: 18px 0; }
h1 { font-size: 1.4rem; margin: 0 0 8px; }
h2 { font-size: 1.02rem; margin: 0 0 12px; }
p { margin: 8px 0; }
.sub { color: #55555c; font-size: 0.88rem; }
.accent { color: #0059ec; }
.badge { display: inline-block; border: 1px solid #0059ec; color: #0059ec;
  border-radius: 999px; padding: 1px 10px; font-size: 0.78rem;
  letter-spacing: 0.04em; vertical-align: 2px; }
dl.card { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 10px 18px; margin: 0; }
dl.card div { border-top: 1px solid #ececf0; padding-top: 8px; }
dt { font-size: 0.76rem; color: #55555c; letter-spacing: 0.02em; }
dd { margin: 2px 0 0; font-size: 1.1rem; font-variant-numeric: tabular-nums; }
dl.kv { margin: 0; font-size: 0.84rem; }
dl.kv div { display: flex; gap: 12px; border-bottom: 1px solid #ececf0;
  padding: 4px 0; }
dl.kv dt { flex: 0 0 260px; color: #55555c; }
dl.kv dd { margin: 0; font-size: 0.84rem; font-variant-numeric: tabular-nums; }
.tbl { max-height: 430px; overflow: auto; border: 1px solid #ececf0;
  border-radius: 6px; }
table { border-collapse: collapse; width: 100%; font-size: 0.8rem;
  font-variant-numeric: tabular-nums; }
th, td { border-bottom: 1px solid #ececf0; padding: 4px 10px; text-align: right; }
th:first-child, td:first-child { text-align: left; }
th { color: #55555c; font-weight: 600; background: #fafafa; position: sticky;
  top: 0; }
svg { display: block; width: 100%; height: auto; }
.note { font-size: 0.8rem; color: #55555c; }
.na { font-size: 0.86rem; color: #55555c; background: #fafafa;
  border: 1px dashed #c9c9cf; border-radius: 6px; padding: 8px 12px; }
ul.methods { margin: 0; padding-left: 1.25em; }
ul.methods li { margin: 7px 0; font-size: 0.88rem; }
code { background: #f2f2f4; border-radius: 4px; padding: 1px 5px;
  font-family: ui-monospace, Consolas, "Courier New", monospace;
  font-size: 0.86em; }
footer { color: #55555c; font-size: 0.78rem; padding: 0 4px; }
"""


def load_panel(panel_dir: Path | None = None) -> dict:
    """Read the four display panels; a missing file degrades to None (honest)."""
    base = PANEL_DIR if panel_dir is None else Path(panel_dir)
    panel: dict = {}
    for key, fname in PANEL_FILES.items():
        fp = base / fname
        panel[key] = json.loads(fp.read_text(encoding="utf-8")) if fp.exists() else None
    return panel


def _esc(v: object) -> str:
    """HTML-escape any panel-derived value (deterministic, quote-safe)."""
    return html.escape(str(v), quote=True)


def plain(x: object) -> str:
    """Minimal deterministic numeric literal, verbatim-equal to the panel value.

    ints render without a decimal point; floats render via repr (CPython's
    shortest round-trip literal), so the artifact string is exactly the value
    embedded in the committed panel JSON.
    """
    if isinstance(x, bool):
        return str(x)
    if isinstance(x, int):
        return str(x)
    f = float(x)
    if f.is_integer() and abs(f) < 1e16:
        return str(int(f))
    return repr(f)


def f4(x: object) -> str:
    """Fixed 4-decimal rendering for long float tails (table cells, SVG labels)."""
    return f"{float(x):.4f}"


def _px(v: float) -> str:
    s = f"{v:.2f}"
    return "0.00" if s == "-0.00" else s


def _na(label: str) -> str:
    return (
        f'<p class="na">面板缺失 / panel unavailable:{_esc(label)} — '
        "本快照未提供该面板,如实降级呈现,不伪造数据。</p>"
    )


def _head() -> list[str]:
    return [
        "<!DOCTYPE html>",
        '<html lang="zh-CN">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f'<meta name="generator" content="aionis export_evidence_html.py '
        f'{GENERATOR_VERSION}">',
        f"<title>Aionis 研究证据工件 · Atlas Claim Evidence ({ARTIFACT_ID})</title>",
        "<!--",
        f"  Aionis standalone evidence artifact — {ARTIFACT_ID}",
        "  byte-stable artifact — regenerate with: "
        "`uv run python scripts/export_evidence_html.py`",
        f"  generator version: {GENERATOR_VERSION}",
        "  self-contained: zero JS, zero external resources, zero font requests",
        "  (system font stack only). All numbers are verbatim panel values from",
        "  web/src/data/aionis/*.json; as-of stamps come from panel fields only.",
        "-->",
        "<style>",
        _CSS.rstrip(),
        "</style>",
        "</head>",
    ]


def _claim_section() -> list[str]:
    return [
        "<main>",
        "<section>",
        "<h1>Aionis 研究证据工件 · Atlas Claim Evidence "
        f'<span class="badge">{ARTIFACT_ID}</span></h1>',
        '<p class="sub">One pre-registered two-tailed claim per phase — '
        "cross-sectional monthly rank-IC on S&amp;P 500 point-in-time "
        "constituents. 每相单一预注册两尾主张:横截面月度 rank-IC 差分。</p>",
        "<p>主张(预注册、两尾):<em>处理信号(treatment)相对纯基本面基线的月度 "
        "cross-sectional rank-IC <span class=\"accent\">差分</span>与零无差异"
        "</em>。本页是该主张一次确认性测量的自包含呈现:全部数字逐字取自已提交的"
        "显示面板(web/src/data/aionis/*.json)。NULL 判定 + 窄置信区间 = 有信息量"
        "的结论(纪律的胜利),不是失败。本工件只呈现测量与设计,不构成投资建议。</p>",
        "</section>",
    ]


def _headline_section(metrics: object) -> list[str]:
    lines = ["<section>", "<h2>2 · 头条读数 / Headline reading</h2>"]
    if not isinstance(metrics, dict):
        lines.append(_na("metrics.json(头条读数卡)"))
        lines.append("</section>")
        return lines
    verdict = _esc(metrics["verdict"])
    rows = [
        ("combined_ic · 月度 rank-IC 差分", plain(metrics["combined_ic"])),
        ("95% CI(HAC)", f"[{plain(metrics['ci_lo'])}, {plain(metrics['ci_hi'])}]"),
        ("p(HAC)", plain(metrics["p"])),
        ("n_months · 样本外月数", plain(metrics["n_months"])),
        ("verdict · 预注册两尾判定", f'<span class="badge">{verdict}</span>'),
        ("SESOI · 实际显著域", f"±{plain(metrics['sesoi'])}"),
        ("config_sig_short · 冻结配置签名", _esc(metrics["config_sig_short"])),
        ("ledger_row · 账本行", plain(metrics["ledger_row"])),
    ]
    cells = "".join(f"<div><dt>{k}</dt><dd>{v}</dd></div>" for k, v in rows)
    lines.append(f'<dl class="card">{cells}</dl>')
    lines.append(
        '<p class="note">以上读数全部取自 metrics.json 面板实值(数字逐字嵌入,'
        "不经过任何重算或四舍五入);verdict 按预注册两尾判定规则给出。"
        f'面板 snapshot_ts:{_esc(metrics.get("snapshot_ts"))}。</p>'
    )
    lines.append("</section>")
    return lines


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
    skipped = 0
    if isinstance(evidence, list):
        ordered = sorted(
            evidence, key=lambda r: int(r.get("n", 0)) if isinstance(r, dict) else 0
        )
        for e in ordered:
            if not isinstance(e, dict):
                continue
            if e.get("ci_lo") is None or e.get("ci_hi") is None:
                skipped += 1
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


def _forest_section(metrics: object, evidence: object) -> list[str]:
    lines = [
        "<section>",
        "<h2>3 · 森林图 / Forest — 95% CI vs SESOI 带 vs 零线</h2>",
    ]
    m = metrics if isinstance(metrics, dict) else None
    svg = _forest_svg(m, evidence)
    if svg is None:
        lines.append(_na("metrics.json 与 evidence.json(森林图)"))
    else:
        lines.append(svg)
        if isinstance(evidence, list):
            no_ci = [
                e for e in evidence
                if isinstance(e, dict)
                and (e.get("ci_lo") is None or e.get("ci_hi") is None)
            ]
            if no_ci:
                ns = ", ".join(f"#{int(e.get('n', 0))}" for e in no_ci)
                lines.append(
                    f'<p class="note">估计 {ns} 在 evidence 面板中无 CI 入账,'
                    "如实不入图(点估计见 evidence 面板)。</p>"
                )
    lines.append("</section>")
    return lines


def _bars_svg(ic_rows: object, sesoi: float | None) -> str | None:
    if not isinstance(ic_rows, list):
        return None
    rows = sorted(
        (
            r for r in ic_rows
            if isinstance(r, dict) and isinstance(r.get("combined"), (int, float))
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


def _bars_section(ic_rows: object, sesoi: float | None) -> list[str]:
    lines = [
        "<section>",
        "<h2>4 · 逐月 IC 序列 / Monthly combined IC, inline SVG</h2>",
    ]
    svg = _bars_svg(ic_rows, sesoi)
    if svg is None:
        lines.append(_na("ic_monthly.json(逐月 IC 序列图)"))
    else:
        lines.append(svg)
    lines.append("</section>")
    return lines


def _table_section(ic_rows: object) -> list[str]:
    lines = [
        "<section>",
        "<h2>5 · 逐月 IC 数据表(无 JS 回退)/ Monthly IC table</h2>",
    ]
    if not isinstance(ic_rows, list) or not ic_rows:
        lines.append(_na("ic_monthly.json(逐月 IC 表)"))
        lines.append("</section>")
        return lines
    ordered = sorted(
        ic_rows, key=lambda r: str(r.get("month", "")) if isinstance(r, dict) else ""
    )
    body: list[str] = []
    shown = 0
    for r in ordered:
        if not isinstance(r, dict):
            continue
        shown += 1
        cells = []
        for key in ("month", "us", "cn", "combined"):
            v = r.get(key)
            if isinstance(v, str):
                cells.append(f"<td>{_esc(v)}</td>")
            elif isinstance(v, (int, float)) and not isinstance(v, bool):
                cells.append(f"<td>{f4(v)}</td>")
            else:
                cells.append("<td>—</td>")
        body.append("<tr>" + "".join(cells) + "</tr>")
    thead = (
        "<tr><th>month(月)</th><th>us</th><th>cn</th><th>combined</th></tr>"
    )
    lines.append(f'<div class="tbl"><table><thead>{thead}</thead>'
                 f'<tbody>{"".join(body)}</tbody></table></div>')
    lines.append(f'<p class="note">表行数:{shown}(ic_monthly 面板实有记录;null '
                 "以 — 如实呈现)。若与 metrics.json 的 n_months 不同,系两面板各自"
                 "如实取值,口径以 runs 账本与预注册文档为准。</p>")
    lines.append("</section>")
    return lines


def _methods_section(metrics: object, prov: object) -> list[str]:
    prelude = (
        "<li><strong>预注册 + commit-then-reveal:</strong>冻结配置的 sha256 在任何"
        "样本外观测前先入账(config_committed),同一签名重跑位级一致;结论不可被"
        "事后重跑拯救。"
    )
    if isinstance(prov, dict):
        fr = prov.get("freeze") if isinstance(prov.get("freeze"), dict) else {}
        ct = prov.get("contract") if isinstance(prov.get("contract"), dict) else {}
        prelude += (
            f"本测量:freeze row {plain(fr.get('ledger_row'))} @ "
            f"{_esc(fr.get('ts'))} → result row {plain(prov.get('ledger_row'))} @ "
            f"{_esc(prov.get('result_ts'))}(freeze_before_result="
            f"{plain(bool(ct.get('freeze_before_result')))})。"
        )
    else:
        prelude += "headline_provenance 面板缺失,冻结链详情不可用。"
    lines = [
        "<section>",
        "<h2>6 · 方法学与边界 / Methodology &amp; boundaries</h2>",
        '<ul class="methods">',
        prelude + "</li>",
    ]
    m = metrics if isinstance(metrics, dict) else None
    lines.extend([
        "<li><strong>无泄漏数据契约:</strong>PIT 数据(fundamentals 按 filed 日期、"
        "宏经 ALFRED vintage、宇宙按 PIT 成分);PurgedGroupKFold + embargo "
        "(group=month, embargo=21 sessions),标签无泄漏。</li>",
        "<li><strong>确定性(H6):</strong>" + (
            f"{_esc(m['h6'])} — n_jobs=1、种子全固定、版本锁定;"
            if m is not None else ""
        ) + "IC 序列与原始分数跨重跑位级一致。</li>",
        "<li><strong>等价性检验(如实呈现):</strong>" + (
            f"JT look1 = {_esc(m['jt_look1'])}(metrics.json 实值,不修饰)。"
            if m is not None else "metrics 面板缺失,等价性读数不可用。"
        ) + "</li>",
        "<li><strong>E3 forward-live(P0-1):</strong>forward-live 已实现,待业主"
        "契约冻结(按仓库现状如实表述;本页不宣称已完成的活体验证)。</li>",
        "<li><strong>NULL 判定立场:</strong>按预注册判定规则如实呈现——零结果 + "
        "窄 CI 是预期内且有信息量的结果;本工件仅呈现测量与设计,不给投资建议,"
        "不构成任何收益承诺。</li>",
        "</ul>",
        "</section>",
    ])
    return lines


def _provenance_section(metrics: object, prov: object) -> list[str]:
    lines = [
        "<section>",
        "<h2>7 · 溯源 / Provenance</h2>",
    ]
    if isinstance(metrics, dict):
        lines.append(f'<p class="note">metrics 面板 snapshot_ts:'
                     f'{_esc(metrics.get("snapshot_ts"))}。</p>')
    else:
        lines.append(_na("metrics.json(snapshot_ts)"))
    if isinstance(prov, dict):
        fr = prov.get("freeze") if isinstance(prov.get("freeze"), dict) else {}
        ct = prov.get("contract") if isinstance(prov.get("contract"), dict) else {}
        hl = prov.get("headline") if isinstance(prov.get("headline"), dict) else {}
        rows = [
            ("headline_provenance.status / phase",
             f"{_esc(prov.get('status'))} / {_esc(prov.get('phase'))}"),
            ("result(ledger_row / ts / event)",
             f"{plain(prov.get('ledger_row'))} / {_esc(prov.get('result_ts'))} / "
             f"{_esc(prov.get('result_event'))}"),
            ("freeze(config_committed)",
             f"row {plain(fr.get('ledger_row'))} / {_esc(fr.get('ts'))} / "
             f"{_esc(fr.get('event'))}"),
            ("config_sig_short / source",
             f"{_esc(prov.get('config_sig_short'))} / "
             f"{_esc(prov.get('config_sig_source'))}"),
            ("contract", f"freeze_before_result="
             f"{plain(bool(ct.get('freeze_before_result')))} — "
             f"{_esc(ct.get('note'))}"),
            ("headline(全精度实值)",
             f"combined_ic={plain(hl.get('combined_ic'))}, "
             f"p_hac={plain(hl.get('p_hac'))}, "
             f"ci=[{plain(hl.get('ci_lo'))}, {plain(hl.get('ci_hi'))}], "
             f"n_months={plain(hl.get('n_months'))}"),
            ("provenance 面板 snapshot_ts", _esc(prov.get("snapshot_ts"))),
        ]
        cells = "".join(f"<div><dt>{k}</dt><dd>{v}</dd></div>" for k, v in rows)
        lines.append(f'<dl class="kv">{cells}</dl>')
    else:
        lines.append(_na("headline_provenance.json"))
    lines.extend([
        '<p class="note">生成器:export_evidence_html.py '
        f'v{GENERATOR_VERSION};artifact id:{ARTIFACT_ID}。byte-stable artifact — '
        "regenerate with <code>uv run python scripts/export_evidence_html.py</code>"
        "(确定性:无运行时时钟,as_of 全部取自面板字段,排序写死,LF 换行)。</p>",
        '<p class="note">配色说明:本工件不依赖站点 CSS 变量,使用硬编码 hex 并与'
        " web/src/app/globals.css 浅色 token 对应——#ffffff=--card、#171717=--ink、"
        "#0059ec=--blue-text(单蓝强调)、#e6f0ff=--blue-tint、#e4e4e7≈--line;"
        "方向编码用蓝/灰明度差(色盲安全,非红绿对)。</p>",
        "</section>",
        "</main>",
    ])
    return lines


def render_html(panel: dict) -> str:
    """Pure renderer: panel dict in, byte-stable HTML string out."""
    metrics = panel.get("metrics")
    ic_rows = panel.get("ic_monthly")
    evidence = panel.get("evidence")
    prov = panel.get("provenance")
    m = metrics if isinstance(metrics, dict) else None
    sesoi = float(m["sesoi"]) if m is not None else None

    parts = _head()
    parts.append("<body>")
    parts.extend(_claim_section())
    parts.extend(_headline_section(metrics))
    parts.extend(_forest_section(metrics, evidence))
    parts.extend(_bars_section(ic_rows, sesoi))
    parts.extend(_table_section(ic_rows))
    parts.extend(_methods_section(metrics, prov))
    parts.extend(_provenance_section(metrics, prov))
    parts.extend([
        "<footer>",
        "Aionis — falsifiable, anti-leakage research harness. 自包含证据工件:"
        "零 JS、零外部资源、零字体请求;浏览器直开即读。</footer>",
        "</body>",
        "</html>",
    ])
    return "\n".join(parts) + "\n"


def main() -> int:
    panel = load_panel()
    out = render_html(panel)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="\n") as f:
        f.write(out)
    digest = hashlib.sha256(OUT.read_bytes()).hexdigest()
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes) sha256={digest}")
    return 0


# ---------------------------------------------------------------------------
# R2-full S1 — evidence matrix manifest (tasks/active/TASK-R2-full-artifact-matrix.md)
#
# Machine-readable matrix of all five claims + self-contained artifact digests.
# Every value is read from frozen/committed files (differential.json,
# ledger.jsonl, metrics.json) at export time — zero hand-typed numbers, zero
# wall clock, byte-stable double-run (contract-tested).

MATRIX_ID = "evidence-matrix-v1"
MATRIX_PATH = ROOT / "reports/evidence/evidence-matrix-v1.json"
RESULTS_DIR = ROOT / "runs/results"
LEDGER_PATH = ROOT / "runs/ledger.jsonl"

# Frozen claim registry. Provenance: docs/RESULTS.md §2 + §6 ledger index —
# sigs are the confirmatory results dirs, ledger_row the 1-based ledger line
# whose config_sig must equal that sig (export-time reconciliation gate).
_CLAIMS: tuple[dict, ...] = (
    {
        "phase": "B", "ledger_row": 28,
        "sig": "17245a75d2d4cd17c68f36a9d0f4b4f7f3baf1db31b33b87be79e6e4a11400da",
    },
    {
        "phase": "C", "ledger_row": 30,
        "sig": "a7fdb48f5942fae146b151143807653fd66c4c5f1601dc7cf9d04a796c1fada1",
    },
    {
        "phase": "D", "ledger_row": 34,
        "sig": "d31580630ff35326557dda9f50832c7af3625dd6507e47e252ea01800372a12c",
    },
    {
        "phase": "E1", "ledger_row": 37,
        "sig": "ef321e9ee808804601e012818fa95522d2dc5f0fe8c53771d7f1b412c25ed49f",
    },
)
_MATRIX_ARTIFACTS = ("atlas-claim-v1.html", "research-dossier-v1.html")


def export_evidence_matrix_manifest(
    results_dir: Path | None = None,
    ledger_path: Path | None = None,
    metrics_path: Path | None = None,
    artifacts_dir: Path | None = None,
    out_path: Path | None = None,
) -> dict:
    """Build and write the five-claim evidence matrix manifest.

    Returns the manifest dict. Raises on any ledger/config-sig mismatch (the
    export-time gate — same spirit as the atlas byte-stability contract).
    """
    results_dir = RESULTS_DIR if results_dir is None else Path(results_dir)
    ledger_path = LEDGER_PATH if ledger_path is None else Path(ledger_path)
    metrics_path = PANEL_DIR / "metrics.json" if metrics_path is None else Path(metrics_path)
    artifacts_dir = ROOT / "reports/evidence" if artifacts_dir is None else Path(artifacts_dir)
    out_path = MATRIX_PATH if out_path is None else Path(out_path)

    ledger_lines = ledger_path.read_text(encoding="utf-8").splitlines()

    def _ledger_sig(row: int) -> str:
        rec = json.loads(ledger_lines[row - 1])
        sig = rec.get("config_sig")
        if not sig:
            raise ValueError(f"ledger line {row} has no config_sig")
        return str(sig)

    claims: dict[str, dict] = {}
    for c in _CLAIMS:
        sig = _ledger_sig(c["ledger_row"])
        if sig != c["sig"]:
            raise ValueError(
                f"ledger line {c['ledger_row']} config_sig {sig[:12]} != "
                f"results dir {c['sig'][:12]}"
            )
        diff = json.loads(
            (results_dir / c["sig"] / "differential.json").read_text(encoding="utf-8")
        )
        claims[c["phase"]] = {
            "kind": "phase",
            "ledger_row": c["ledger_row"],
            "results_sig": c["sig"],
            "mean_diff": diff["mean_diff"],
            "ci_lo": diff["ci_lo"],
            "ci_hi": diff["ci_hi"],
            "dm_p_mbb": diff["dm_p_mbb"],
            "n_months": diff["n_months"],
            # docs/RESULTS.md §2: all four phase headlines are zero-LLM.
            "zero_llm": True,
        }

    # Track C: no local results dir (2026-08-30 round note) — headline values
    # from the committed metrics panel, config_sig from ledger line 49 itself.
    tc = json.loads(metrics_path.read_text(encoding="utf-8"))
    if int(tc.get("ledger_row", -1)) != 49:
        raise ValueError("metrics.json ledger_row != 49")
    claims["track_c"] = {
        "kind": "confirmatory_oos",
        "ledger_row": 49,
        "config_sig": _ledger_sig(49),
        "combined_ic": tc["combined_ic"],
        "p_hac": tc["p"],
        "ci_lo": tc["ci_lo"],
        "ci_hi": tc["ci_hi"],
        "n_months": tc["n_months"],
        "verdict": tc["verdict"],
        "jt_look1": tc["jt_look1"],
        "h6": tc["h6"],
        "sesoi": tc["sesoi"],
    }

    artifacts = []
    for name in _MATRIX_ARTIFACTS:
        fp = artifacts_dir / name
        raw = fp.read_bytes()
        artifacts.append({
            "id": name.removesuffix(".html"),
            "path": f"reports/evidence/{name}",
            "sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw),
        })

    manifest = {
        "id": MATRIX_ID,
        "generator": "scripts/export_evidence_html.py",
        "claims": claims,
        "artifacts": artifacts,
    }
    payload = json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(payload, encoding="utf-8")
    print(
        f"[evidence-matrix] {len(claims)} claims / {len(artifacts)} artifacts -> {out_path}"
    )
    return manifest


if __name__ == "__main__":
    raise SystemExit(main())
