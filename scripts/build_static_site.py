"""构建 Aionis 静态研究站点（Tailwind CSS · 暗色金融终端风 · 中文）→ site/index.html。

设计（业主 2026-08-02 反馈：参考 参照站 的 UI，勿手搓 CSS）：
- 复用 **Tailwind CSS**（CDN，成熟框架，参考站同款）——不手写 CSS。
- 暗色金融终端风：顶部导航 + KPI 数据卡 + 卡片网格 + 数据表 + 高密度。
- 全中文；内容驱动（真实 Track B 差分结果 + 七主题 + 反泄漏 + 边界）。
- 图表 plotly（暗色模板，数据驱动；统计量由 rank_ic_summary 预计算嵌入）。
- 数据源：site/track_b_data.json（a-run --mode differential 生成；缺失则无 IC 序列图）。

Run:  uv run python scripts/build_static_site.py
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
SITE_DIR = PROJECT_ROOT / "site"

# 真实 headline（Track B 首个差分，config #41/#42，chronological walk-forward 2021-01..2026-06）
TREATMENT = {"name": "treatment", "sub": "七主题 23 特征 (#41)", "mean": 0.005511,
             "ci": (-0.021441, 0.032463), "p": 0.6886}
PRICE_ONLY = {"name": "price-only", "sub": "10 价格特征 (#42)", "mean": -0.002062,
              "ci": (-0.031623, 0.027500), "p": 0.8913}
DIFFERENTIAL = {"name": "差分", "sub": "treatment − price-only (§1 headline)", "mean": 0.007572,
                "ci": (-0.004492, 0.019636), "p": 0.2186}
SESOI = 0.010

# Track C 首条 confirmatory OOS climax（ledger #49, 2026-08-05）。诚实 framing：
# null 点估计 + look-1 欠功率（power-floor 披露），NOT "等价已宣告"。
# 数字源自 ledger #49（与 archive/docs/methods-and-results-draft.md（已归档）§5 / docs/RESULTS.md §0 一致）。
TRACK_C_CLIMAX = {
    "combined_ic": -0.0088,
    "p_hac": 0.484,
    "ci": (-0.034, 0.016),
    "n_months": 71,
    "rci": (-0.051, 0.027),
    "jt_verdict": "NOT_EQUIVALENT",
    "h6": "PASS",
}

SEVEN_THEMES = [
    ("① 行情/价格", "Tiingo + Alpaca", "已覆盖", "退市价缺失（保守上界）", "ok"),
    ("② 宏观", "ALFRED vintage", "已覆盖", "macro 会修订→vintage", "ok"),
    ("③ 基本面", "EDGAR filed-date", "已覆盖（13 特征）", "filed 非 period-end", "ok"),
    ("④ 新闻情绪", "E3 闭集 + FinGPT", "延后 S3 ablation", "LLM 记忆泄漏；不作主 alpha", "warn"),
    ("⑤ 风险", "alphalens/pyfolio/empyrical", "评估层待挂", "tearsheet 覆盖", "todo"),
    ("⑥ 回测净成本", "FINSABER (KDD2026)", "待挂接", "next-open/slippage/liquidity", "todo"),
    ("⑦ 市场结构", "FF5 + Amihud", "已实现 ff5_residual", "FF 无 vintage（声明）", "ok"),
]

ANTI_LEAKAGE = [
    ("config_committed 先于 result", "ledger #40/#41/#42 在任何 OOS 观察前入账"),
    ("PIT 数据", "EDGAR filed-date / ALFRED vintage / constituents_on（非今日快照）"),
    ("chronological walk-forward", "expanding min_train=60 / embargo=21 / assert train<test（非 CV-proxy）"),
    ("H6 确定性", "n_jobs=1 / 全 seed=0 / version-pinned / bit-identical 重跑"),
    ("两尾 · 预注册 · null-favored", "每条 claim 预注册；null-with-tight-CI 即达精度目标"),
]

STATUS_STYLE = {"ok": ("已覆盖", "emerald"), "warn": ("延后", "amber"), "todo": ("待挂", "slate")}


def _load_ic_series(site_dir: Path) -> dict | None:
    path = site_dir / "track_b_data.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _load_mount_metrics(site_dir: Path) -> dict | None:
    path = site_dir / "mount_metrics.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _fmt_pct(x):
    return f"{x * 100:.1f}%" if isinstance(x, (int, float)) else "—"


def _fmt_num(x, nd=2):
    return f"{x:.{nd}f}" if isinstance(x, (int, float)) else "—"


def _metrics_section_html(mount: dict | None) -> str:
    if not mount:
        return '<p class="text-slate-500 text-sm">风险指标待 site/mount_metrics.json'
        '（运行 <code>track_b_mounts_run.py</code>）。</p>'
    try:
        tm = mount["treatment"]["tearsheet"]["model"]
        pm = mount["price_only"]["tearsheet"]["model"]
        ew = mount["treatment"]["tearsheet"]["ew"]
    except (KeyError, TypeError):
        return '<p class="text-slate-500 text-sm">mount_metrics 结构异常。</p>'
    rows = [
        ("年化收益", _fmt_pct(tm["annual_return"]), _fmt_pct(pm["annual_return"]),
         _fmt_pct(ew["annual_return"])),
        ("年化波动", _fmt_pct(tm["annual_volatility"]), _fmt_pct(pm["annual_volatility"]),
         _fmt_pct(ew["annual_volatility"])),
        ("Sharpe", _fmt_num(tm["sharpe_ratio"]), _fmt_num(pm["sharpe_ratio"]),
         _fmt_num(ew["sharpe_ratio"])),
        ("Sortino", _fmt_num(tm["sortino_ratio"]), _fmt_num(pm["sortino_ratio"]),
         _fmt_num(ew["sortino_ratio"])),
        ("最大回撤", _fmt_pct(tm["max_drawdown"]), _fmt_pct(pm["max_drawdown"]),
         _fmt_pct(ew["max_drawdown"])),
        ("Calmar", _fmt_num(tm["calmar_ratio"]), _fmt_num(pm["calmar_ratio"]),
         _fmt_num(ew["calmar_ratio"])),
    ]
    body = "".join(
        f"<tr class='border-b border-slate-800'>"
        f"<td class='py-2 px-3 font-medium text-slate-100'>{label}</td>"
        f"<td class='py-2 px-3 text-blue-300'>{tm_v}</td>"
        f"<td class='py-2 px-3 text-slate-300'>{pm_v}</td>"
        f"<td class='py-2 px-3 text-slate-400'>{ew_v}</td></tr>"
        for label, tm_v, pm_v, ew_v in rows
    )
    return (
        '<div class="bg-amber-500/10 border border-amber-500/30 rounded-lg p-2 mb-3 text-xs '
        'text-amber-300">⚠️ GROSS（未扣成本）· 探索性 top-quantile 等权组合月度收益 · '
        "非净成本/非可交易策略；指标由 empyrical 计算。</div>"
        '<div class="overflow-x-auto"><table class="w-full text-sm">'
        '<thead><tr class="text-left text-slate-400 border-b border-slate-700">'
        "<th class='py-2 px-3'>指标</th><th class='py-2 px-3'>treatment(top-q)</th>"
        "<th class='py-2 px-3'>price-only(top-q)</th>"
        "<th class='py-2 px-3'>等权(universe)</th></tr></thead>"
        f"<tbody>{body}</tbody></table></div>"
    )


def _ff5_section_html(mount: dict | None) -> str:
    if not mount:
        return '<p class="text-slate-500 text-sm">FF5 待 mount_metrics.json。</p>'
    try:
        tf = mount["treatment"]["ff5"]
        pf = mount["price_only"]["ff5"]
    except (KeyError, TypeError):
        return '<p class="text-slate-500 text-sm">FF5 未取得。</p>'
    if not tf or not pf:
        note = mount.get("treatment", {}).get("ff5_note") or "FF5 数据未取得（网络）"
        return f'<p class="text-slate-500 text-sm">{note}</p>'
    betas = [("beta_mkt", "β MKT"), ("beta_smb", "β SMB"), ("beta_hml", "β HML"),
             ("beta_rmw", "β RMW"), ("beta_cma", "β CMA")]
    rows = [("α（月）", f"{tf['alpha']:.4f}", f"{pf['alpha']:.4f}")]
    rows += [(lbl, f"{tf[k]:+.2f}", f"{pf[k]:+.2f}") for k, lbl in betas]
    rows.append(("R²", f"{tf['r_squared']:.3f}", f"{pf['r_squared']:.3f}"))
    body = "".join(
        f"<tr class='border-b border-slate-800'><td class='py-2 px-3 font-medium text-slate-100'>{lbl}</td>"
        f"<td class='py-2 px-3 text-blue-300'>{tv}</td><td class='py-2 px-3 text-slate-300'>{pv}</td></tr>"
        for lbl, tv, pv in rows
    )
    return (
        '<div class="bg-amber-500/10 border border-amber-500/30 rounded-lg p-2 mb-3 text-xs text-amber-300">'
        "⚠️ GROSS · FF5 无 vintage（潜在轻微泄漏）· R² 低则因子解释力弱 · 探索性。</div>"
        '<div class="overflow-x-auto"><table class="w-full text-sm">'
        '<thead><tr class="text-left text-slate-400 border-b border-slate-700">'
        "<th class='py-2 px-3'>FF5 分解</th><th class='py-2 px-3'>treatment</th>"
        "<th class='py-2 px-3'>price-only</th></tr></thead>"
        f"<tbody>{body}</tbody></table></div>"
    )


def _kpi_tile(label: str, value: str, sub: str = "", accent: str = "slate") -> str:
    color = {"emerald": "text-emerald-400", "rose": "text-rose-400",
             "amber": "text-amber-400", "slate": "text-slate-100"}.get(accent, "text-slate-100")
    return f"""
    <div class="bg-slate-800/60 border border-slate-700 rounded-lg p-4">
      <div class="text-xs text-slate-400 mb-1">{label}</div>
      <div class="text-2xl font-bold {color}">{value}</div>
      <div class="text-xs text-slate-500 mt-1">{sub}</div>
    </div>"""


def _theme_rows() -> str:
    rows = []
    for theme, src, _status, gap, key in SEVEN_THEMES:
        label, color = STATUS_STYLE[key]
        badge = (f'<span class="px-2 py-0.5 rounded text-xs bg-{color}-500/15 '
                 f'text-{color}-400">{label}</span>')
        rows.append(
            f"<tr class='border-b border-slate-800'>"
            f"<td class='py-2 px-3 font-medium text-slate-100'>{theme}</td>"
            f"<td class='py-2 px-3 text-slate-300'>{src}</td>"
            f"<td class='py-2 px-3'>{badge}</td>"
            f"<td class='py-2 px-3 text-slate-400 text-sm'>{gap}</td></tr>"
        )
    return "".join(rows)


def _antileakage_cards() -> str:
    cards = []
    for title, desc in ANTI_LEAKAGE:
        cards.append(
            f'<div class="bg-slate-800/60 border border-slate-700 rounded-lg p-3">'
            f'<div class="flex items-start gap-2">'
            f'<span class="text-emerald-400 mt-0.5">✓</span>'
            f'<div><div class="font-semibold text-slate-100 text-sm">{title}</div>'
            f'<div class="text-xs text-slate-400 mt-0.5">{desc}</div></div></div></div>'
        )
    return "".join(cards)


def _trackc_section_html() -> str:
    """Track C 首条 confirmatory OOS climax section（ledger #49, 2026-08-05）。

    诚实 framing：null 点估计 + look-1 欠功率（power-floor 披露），NOT "等价已宣告"。
    纯新增 section（Track B sections 不动）；复用 _kpi_tile + section-card 模式。
    确定性：仅用模块常量，无 random/time → byte-identical 重建。
    """
    c = TRACK_C_CLIMAX
    ic_str = f"{c['combined_ic']:+.4f}"
    ci_lo, ci_hi = f"{c['ci'][0]:+.3f}", f"{c['ci'][1]:+.3f}"
    rci_lo, rci_hi = f"{c['rci'][0]:+.3f}", f"{c['rci'][1]:+.3f}"
    return f"""
  <!-- Track C 首条 confirmatory（climax）-->
  <section id="track-c" class="mb-6 bg-slate-800/40 border border-emerald-700/40 rounded-xl p-5">
    <h2 class="text-lg font-bold text-slate-50 mb-1">🏆 首条 confirmatory OOS — Track C 双区域 climax（ledger #49）</h2>
    <p class="text-slate-400 text-xs mb-3">2026-08-05 · US (S&amp;P 500) + CN (CSI 300) 联合 chronological walk-forward · 41 特征 · regime 条件化（multiplicity 预算 1）</p>
    <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-3">
      {_kpi_tile("combined rank-IC", ic_str, "null · p_hac=0.484", "amber")}
      {_kpi_tile("J-T look-1", c['jt_verdict'], "RCI 99.44% · 欠功率（非效应）", "amber")}
      {_kpi_tile("H6 双跑", c['h6'], "真实数据 bit-identical", "emerald")}
      {_kpi_tile("IC 月数", str(c['n_months']), "68 折 · 2016-01..2026-08", "slate")}
    </div>
    <div class="bg-slate-900/50 border border-slate-700 rounded-lg p-3 mb-3 overflow-x-auto">
      <table class="w-full text-sm">
        <thead><tr class="text-left text-slate-400 border-b border-slate-700">
          <th class="py-2 px-3">量</th><th class="py-2 px-3">值</th><th class="py-2 px-3">判读</th>
        </tr></thead>
        <tbody>
          <tr class="border-b border-slate-800"><td class="py-2 px-3 font-medium text-slate-100">combined rank-IC 均值</td><td class="py-2 px-3 text-amber-300">{ic_str}</td><td class="py-2 px-3 text-slate-300">null（95% HAC CI [{ci_lo}, {ci_hi}] 跨零；p_hac={c['p_hac']:.3f}）</td></tr>
          <tr class="border-b border-slate-800"><td class="py-2 px-3 font-medium text-slate-100">J-T look-1 (n=60, RCI 99.44%)</td><td class="py-2 px-3 text-amber-300">{c['jt_verdict']}</td><td class="py-2 px-3 text-slate-300">RCI [{rci_lo}, {rci_hi}] 宽于 ±{SESOI} SESOI = 欠功率，<strong>非</strong>效应信号</td></tr>
          <tr><td class="py-2 px-3 font-medium text-slate-100">H6 双跑 bit-identical</td><td class="py-2 px-3 text-emerald-300">{c['h6']}</td><td class="py-2 px-3 text-slate-300">真实数据确定性验证</td></tr>
        </tbody>
      </table>
    </div>
    <p class="text-sm text-slate-300">prospective power analysis：J-T 60/90/120 schedule 在 SESOI ±{SESOI} + 月频 rank-IC 噪声 σ≈0.10 下<strong class="text-amber-300">结构性欠功率</strong>（宣告等价需 ~36+ 年）。因此项目诚实、预注册的贡献 = <strong class="text-slate-100">null 点估计 + 反泄漏纪律 + power-limit 披露</strong>，<strong>非</strong>“等价已宣告”。详见 <a class="text-blue-400 hover:underline" href="https://github.com/Rethymus/Aionis/blob/main/docs/RESULTS.md">方法学与结果（RESULTS.md）</a>。</p>
  </section>"""


def build(site_dir: Path = SITE_DIR) -> Path:
    site_dir.mkdir(exist_ok=True)
    ic_data = _load_ic_series(site_dir)
    ic_data_json = json.dumps(ic_data) if ic_data else "null"
    mount = _load_mount_metrics(site_dir)
    metrics_section = _metrics_section_html(mount)
    ff5_section = _ff5_section_html(mount)
    ci_crosses_zero = DIFFERENTIAL["ci"][0] < 0 < DIFFERENTIAL["ci"][1]
    equiv = abs(DIFFERENTIAL["ci"][1]) <= SESOI and abs(DIFFERENTIAL["ci"][0]) <= SESOI

    ic_section = (
        '<div class="bg-slate-800/40 border border-slate-700 rounded-lg p-2 mt-3">'
        '<div id="ic-series-chart"></div></div>'
        if ic_data
        else '<p class="text-slate-500 text-sm mt-2">IC 月度序列图待 '
        '<code class="text-slate-400">site/track_b_data.json</code></p>'
    )

    def arm_row(a, emphasis=False):
        cls = "font-bold text-slate-50" if emphasis else "text-slate-200"
        return (
            f"<tr class='border-b border-slate-800'>"
            f"<td class='py-2 px-3 {cls}'>{a['name']}<div class='text-xs text-slate-500'>{a['sub']}</div></td>"
            f"<td class='py-2 px-3 {cls}'>{a['mean']:+.4f}</td>"
            f"<td class='py-2 px-3 text-slate-300'>({a['ci'][0]:+.4f}, {a['ci'][1]:+.4f})</td>"
            f"<td class='py-2 px-3 text-slate-300'>{a['p']:.3f}</td></tr>"
        )

    html = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Aionis · 可证伪、反泄漏的横截面选股研究</title>
<script src="https://cdn.tailwindcss.com"></script>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
</head>
<body class="bg-slate-900 text-slate-200 min-h-screen">

<!-- 顶部导航 -->
<nav class="sticky top-0 z-50 bg-slate-950/95 backdrop-blur border-b border-slate-800">
  <div class="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between">
    <div class="flex items-center gap-2">
      <span class="text-lg font-bold text-slate-50">Aionis</span>
      <span class="text-xs text-slate-500 hidden sm:inline">可证伪 · 反泄漏 · null-favored</span>
    </div>
    <div class="flex gap-3 text-sm text-slate-400">
      <a href="#finding" class="hover:text-slate-100">核心结论</a>
      <a href="#track-c" class="hover:text-slate-100">🏆 Climax</a>
      <a href="#themes" class="hover:text-slate-100">七主题</a>
      <a href="#result" class="hover:text-slate-100">差分结果</a>
      <a href="#metrics" class="hover:text-slate-100">风险指标</a>
      <a href="#ff5" class="hover:text-slate-100">FF5</a>
      <a href="#discipline" class="hover:text-slate-100">反泄漏</a>
      <a href="#boundary" class="hover:text-slate-100">边界</a>
    </div>
  </div>
</nav>

<!-- 探索性横幅 -->
<div class="bg-amber-500/10 border-b border-amber-500/30 text-amber-300 text-center text-xs py-1.5">
  ⚠️ 含探索性（Track B）+ 首条 confirmatory（Track C climax）· 非投资建议 · null 是预期成果
</div>

<main class="max-w-6xl mx-auto px-4 py-6">

  <!-- Hero -->
  <div class="mb-6">
    <h1 class="text-3xl font-bold text-slate-50">Aionis</h1>
    <p class="text-slate-400 mt-1">S&amp;P 500 月频横截面 rank-IC · 七主题选股研究 · chronological walk-forward</p>
    <div class="flex flex-wrap gap-1.5 mt-3">
      <span class="px-2.5 py-1 rounded-full text-xs bg-blue-500/15 text-blue-300">config_committed 先于 result</span>
      <span class="px-2.5 py-1 rounded-full text-xs bg-blue-500/15 text-blue-300">PIT 数据</span>
      <span class="px-2.5 py-1 rounded-full text-xs bg-blue-500/15 text-blue-300">chronological walk-forward</span>
      <span class="px-2.5 py-1 rounded-full text-xs bg-blue-500/15 text-blue-300">H6 确定性</span>
      <span class="px-2.5 py-1 rounded-full text-xs bg-blue-500/15 text-blue-300">null-favored 两尾</span>
    </div>
  </div>

  <!-- KPI 数据卡 -->
  <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 mb-6">
    {_kpi_tile("差分 mean", f"{DIFFERENTIAL['mean']:+.4f}", "treatment − price-only", "amber")}
    {_kpi_tile("差分 p (HAC)", f"{DIFFERENTIAL['p']:.3f}", "不显著" if DIFFERENTIAL['p'] > 0.05 else "显著", "emerald" if DIFFERENTIAL['p'] > 0.05 else "rose")}
    {_kpi_tile("95% CI 跨零", "是" if ci_crosses_zero else "否", f"({DIFFERENTIAL['ci'][0]:+.3f}, {DIFFERENTIAL['ci'][1]:+.3f})", "emerald" if ci_crosses_zero else "rose")}
    {_kpi_tile("SESOI 等价", "未达" if not equiv else "达", f"±{SESOI}（CI 上界 {DIFFERENTIAL['ci'][1]:+.3f}）", "amber" if not equiv else "emerald")}
    {_kpi_tile("walk-forward 折数", "66", "expanding min_train=60", "slate")}
    {_kpi_tile("universe", "566", "tickers · 2016+ PIT", "slate")}
  </div>

  <!-- 核心结论 -->
  <section id="finding" class="mb-6 bg-slate-800/40 border border-slate-700 rounded-xl p-5">
    <h2 class="text-lg font-bold text-slate-50 mb-2">📊 核心发现：Track B 首个 headline 差分</h2>
    <p class="text-slate-300">差分 95% CI 跨零、p={DIFFERENTIAL['p']:.3f} →
      <strong class="text-amber-300">treatment 未显著优于 price-only baseline</strong>（符合 null-favored 预注册）。
      但 CI 上界 {DIFFERENTIAL['ci'][1]:+.3f} &gt; SESOI ±{SESOI} → <strong class="text-amber-300">不构成严格等价</strong>
     （RCI ⊄ [−0.010,+0.010]，差分可能高达 ~0.020，需更多样本）。</p>
    <div class="mt-3 bg-slate-800/40 border border-slate-700 rounded-lg p-2"><div id="ci-chart"></div></div>
  </section>

  {_trackc_section_html()}

  <div class="grid lg:grid-cols-2 gap-4 mb-6">
    <!-- 战略复盘 -->
    <section class="bg-slate-800/40 border border-slate-700 rounded-xl p-5">
      <h2 class="text-lg font-bold text-slate-50 mb-2">🔎 战略复盘结论</h2>
      <p class="text-slate-300 text-sm">方向<strong class="text-emerald-300">没跑偏</strong>——反泄漏纪律与 null-first 是稀缺价值。
        两处失调已处理：目标叙事双轨 → 裁断为 <strong>Track B（七主题平台）</strong>；
        治理复杂度曾超研究产出 → 已切到"用治理产出研究"。</p>
    </section>
    <!-- 反泄漏纪律 -->
    <section id="discipline" class="bg-slate-800/40 border border-slate-700 rounded-xl p-5">
      <h2 class="text-lg font-bold text-slate-50 mb-3">🛡️ 反泄漏纪律</h2>
      <div class="grid gap-2">{_antileakage_cards()}</div>
    </section>
  </div>

  <!-- 七主题 -->
  <section id="themes" class="mb-6 bg-slate-800/40 border border-slate-700 rounded-xl p-5">
    <h2 class="text-lg font-bold text-slate-50 mb-3">🌐 七主题覆盖矩阵</h2>
    <div class="overflow-x-auto"><table class="w-full text-sm">
      <thead><tr class="text-left text-slate-400 border-b border-slate-700">
        <th class="py-2 px-3">主题</th><th class="py-2 px-3">数据源/轮子</th>
        <th class="py-2 px-3">覆盖</th><th class="py-2 px-3">泄漏 gotcha</th>
      </tr></thead>
      <tbody>{_theme_rows()}</tbody>
    </table></div>
  </section>

  <!-- 差分结果 -->
  <section id="result" class="mb-6 bg-slate-800/40 border border-slate-700 rounded-xl p-5">
    <h2 class="text-lg font-bold text-slate-50 mb-3">📈 首个差分结果（chronological walk-forward · 2021-01..2026-06 · 66 折）</h2>
    <table class="w-full text-sm mb-2">
      <thead><tr class="text-left text-slate-400 border-b border-slate-700">
        <th class="py-2 px-3">臂</th><th class="py-2 px-3">mean rank-IC</th>
        <th class="py-2 px-3">95% HAC CI</th><th class="py-2 px-3">p</th>
      </tr></thead>
      <tbody>{arm_row(TREATMENT)}{arm_row(PRICE_ONLY)}{arm_row(DIFFERENTIAL, emphasis=True)}</tbody>
    </table>
    {ic_section}
  </section>

  <!-- 风险指标 -->
  <section id="metrics" class="mb-6 bg-slate-800/40 border border-slate-700 rounded-xl p-5">
    <h2 class="text-lg font-bold text-slate-50 mb-3">📊 风险指标（gross · 探索性）</h2>
    {metrics_section}
  </section>

  <!-- FF5 分解 -->
  <section id="ff5" class="mb-6 bg-slate-800/40 border border-slate-700 rounded-xl p-5">
    <h2 class="text-lg font-bold text-slate-50 mb-3">🧩 FF5 残差分解（market structure · gross）</h2>
    {ff5_section}
  </section>

  <!-- 诚实边界 -->
  <section id="boundary" class="mb-6 bg-rose-500/5 border border-rose-500/30 rounded-xl p-5">
    <h2 class="text-lg font-bold text-rose-300 mb-2">⚠️ 诚实边界</h2>
    <ul class="text-sm text-slate-300 list-disc pl-5 space-y-1">
      <li>仅适用于：lambdarank / 23 vs 10 特征 / 2016+ PIT S&amp;P 500 / 幸存者偏差"可缓解不可根除"。</li>
      <li><strong>不证明</strong>："市场有效" / "七主题无效" / "可交易" / "可承载资金"。</li>
      <li><strong>可写</strong>："在此实现与样本下，未观察到 treatment 显著优于 price-only 的横截面 rank-IC。"</li>
      <li>差分 CI 上界 0.020 &gt; SESOI 0.010 → 非严格等价，需更多样本。</li>
    </ul>
  </section>

  <footer class="text-center text-slate-500 text-sm pt-4 border-t border-slate-800">
    <p>Aionis · 可证伪、反泄漏的量化选股研究 harness（非交易机器人）</p>
    <p class="mt-1">
      <a class="text-blue-400 hover:underline" href="https://github.com/Rethymus/Aionis">GitHub</a> ·
      <a class="text-blue-400 hover:underline" href="https://github.com/Rethymus/Aionis/blob/main/docs/track-b-preregistration.md">预注册</a> ·
      <a class="text-blue-400 hover:underline" href="https://github.com/Rethymus/Aionis/blob/main/docs/track-b-results.md">完整结果</a>
    </p>
  </footer>
</main>

<script>
const SESOI={SESOI};
const arms=[
  {{mean:{TREATMENT['mean']},lo:{TREATMENT['ci'][0]},hi:{TREATMENT['ci'][1]},name:{json.dumps(TREATMENT['name']+' ('+TREATMENT['sub']+')',ensure_ascii=False)}}},
  {{mean:{PRICE_ONLY['mean']},lo:{PRICE_ONLY['ci'][0]},hi:{PRICE_ONLY['ci'][1]},name:{json.dumps(PRICE_ONLY['name']+' ('+PRICE_ONLY['sub']+')',ensure_ascii=False)}}},
  {{mean:{DIFFERENTIAL['mean']},lo:{DIFFERENTIAL['ci'][0]},hi:{DIFFERENTIAL['ci'][1]},name:{json.dumps(DIFFERENTIAL['name']+' ('+DIFFERENTIAL['sub']+')',ensure_ascii=False)}}}
];
const dark={{paper_bgcolor:'rgba(0,0,0,0)',plot_bgcolor:'rgba(0,0,0,0)',
  font:{{color:'#cbd5e1'}},xaxis:{{gridcolor:'#334155',zerolinecolor:'#475569'}},
  yaxis:{{gridcolor:'#334155'}}}};
Plotly.newPlot('ci-chart',
  [{{x:arms.map(a=>a.mean),y:arms.map(a=>a.name),mode:'markers',marker:{{size:14,color:['#60a5fa','#94a3b8','#f59e0b']}},type:'scatter',name:'mean',
    error_x:{{type:'data',symmetric:false,array:arms.map(a=>a.hi-a.mean),arrayminus:arms.map(a=>a.mean-a.lo),thickness:2,color:'#cbd5e1'}}}},
   {{x:[-SESOI,SESOI],y:[arms[2].name,arms[2].name],mode:'lines',line:{{color:'#10b981',dash:'dash'}},type:'scatter',name:'SESOI ±0.010'}},
   {{x:[0,0],y:[arms[0].name,arms[2].name],mode:'lines',line:{{color:'#64748b',width:1}},showlegend:false,type:'scatter'}}],
  Object.assign({{}},dark,{{margin:{{l:280,r:30,t:10,b:40}},height:280,
    xaxis:{{title:'月频 rank-IC / 差分（95% HAC CI）',zeroline:true,gridcolor:'#334155'}},
    legend:{{x:0.01,y:-0.3,orientation:'h'}}}}),{{displayModeBar:false,responsive:true}});
const icData={ic_data_json};
if(icData){{
  const months=Object.keys(icData.differential.ic_series).sort();
  const ts=a=>months.map(m=>icData[a].ic_series[m]??null);
  const roll=arr=>{{const o=[],W=6;for(let i=0;i<arr.length;i++){{const w=arr.slice(Math.max(0,i-W+1),i+1).filter(v=>v!==null);o.push(w.length?w.reduce((a,b)=>a+b,0)/w.length:null);}}return o;}};
  Plotly.newPlot('ic-series-chart',[
    {{x:months,y:ts('treatment'),mode:'lines',name:'treatment',line:{{color:'#60a5fa',width:1}},opacity:0.5}},
    {{x:months,y:ts('price_only'),mode:'lines',name:'price-only',line:{{color:'#94a3b8',width:1}},opacity:0.5}},
    {{x:months,y:ts('differential'),mode:'lines',name:'差分',line:{{color:'#f59e0b',width:1}},opacity:0.6}},
    {{x:months,y:roll(ts('differential')),mode:'lines',name:'差分(6月滚动)',line:{{color:'#f59e0b',width:3}}}}],
    Object.assign({{}},dark,{{margin:{{l:45,r:25,t:10,b:40}},height:320,hovermode:'x unified',
      xaxis:{{title:'月',gridcolor:'#334155'}},yaxis:{{title:'月频 rank-IC',zeroline:true,gridcolor:'#334155'}},
      legend:{{x:0.01,y:1.15,orientation:'h'}}}}),{{displayModeBar:false,responsive:true}});
}}
</script>
</body></html>"""

    out = site_dir / "index.html"
    out.write_text(html, encoding="utf-8")
    print(f"✅ 构建中文站点（Tailwind 暗色）: {out} ({out.stat().st_size:,} bytes); "
          f"IC 序列: {'已加载' if ic_data else '缺失'}")
    return out


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="构建 Aionis 静态研究站点（默认 site/；hermetic 测试用 --out-dir）",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=SITE_DIR,
        help="输出目录（默认 %(default)s；测试传 tmp_path，避免触碰 site/ 工作树）",
    )
    args = parser.parse_args()
    build(args.out_dir)
