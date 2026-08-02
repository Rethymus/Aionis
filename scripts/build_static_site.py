"""构建 Aionis 静态研究站点（中文、内容驱动、真实结果）→ site/index.html。

设计原则（业主反馈 2026-08-02）：
- 全中文（项目身份、结论、边界）。
- 内容驱动：呈现真实研究故事（战略复盘 + Track B 首个差分结果 + 七主题覆盖 + 反泄漏纪律），
  非通用 demo。
- 复用优先：统计量（rank-IC / HAC CI）由项目真实函数预计算（rank_ic_summary），嵌入真实数字；
  图表用 plotly（数据驱动的 CI/折线图，非手搓 tearsheet 轮子）。
- 数据源：site/track_b_data.json（由 scripts/track_b_a_run.py --mode differential 生成）；
  若缺失则用嵌入的 headline 数字（无 IC 时间序列图）。

Run:  uv run python scripts/build_static_site.py
"""
from __future__ import annotations

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
SITE_DIR = PROJECT_ROOT / "site"
SITE_DIR.mkdir(exist_ok=True)

# --- 真实 headline 结果（Track B 首个差分，config #41/#42，2026-08-02）---
# 来源：scripts/track_b_a_run.py --mode differential 的输出（chronological walk-forward,
# expanding min_train=60, embargo=21, 2021-01..2026-06, 66 folds）。
TREATMENT = {"name": "treatment（七主题，23 特征，#41）", "mean": 0.005511,
             "ci": (-0.021441, 0.032463), "p": 0.6886}
PRICE_ONLY = {"name": "price-only baseline（10 价格特征，#42）", "mean": -0.002062,
              "ci": (-0.031623, 0.027500), "p": 0.8913}
DIFFERENTIAL = {"name": "差分（treatment − price-only，§1 headline）", "mean": 0.007572,
                "ci": (-0.004492, 0.019636), "p": 0.2186}
SESOI = 0.010  # 预注册 §7 经济等价门槛

# --- 七主题覆盖矩阵（来源：reports/2026-08-02-strategic-review + reuse-catalog-v2）---
SEVEN_THEMES = [
    ("① 行情 / 价格", "Tiingo + Alpaca（adjClose）", "已覆盖", "退市价缺失（结构性，保守上界）"),
    ("② 宏观", "ALFRED vintage（FRED）", "已覆盖", "macro 会修订 → 必须 vintage"),
    ("③ 基本面", "EDGAR XBRL filed-date（edgartools）", "已覆盖（13 特征）", "filed 非 period-end"),
    ("④ 新闻情绪", "E3 闭集 13D/8-K 抽取 + FinGPT embedding", "延后（S3 ablation）",
     "LLM 参数记忆泄漏；不作主 alpha"),
    ("⑤ 风险", "alphalens / pyfolio / empyrical（Apache）", "评估层（待挂接）",
     " tearsheet 在评估层覆盖"),
    ("⑥ 回测净成本", "FINSABER（Apache，KDD 2026）", "待挂接",
     "next-open / slippage / liquidity"),
    ("⑦ 市场结构", "FF5 残差 + Amihud（statsmodels + 文献）", "已实现（ff5_residual.py）",
     "FF 无 vintage（声明）"),
]

# --- 反泄漏链 ---
ANTI_LEAKAGE = [
    ("config_committed 先于 result", "ledger 行 #40/#41/#42 在任何 OOS 观察前入 ledger"),
    ("PIT 数据", "EDGAR filed-date / ALFRED vintage / S&P constituents_on（非今日快照）"),
    ("chronological walk-forward", "expanding，min_train=60 月，embargo=21 sessions，"
                                  "assert max(train)<min(test)（非 shared-fold CV-proxy）"),
    ("H6 确定性", "n_jobs=1，全 seed=0，version-pinned；同 config 重跑 bit-identical"),
    ("两尾、预注册、null-favored", "每条 claim 预注册；null-with-tight-CI 是可发表成果"),
]


def _load_ic_series() -> dict | None:
    """加载 site/track_b_data.json（IC 月度序列）；缺失则返回 None。"""
    path = SITE_DIR / "track_b_data.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _theme_table_html() -> str:
    rows = "\n".join(
        f"<tr><td>{theme}</td><td>{src}</td><td>{status}</td><td>{gap}</td></tr>"
        for theme, src, status, gap in SEVEN_THEMES
    )
    return (
        '<table class="data-table"><thead><tr>'
        "<th>主题</th><th>数据源 / 轮子</th><th>覆盖状态</th><th>泄漏 gotcha / 注</th>"
        f"</tr></thead><tbody>{rows}</tbody></table>"
    )


