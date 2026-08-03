# 条件化 rank-IC 多重检验预算设计（Option A′ gate 7）

> 日期：2026-08-03
> 类型：设计笔记（**PROPOSED**，非 ADR、非冻结）
> 解决：独立批判者 #4（"条件化 rank-IC 完全炸掉 n_trials=30 / DSR·J-T 门失效"）
> 约束：不触冻结面 / ledger；PROPOSED，待 owner 冻结才进 Track C 预注册。
> 关联：[`track-b-preregistration.md`](../../docs/track-b-preregistration.md) §8、[`ADR-010`](../../decisions/ADR-010-sesoi-tost-sequential-gate.md)、[`market-driver-framework.md`](../../docs/market-driver-framework.md) §6.1（TACO PIT regime 构造）、[`2026-08-03-qlib-dualregion-poc.md`](../2026-08-03-qlib-dualregion-poc.md)。

## 0. 问题

批判者 #4：把 rank-IC 条件化在 K 个 regime 状态（板块/宏观/跨市场传染）上 = K 个比较，
treatment-minus-baseline 差分变成 K 个检验 → n_trials=30 "完全炸掉" → DSR/J-T 群序贯门失效。

## 1. 解决：预指定交互 = 1 个检验，不是 K 个

多重检验文献的核心区分（**复用方法论，不重造**）：

- **事后子组捞鱼（post-hoc subgroup fishing）**：看了数据后挑 K 个 regime 各自检验 → K 个隐式检验
  → 必须 Bonferroni/BHY 校正 → n_trials 爆炸。**这是批判者正确担心的罪。**
- **预指定交互（pre-specified interaction）**：见数据**前**预注册一个交互项 `treatment × regime`，
  检验"treatment 效应是否随 regime 变化"→ **1 个假设，multiplicity 预算 = 1**，不增加 n_trials。

> ⇒ Option A′ 的 conditioning 必须**作为单个预指定交互项注册**（Track C 预注册冻结前），
> **不是** K 个事后子组。这样 n_trials=30 不被炸，DSR/J-T 门仍有效。

## 2. 复用轮子（Aionis 已装 + 文献）

### Aionis 已装（直接用，零新依赖）
| 轮子 | license | 角色 |
|---|---|---|
| `eslazarev/purgedcv` | MIT | DSR / PBO / CPCV（Track B §8 已用） |
| `arch.bootstrap` | BSD | Hansen-SPA / MCS / StepM |
| `YannickKae/Evaluating-Investment-Strategies` | CC0 | Harvey-Liu haircut 端口 |

Track B 预注册 §8 已设 `n_trials=30` + DSR + PBO + haircut；Track C 沿用同一多重检验机器。

### 文献（复用方法论）
- **Harvey-Liu-Zhu 2016**（`ssrn.com/abstract_id=2249314`）— factor zoo 多重检验框架；t > 3.0 hurdle；
  Bonferroni/Holm/BHY。Aionis `frontier_positioning.md` 已引。
- **Harvey-Liu 2015 "Backtracking"**（`people.duke.edu/~charvey/…/P120_Backtesting.PDF`）— BHY haircut；
  非线性（小 Sharpe 重罚、大 Sharpe 轻罚）。
- **Bailey-López de Prado "Deflated Sharpe Ratio"**（`davidhbailey.com/dhbpapers/deflated-sharpe.pdf`）—
  N independent trials + 非正态修正。
- **🆕 Deflated-RankICIR**（FARS 2026, `lemma-public-asset.analemma.ai/…/idea_54571e91…/main.pdf`）—
  **把 DSR 直接适配到因子级 RankIC 时间序列**（Aionis 的 estimand）：pairwise 相关估有效试验数
  `N̂ = ρ̂ + (1−ρ̂)·M`，stationary bootstrap（block=20d, 1000 reps）估每因子 SE。CSI300 × 70 LLM 因子
  实测 IR 1.717。**直接对靶 rank-IC 多重检验**——比策略级 DSR 更贴 Aionis。
  ⚠️ **待查**：代码是否公开 + license（论文 PDF 仅述方法；需 GitHub 检索）。若 permissive，是 gate 7 主轮子。

## 3. PROPOSED 预算（Track C，待 owner 冻结）

1. **conditioning = 单个预指定交互项**（`treatment × regime`），multiplicity 预算 = **1**（非 K）。
   - 双尾 claim："treatment 效应是否随 regime 显著变化" + "条件化后的 treatment-vs-baseline 差分"。
2. **n_trials = 30 沿用** Track B（DSR/haircut/SPA 喂**全部试过**的 config，含丢弃的）。
3. **regime 必须 PIT 构造**（`market-driver-framework.md:178-181` TACO 范式：as-of 固定窗 σ 归一化，
   **绝不追溯重算**），否则 regime 定义本身泄漏（批判者 M1）。
4. **主轮子**：`purgedcv` DSR + haircut（已装）；若 Deflated-RankICIR license-clean，采用其因子级
   RankIC 多重检验作为对靶升级。
5. **J-T 群序贯等价门**（`ADR-010`）应用于**交互项差分**的 rank-IC 序列（RCIₖ ⊂ [−SESOI,+SESOI]）。

## 4. 对批判者 #4 的裁决

**PARTIAL → 解决。** 批判者对"事后子组 = K 检验"的担心成立（是真罪）；但 Option A′ 用**预指定交互
（1 检验）+ Aionis 已有 DSR/haircut 机器**，n_trials=30 不被炸、J-T 门不失效。批判者"完全炸掉/门失效"
**过强**。

**门（实证背书）：** conditioning 必须 ① 预注册为单交互项（非事后子组）+ ② regime PIT 构造（TACO 范式）。

## 5. 不越界声明

- 本笔记是 **PROPOSED 设计**；未触冻结面 / ledger / prereg / ADR / config / 结果 / E3。
- 未运行任何 confirmatory/strategy/forward 脚本；未观察 E3 outcome。
- Deflated-RankICIR 的代码可用性 / license 待查；未确认前不主张采用，只作候选。
- Track C 的任何落地都是**新预注册 + 新 config + 新 ledger 行**，绝不静默修改 B/C/D/E1 或 Track B。
