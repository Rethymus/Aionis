export type Lang = "zh" | "en";

export const dict = {
  zh: {
    "brand.name": "Aionis",
    "brand.tagline": "反泄漏选股研究终端",

    "nav.group.insights": "洞察",
    "nav.group.monitor": "监测",
    "nav.group.reference": "参考",
    "nav.overview": "总览",
    "nav.picks": "选股决策",
    "nav.evidence": "证据墙",
    "nav.powerfloor": "Power Floor",
    "nav.discipline": "反泄漏纪律",
    "nav.method": "研究方法",

    "ticker.label": "模型评分实时榜",

    "hero.title": "看清选股背后的反泄漏底牌",
    "hero.subtitle": "追踪反泄漏纪律下的选股决策、证据墙与功率地板——null 是预期、可发表的结果。",
    "hero.badge": "个人兴趣研究 · 非投资建议",

    "kpi.combined_ic": "Confirmatory rank-IC",
    "kpi.n_months": "样本外月数",
    "kpi.p_value": "p 值 (HAC)",
    "kpi.verdict": "J-T look-1 判定",
    "kpi.h6": "H₆ 确定性",

    "module.picks.title": "选股决策榜",
    "module.picks.window": "最新样本外月 · 模型评分",
    "module.picks.cta": "完整榜单 →",
    "module.evidence.title": "证据墙",
    "module.evidence.window": "14 条预注册配置 · 全部 null",
    "module.evidence.cta": "查看全部 →",
    "module.powerfloor.title": "Power Floor 监测",
    "module.powerfloor.window": "ML 噪声超额 · 21 个 IC 系列",
    "module.discipline.title": "反泄漏仪表盘",
    "module.discipline.window": "PIT / embargo / H6 实时状态",

    "callout.noninvestment": "非投资建议",

    "picks.col.rank": "排名",
    "picks.col.ticker": "标的",
    "picks.col.score": "模型评分",
    "picks.col.change": "排名变化",
    "picks.region.us": "美股",
    "picks.region.cn": "A 股",
    "picks.intro": "Aionis 模型对最新样本外月的选股排名（LightGBM rank-IC 评分）。排名变化箭头对比上月。",
    "picks.shorts.title": "做空端（模型最不看好）",

    "evidence.intro": "跨 14 条预注册配置，没有任何 treatment 臂相对 price-only 基线显示可靠的正向增量 rank-IC。所有置信区间都跨越零。",
    "evidence.grade.CV-proxy": "CV 代理",
    "evidence.grade.chron": "时序/探索",
    "evidence.grade.CONFIRMATORY": "Confirmatory",

    "powerfloor.intro": "在月频 rank-IC 噪声地板下，宣告 ±0.010 等价结构性不可行——地板由 ML 噪声超额驱动，非纯数学界。",
    "discipline.intro": "反泄漏纪律的活体状态：点在时间数据、purged 折 + embargo、H6 比特一致确定性。",

    "footer.note": "个人兴趣研究 · null 是预期结果 · 非投资建议",
  },
  en: {
    "brand.name": "Aionis",
    "brand.tagline": "Anti-leakage stock-pick research terminal",

    "nav.group.insights": "Insights",
    "nav.group.monitor": "Monitoring",
    "nav.group.reference": "Reference",
    "nav.overview": "Overview",
    "nav.picks": "Stock Picks",
    "nav.evidence": "Evidence Wall",
    "nav.powerfloor": "Power Floor",
    "nav.discipline": "Anti-leakage",
    "nav.method": "Method",

    "ticker.label": "Model score live ticker",

    "hero.title": "See the anti-leakage cards behind every stock pick",
    "hero.subtitle": "Track stock-pick decisions, the evidence wall, and the power floor under anti-leakage discipline — null is the intended, publishable outcome.",
    "hero.badge": "Personal research · non-investment advice",

    "kpi.combined_ic": "Confirmatory rank-IC",
    "kpi.n_months": "Out-of-sample months",
    "kpi.p_value": "p-value (HAC)",
    "kpi.verdict": "J-T look-1 verdict",
    "kpi.h6": "H₆ determinism",

    "module.picks.title": "Stock-pick ranking",
    "module.picks.window": "Latest OOS month · model score",
    "module.picks.cta": "Full ranking →",
    "module.evidence.title": "Evidence wall",
    "module.evidence.window": "14 pre-registered configs · all null",
    "module.evidence.cta": "View all →",
    "module.powerfloor.title": "Power Floor monitor",
    "module.powerfloor.window": "ML noise excess · 21 IC series",
    "module.discipline.title": "Anti-leakage dashboard",
    "module.discipline.window": "PIT / embargo / H6 live status",

    "callout.noninvestment": "Non-investment advice",

    "picks.col.rank": "Rank",
    "picks.col.ticker": "Ticker",
    "picks.col.score": "Model score",
    "picks.col.change": "Rank change",
    "picks.region.us": "US",
    "picks.region.cn": "CN (A-share)",
    "picks.intro": "Aionis model's stock-pick ranking for the latest out-of-sample month (LightGBM rank-IC score). Arrows compare against last month.",
    "picks.shorts.title": "Short side (model's least-favored)",

    "evidence.intro": "Across 14 pre-registered configurations, no treatment arm shows a reliable positive incremental rank-IC over the price-only baseline. All CIs bracket zero.",
    "evidence.grade.CV-proxy": "CV-proxy",
    "evidence.grade.chron": "chron./explor.",
    "evidence.grade.CONFIRMATORY": "Confirmatory",

    "powerfloor.intro": "At the monthly rank-IC noise floor, declaring ±0.010 equivalence is structurally infeasible — the floor is driven by the ML noise excess, not the pure math bound.",
    "discipline.intro": "Live status of the anti-leakage discipline: point-in-time data, purged folds + embargo, H6 bit-identical determinism.",

    "footer.note": "Personal research · null is the intended outcome · non-investment advice",
  },
} as const;

export type DictKey = keyof typeof dict["zh"];