def _antileakage_html() -> str:
    items = "\n".join(
        f'<li><strong>{title}</strong>：{desc}</li>' for title, desc in ANTI_LEAKAGE
    )
    return f'<ul class="anti-leakage">{items}</ul>'


def build() -> Path:
    ic_data = _load_ic_series()
    ic_data_json = json.dumps(ic_data) if ic_data else "null"

    diff_verdict = (
        "差分 95% CI 跨零、p=0.219 → <strong>treatment 未显著优于 price-only baseline</strong>"
        "（符合 null-favored 预注册）。"
    )
    equiv_note = (
        f"但 CI 上界 {DIFFERENTIAL['ci'][1]:+.4f} &gt; SESOI ±{SESOI} → "
        "<strong>不构成严格等价</strong>（RCI ⊄ [−0.010,+0.010]），差分可能高达 ~0.020，"
        "需更多样本才能宣称等价。"
    )

    ic_section = (
        '<div class="chart-card"><div id="ic-series-chart"></div>'
        '<p class="caption">月度 rank-IC 序列（2021-01..2026-06，chronological walk-forward，'
        "真实 OOS 数据）。</p></div>"
        if ic_data
        else '<p class="muted">IC 月度序列图待 site/track_b_data.json 生成'
        '（运行 <code>track_b_a_run.py --mode differential</code>）。</p>'
    )

    html = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Aionis — 可证伪、反泄漏的横截面选股研究</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:"PingFang SC","Noto Sans SC","Microsoft YaHei",-apple-system,sans-serif;
       background:#f8fafc; color:#1e293b; line-height:1.7; }}
