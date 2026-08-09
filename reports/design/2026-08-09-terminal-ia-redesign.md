# Terminal IA redesign — from disjointed panels to a decision funnel (PROPOSED)

> Owner critique (2026-08-09): the terminal feels like "几个零散项目拼凑出来的杂项目"
> — modules are bolted-on, not an organic whole; data doesn't help the user form a
> stock-picking thesis. Plus concrete gaps (taco empty on deploy, reddit thin, Trump
> inaugurations unmarked, themes ④⑤ empty, data not 2016→latest).
> This is the **design draft** for the rebuild. Status: PROPOSED, owner-review.
> No code/ledger/frozen surface changed in this doc.

## 0. The real problem (IA, not data)

The terminal has ~16 panels but presents them as a **flat nav list** (insights /
alternative / monitor / reference). A user lands and cannot tell **how to use them
to decide**. Each panel answers a question, but the questions aren't ordered into a
reasoning chain. Fixing this is **information architecture**, not adding more charts.

## 1. Data-coverage truth (2016 audit, grounded in the actual JSONs)

| Panel | Coverage | Verdict |
|---|---|---|
| market_context, taco, cot | **2016→2026** ✓ | Already full — deploy-stale; redeploy surfaces it |
| smart_money (13D) | display = recent 60, latest **2024-12** | Stale: forward collector hasn't run; **deepen display + refresh** |
| form4 | display = recent 50 (underlying 2013-2026) | **Deepen display** to show full history |
| ic_monthly, picks_backtest, pick_conviction | **2021+ (OOS window)** | **Research boundary** — extending to 2016 = rerun-to-significance (FORBIDDEN). Frame honestly as "OOS 2021+" |
| reddit | forward-only, 1 snapshot | **Structural**: Pushshift dead 2023; no permissive 2016 corpus. Honest label only |
| themes ④ news / ⑤ risk | placeholders | **Build**: news = filings/earnings LLM (forward-only); risk = pyfolio adapter |

**Implication**: "all data 2016→latest" is **partly impossible** (reddit), **partly a
research boundary** (model outputs 2021+), and **partly a deploy/refresh gap** (the
rest). The terminal must **label these honestly** instead of looking broken.

## 2. The through-line: a 6-step decision funnel

The terminal's job: help the user **form + validate a stock-picking thesis**. A thesis
= "in THIS regime, THESE themes favor THESE stocks, confirmed by smart-money/insiders,
model track-record = X." So the nav becomes an ordered funnel — each step answers one
question and feeds the next:

| Step | Question | Panels |
|---|---|---|
| **① 定调 Regime** | What market is this? | 市场全景 · 多空压力(COT) · TACO |
| **② 定向 Themes** | Where to look? | 七主题 (operationalized: direction × strength × favored) |
| **③ 定标 Picks** | What specifically? | 选股决策 · 板块概率 · 选股确信度 |
| **④ 佐证 Confirmation** | What do others think? | 聪明钱(13D) · 内部人(Form4) · 散户(Reddit) |
| **⑤ 问责 Track record** | How good is the model? | 命中记录 · 校准可靠性 · Power Floor |
| **⑥ 边界 Discipline** | Why trust it / limits? | 反泄漏纪律 · 证据墙(null) · 研究方法 |

Every panel gets a **one-line role tagline** in its header (e.g. themes: "此刻哪个
主题在发什么信号 → 决定往哪个方向看"). This is what makes it feel organic — each
module declares its place in the reasoning.

## 3. Seven-themes operationalization (fixing the "生硬" panel)

Current: 7 cards showing "cross-sectional mean of momentum_21d = 0.3" — meaningless to
a user. Rebuild each theme to show:

- **Direction**: 极性 (bullish / bearish / neutral) — sign vs forward return or regime.
- **Strength**: 强度 (distance from neutral, normalized).
- **Favors**: 此刻利好的板块/个股 (top-decile names by this theme's signal).
- **Status**: live / forward-only / needs-data (honest).

→ A user reads "① 价格动量: 偏多 · 强 · 利好半导体" and knows **what to do**. The 7
themes stop being "abstract means" and become **directional guidance**.

## 4. Honest-labeling policy (make constraints visible, not broken-looking)

| Constraint | Label on the panel |
|---|---|
| Reddit forward-only | badge: "forward-only · 自 2026-08-08 累积 · 无 2016 历史 (Pushshift 2023 已死)" |
| Model outputs (ic/backtest/conviction) | badge: "OOS 窗口 2021+ · 研究冻结边界" |
| Themes ④⑤ placeholders | status: "forward-only / 待适配" (already exists) |
| Research null (#49) | frame as "诚实披露: 模型判别力弱" not "broken" |

## 5. Delete the template cruft (the "obsolete" feeling)

`web/src/components/{accounts, cards, budgets, crypto, dashboard(account-cards…),
investments, transactions, transfers, notifications, settings, support}` are
**shadcn-fintech template leftovers** — **zero routes use them** (real routes use
`overview/` + the `<view>-view.tsx` files). Delete them: smaller bundle, less
"why does a quant terminal have a Netflix-subscription card?" confusion.

## 6. P2: continuous refresh (the owner's "持续更新到最新")

`refresh-terminal-data.yml` exists (daily Mon-Fri) but **only re-exports JSONs from
existing parquets** — it does NOT fetch new raw data (that's why smart_money is stuck
at 2024-12). **Extend it** to run the forward collectors before re-export, on the
owner's preferred cadence:

```
weekly (Fri post-US-close) or daily:
  cot_fetch → form4_fetch → reddit_fetch → stakes_13d_forward → macro_forward
  → export_terminal_data.py → commit JSONs → (push triggers deploy)
```

Leakage-safe: display-layer only; never touches the frozen OOS pipeline / ledger.

## 7. Phased execution

| Phase | Work | Risk |
|---|---|---|
| **P1 (this commit)** | Trump inaugurations marked (market events + style) + 2016 audit + redeploy | low |
| **P2** | Extend refresh cron with forward collectors (weekly); deepen smart_money/form4 display history | low (leakage-safe) |
| **P3a** | Funnel nav regroup (6 steps) + role taglines per panel + delete template cruft | medium (IA) |
| **P3b** | Seven-themes operationalization (direction × strength × favors) | medium |
| **P4** | Fill themes ④ (filings-LLM, forward-only) + ⑤ (pyfolio risk) | medium |

## 8. Boundary

This doc is PROPOSED design only. P1 (Trump events + redeploy) is executed in the same
commit; P2–P4 await owner review of this funnel + per-phase GO. No frozen surface /
ledger / research estimator / E3 touched.
