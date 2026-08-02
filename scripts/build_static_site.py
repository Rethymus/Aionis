"""构建 Aionis 静态研究站点（Tailwind CSS · 暗色金融终端风 · 中文）→ site/index.html。

设计（业主 2026-08-02 反馈：参考 data.xiaoyinsi.com 的 UI，勿手搓 CSS）：
- 复用 **Tailwind CSS**（CDN，成熟框架，参考站同款）——不手写 CSS。
- 暗色金融终端风：顶部导航 + KPI 数据卡 + 卡片网格 + 数据表 + 高密度。
- 全中文；内容驱动（真实 Track B 差分结果 + 七主题 + 反泄漏 + 边界）。
- 图表 plotly（暗色模板，数据驱动；统计量由 rank_ic_summary 预计算嵌入）。
- 数据源：site/track_b_data.json（a-run --mode differential 生成；缺失则无 IC 序列图）。

Run:  uv run python scripts/build_static_site.py
"""
from __future__ import annotations

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
SITE_DIR = PROJECT_ROOT / "site"
SITE_DIR.mkdir(exist_ok=True)

# 真实 headline（Track B 首个差分，config #41/#42，chronological walk-forward 2021-01..2026-06）
TREATMENT = {"name": "treatment", "sub": "七主题 23 特征 (#41)", "mean": 0.005511,
             "ci": (-0.021441, 0.032463), "p": 0.6886}
PRICE_ONLY = {"name": "price-only", "sub": "10 价格特征 (#42)", "mean": -0.002062,
              "ci": (-0.031623, 0.027500), "p": 0.8913}
DIFFERENTIAL = {"name": "差分", "sub": "treatment − price-only (§1 headline)", "mean": 0.007572,
                "ci": (-0.004492, 0.019636), "p": 0.2186}
SESOI = 0.010

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
    ("两尾 · 预注册 · null-favored", "每条 claim 预注册；null-with-tight-CI 即可发表"),
]

STATUS_STYLE = {"ok": ("已覆盖", "emerald"), "warn": ("延后", "amber"), "todo": ("待挂", "slate")}


def _load_ic_series() -> dict | None:
    path = SITE_DIR / "track_b_data.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


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


def build() -> Path:
    ic_data = _load_ic_series()
    ic_data_json = json.dumps(ic_data) if ic_data else "null"
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
      <a href="#themes" class="hover:text-slate-100">七主题</a>
      <a href="#result" class="hover:text-slate-100">差分结果</a>
      <a href="#discipline" class="hover:text-slate-100">反泄漏</a>
      <a href="#boundary" class="hover:text-slate-100">边界</a>
    </div>
  </div>
</nav>

<!-- 探索性横幅 -->
<div class="bg-amber-500/10 border-b border-amber-500/30 text-amber-300 text-center text-xs py-1.5">
  ⚠️ 探索性 · 首个 OOS 结果 · 非投资建议 · null 是预期可发表成果
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

    out = SITE_DIR / "index.html"
    out.write_text(html, encoding="utf-8")
    print(f"✅ 构建中文站点（Tailwind 暗色）: {out} ({out.stat().st_size:,} bytes); "
          f"IC 序列: {'已加载' if ic_data else '缺失'}")
    return out


if __name__ == "__main__":
    build()