.banner {{ background:linear-gradient(135deg,#b45309,#92400e); color:#fff; text-align:center;
          padding:.8rem 1rem; font-weight:600; font-size:.95rem; letter-spacing:.3px; }}
.container {{ max-width:1000px; margin:0 auto; padding:2rem 1.2rem; }}
.hero {{ text-align:center; margin-bottom:2rem; padding-bottom:1.5rem; border-bottom:1px solid #e2e8f0; }}
.hero h1 {{ font-size:2rem; color:#0f172a; margin-bottom:.4rem; }}
.hero .tagline {{ color:#64748b; font-size:1.05rem; }}
.hero .badges {{ margin-top:.8rem; }}
.badge {{ display:inline-block; background:#eff6ff; color:#1d4ed8; border:1px solid #bfdbfe;
         border-radius:999px; padding:.2rem .8rem; font-size:.85rem; margin:.15rem; }}
.finding {{ background:#fff; border:1px solid #e2e8f0; border-left:5px solid #0f172a;
           border-radius:8px; padding:1.5rem; margin-bottom:2rem; box-shadow:0 1px 3px rgba(0,0,0,.06); }}
.finding h2 {{ font-size:1.25rem; margin-bottom:.6rem; }}
.finding .verdict {{ font-size:1.05rem; }}
.finding .equiv {{ margin-top:.5rem; color:#92400e; font-size:.95rem; }}
section {{ margin-bottom:2rem; }}
section h2 {{ font-size:1.3rem; color:#0f172a; margin-bottom:.8rem; padding-bottom:.4rem;
             border-bottom:2px solid #e2e8f0; }}
.data-table {{ width:100%; border-collapse:collapse; background:#fff; border-radius:8px;
              overflow:hidden; box-shadow:0 1px 3px rgba(0,0,0,.06); font-size:.92rem; }}
.data-table th {{ background:#f1f5f9; padding:.7rem .6rem; text-align:left; font-weight:600;
                 border-bottom:2px solid #e2e8f0; }}
.data-table td {{ padding:.6rem; border-bottom:1px solid #f1f5f9; vertical-align:top; }}
.data-table tr:last-child td {{ border-bottom:none; }}
.chart-card {{ background:#fff; border:1px solid #e2e8f0; border-radius:8px; padding:1rem;
              margin:1rem 0; box-shadow:0 1px 3px rgba(0,0,0,.06); }}
.anti-leakage {{ list-style:none; }}
.anti-leakage li {{ background:#fff; border:1px solid #e2e8f0; border-left:4px solid #16a34a;
                   border-radius:6px; padding:.7rem 1rem; margin-bottom:.5rem; }}
.boundary {{ background:#fef2f2; border:1px solid #fecaca; border-left:4px solid #dc2626;
            border-radius:6px; padding:1rem 1.2rem; }}
.boundary ul {{ margin-left:1.2rem; }}
.caption {{ text-align:center; color:#94a3b8; font-size:.85rem; margin-top:.4rem; }}
.muted {{ color:#94a3b8; }}
code {{ background:#f1f5f9; padding:.1rem .35rem; border-radius:3px; font-size:.9em; }}
.footer {{ text-align:center; margin-top:2.5rem; padding-top:1.5rem; border-top:1px solid #e2e8f0;
          color:#94a3b8; font-size:.9rem; }}
.footer a {{ color:#2563eb; text-decoration:none; }}
@media (max-width:640px) {{ .hero h1 {{ font-size:1.5rem; }} .data-table {{ font-size:.82rem; }} }}
</style>
</head>
<body>
<div class="banner">⚠️ 探索性 · 首个 OOS 结果 · 非投资建议 · null-favored（null 是预期可发表成果）</div>
<div class="container">
  <div class="hero">
    <h1>Aionis</h1>
    <div class="tagline">可证伪、反泄漏的横截面选股研究 · S&amp;P 500 月频 rank-IC</div>
    <div class="badges">
      <span class="badge">config_committed 先于 result</span>
      <span class="badge">PIT 数据</span>
      <span class="badge">chronological walk-forward</span>
      <span class="badge">H6 确定性</span>
      <span class="badge">null-favored 两尾</span>
    </div>
  </div>

  <div class="finding">
    <h2>📊 核心发现：Track B 首个 headline 差分（null）</h2>
    <div class="verdict">{diff_verdict}</div>
    <div class="equiv">{equiv_note}</div>
    <div class="chart-card"><div id="ci-chart"></div></div>
  </div>

  <section>
    <h2>🔎 战略复盘结论（2026-08-02）</h2>
    <p>方向<strong>没跑偏</strong>——反泄漏纪律与 null-first 立场是稀缺且正确的价值。存在两处"失调"：
    目标叙事双轨（窄 harness vs 宽选股平台）已裁断为 <strong>Track B（七主题平台）</strong>；
    治理机器复杂度曾超过研究产出，现已切换到"用治理产出研究"。详见
    <code>reports/2026-08-02-strategic-review-coverage-and-alignment.md</code>。</p>
  </section>

  <section>
    <h2>🌐 七主题覆盖矩阵</h2>
    {_theme_table_html()}
  </section>

  <section>
    <h2>📈 首个差分结果（chronological walk-forward, 2021-01..2026-06, 66 折）</h2>
    <table class="data-table">
      <thead><tr><th>臂</th><th>mean</th><th>95% HAC CI</th><th>p</th></tr></thead>
      <tbody>
        <tr><td>{TREATMENT['name']}</td><td>{TREATMENT['mean']:+.4f}</td>
            <td>({TREATMENT['ci'][0]:+.4f}, {TREATMENT['ci'][1]:+.4f})</td><td>{TREATMENT['p']:.3f}</td></tr>
        <tr><td>{PRICE_ONLY['name']}</td><td>{PRICE_ONLY['mean']:+.4f}</td>
            <td>({PRICE_ONLY['ci'][0]:+.4f}, {PRICE_ONLY['ci'][1]:+.4f})</td><td>{PRICE_ONLY['p']:.3f}</td></tr>
        <tr><td><strong>{DIFFERENTIAL['name']}</strong></td>
            <td><strong>{DIFFERENTIAL['mean']:+.4f}</strong></td>
            <td><strong>({DIFFERENTIAL['ci'][0]:+.4f}, {DIFFERENTIAL['ci'][1]:+.4f})</strong></td>
            <td><strong>{DIFFERENTIAL['p']:.3f}</strong></td></tr>
      </tbody>
    </table>
    {ic_section}
  </section>

  <section>
    <h2>🛡️ 反泄漏纪律（不可妥协）</h2>
    {_antileakage_html()}
  </section>

  <section>
    <h2>⚠️ 诚实边界</h2>
    <div class="boundary">
      <ul>
        <li>此结果仅适用于：lambdarank / 23 vs 10 特征 / 2016+ PIT S&amp;P 500 / 幸存者偏差"可缓解不可根除"。</li>
        <li><strong>不证明</strong>："市场有效" / "七主题无效" / "可交易" / "策略可承载资金"。</li>
        <li><strong>可写</strong>："在此实现与样本下，未观察到 treatment 显著优于 price-only 的横截面 rank-IC。"</li>
        <li>差分 CI 上界 0.020 &gt; SESOI 0.010 → 非严格等价，需更多样本。</li>
      </ul>
    </div>
  </section>

  <div class="footer">
    <p>Aionis · 可证伪、反泄漏的量化选股研究 harness（非交易机器人）</p>
    <p><a href="https://github.com/Rethymus/Aionis">GitHub 仓库</a> ·
       <a href="https://github.com/Rethymus/Aionis/blob/main/docs/track-b-preregistration.md">Track B 预注册</a> ·
       <a href="https://github.com/Rethymus/Aionis/blob/main/docs/track-b-results.md">完整结果快照</a></p>
  </div>
</div>

<script>
const SESOI = {SESOI};
const treatment = {{mean: {TREATMENT['mean']}, lo: {TREATMENT['ci'][0]}, hi: {TREATMENT['ci'][1]}, name: {json.dumps(TREATMENT['name'], ensure_ascii=False)}}};
const priceOnly = {{mean: {PRICE_ONLY['mean']}, lo: {PRICE_ONLY['ci'][0]}, hi: {PRICE_ONLY['ci'][1]}, name: {json.dumps(PRICE_ONLY['name'], ensure_ascii=False)}}};
const differential = {{mean: {DIFFERENTIAL['mean']}, lo: {DIFFERENTIAL['ci'][0]}, hi: {DIFFERENTIAL['ci'][1]}, name: {json.dumps(DIFFERENTIAL['name'], ensure_ascii=False)}}};

// 差分 CI 条形图（水平 error bars + SESOI 带 + 零线）
const arms = [treatment, priceOnly, differential];
const ciTrace = {{
  x: arms.map(a => a.mean), y: arms.map(a => a.name),
  error_x: {{type:'data', symmetric:false,
             array: arms.map(a => a.hi-a.mean), arrayminus: arms.map(a => a.mean-a.lo),
             thickness:2, color:'#1e293b'}},
  mode:'markers', marker:{{size:14, color:['#2563eb','#64748b','#dc2626']}},
  type:'scatter', name:'mean ± 95% CI'
}};
const sesoiLo = {{x:[-SESOI,-SESOI], y:[differential.name, differential.name], mode:'lines',
                 line:{{color:'#16a34a',dash:'dash',width:2}}, showlegend:false, type:'scatter'}};
const sesoiHi = {{x:[SESOI,SESOI], y:[differential.name, differential.name], mode:'lines',
                 line:{{color:'#16a34a',dash:'dash',width:2}}, name:'SESOI ±0.010', type:'scatter'}};
const zero = {{x:[0,0], y:[treatment.name, differential.name], mode:'lines',
              line:{{color:'#94a3b8',width:1}}, showlegend:false, type:'scatter'}};
Plotly.newPlot('ci-chart', [ciTrace, sesoiLo, sesoiHi, zero],
  {{margin:{{l:260,r:40,t:20,b:50}}, height:300,
    xaxis:{{title:'月频 rank-IC / 差分（95% HAC CI）', zeroline:true}},
    legend:{{x:0.01, y:-0.25, orientation:'h'}}}},
  {{displayModeBar:false, responsive:true}});

// IC 月度时间序列（若数据存在）
const icData = {ic_data_json};
if (icData) {{
  const months = Object.keys(icData.differential.ic_series).sort();
  const toSeries = arm => months.map(m => icData[arm].ic_series[m] ?? null);
  const rolling = arr => {{  // 6 月滚动均值
    const out = []; const W = 6;
    for (let i=0;i<arr.length;i++) {{
      const w = arr.slice(Math.max(0,i-W+1), i+1).filter(v=>v!==null);
      out.push(w.length ? w.reduce((a,b)=>a+b,0)/w.length : null);
    }} return out;
  }};
  const traces = [
    {{x:months, y:toSeries('treatment'), mode:'lines', name:'treatment', line:{{color:'#2563eb',width:1}}, opacity:0.5}},
    {{x:months, y:toSeries('price_only'), mode:'lines', name:'price-only', line:{{color:'#64748b',width:1}}, opacity:0.5}},
    {{x:months, y:toSeries('differential'), mode:'lines', name:'差分', line:{{color:'#dc2626',width:1}}, opacity:0.6}},
    {{x:months, y:rolling(toSeries('differential')), mode:'lines', name:'差分（6月滚动均值）',
      line:{{color:'#dc2626',width:3}}}},
  ];
  Plotly.newPlot('ic-series-chart', traces,
    {{margin:{{l:50,r:30,t:20,b:50}}, height:340, hovermode:'x unified',
      xaxis:{{title:'月'}}, yaxis:{{title:'月频 rank-IC', zeroline:true}},
      legend:{{x:0.01,y:1.12,orientation:'h'}}}},
    {{displayModeBar:false, responsive:true}});
}}
</script>
</body>
</html>"""

    out = SITE_DIR / "index.html"
    out.write_text(html, encoding="utf-8")
    print(f"✅ 构建中文站点: {out} ({out.stat().st_size:,} bytes); "
          f"IC 序列数据: {'已加载' if ic_data else '缺失（仅 headline 数字）'}")
    return out


if __name__ == "__main__":
    build()
