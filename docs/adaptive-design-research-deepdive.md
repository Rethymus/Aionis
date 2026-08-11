# 纪律化自适应 A+B 合题：深度证据补强（retrospective + forward-looking）

**状态**: 研究（未冻结、非决策）。
**日期**: 2026-08-11
**方法**: 主会话 WebSearch（subagent web-tool 路径本日因 GLM [1210] 失败，改主会话执行）。引用真实可验证 URL；深度受限处标注。

> **重要订正（2026-08-11 写后核对 ledger 时发现）**: 撰写时我误以为 "Step 4（自适应预注册）仍是 owner-gated pending"。**实际不是**——Track Adaptive（自适应 vs 冻结基线两尾预注册）已 `config_committed` 三次（#51 monthly-A 作废 → #52 amend1 weekly① → b7621e6b amend2）并于 **2026-08-09 03:01 UTC 跑完首次 OOS**，verdict = **NULL**（IC_diff −0.0037，p=0.26，CI 跨零；adaptive 周扩窗重训略**差于**真·冻结基线；符合 power floor + GKX 更新频率非主导性预期；`state/current.md` 记为 "Track B #54"）。故本文的"Step 4 决策建议"应读作**事后回顾 + 前瞻**，非 pending 决策。

> 续 `docs/adaptive-design-research.md`（A+B 合题）+ `docs/qlib-reuse-audit.md` + `docs/track-adaptive-preregistration.md`（FROZEN + 已出 null 结果）。本 doc 不重复既有内容，只补外部证据 + 复盘 null 的可信度 + 前瞻未来自适应变体。

---

## ① 证据表：自适应/滚动重校 vs 静态（OOS）

| 主张 | 来源 | 判读 | 置信 |
|------|------|------|------|
| 静态因子模型 OOS 衰减（"factor mirage"）| [CFA Institute, 2025](https://rpc.cfainstitute.org/blogs/enterprising-investor/2025/the-factor-mirage-how-quant-models-go-wrong) | **支持自适应**：静态把相关当因果，OOS 失效 | 中（行业博客，非同行评审）|
| 滚动窗口自适应 OOS 持续优于线性静态 | [arXiv 2511.18578](https://arxiv.org/html/2511.18578v1)（时序基础模型金融再评估）| **支持自适应**：rolling estimation windows 一致优于 | 中（arXiv 预印本）|
| 自适应模型 OOS 仍可能挣扎（~50% 准确率）| [Harbourfront Quant, 2024](https://harbourfront.quant/p/the-limits-of-out-of-sample-testing) | **中性/弱反对**：adaptive 不是银弹；窗口长度 + 重校频率是关键 | 中（Substack）|
| 制度转换是核心挑战；自适应最大增益在 regime transition | [OpenReview cPgX9C2BHB](https://openreview.net/forum?id=cPgX9C2BHB)（factor 模型动态 regime）| **支持自适应（条件性）**：收益集中在转换期 | 中 |
| 非平稳性综述：rolling window + CUSUM 等是理论支柱 | [ScienceDirect S092523122602045X](https://www.sciencedirect.com/science/article/pii/S092523122602045X) | **支持自适应（方法学基础）** | 中-高（同行评审综述）|
| Kelly-Malamud-Zhou (2024, JoF)：模型复杂度 vs OOS | [引用](https://www.instagram.com/reel/DaWaHNWOJy0/)（二手）| **中性**：复杂 vs 简单的 OOS 权衡 | 低（二手引用，需核原文）|

**小结**: 文献**弱-中一致**支持"滚动重校 OOS 优于静态"，但**不是银弹**——收益集中在 regime 转换期，窗口/频率选择是关键调参点。这与 Aionis 现有 `docs/adaptive-design-research.md` 的立场（纪律化自适应 ≠ rerun-to-significance）一致。

---

## ② 核心发现：Romano-Wolf × 自适应设计 = 未开垦地带

**这是本次深度调研最重要的发现，直接关系 Step 4 的统计有效性。**

WebSearch 检索 "Romano-Wolf step-down × adaptive design × rolling recalibration × Type I error"：
- **Romano-Wolf step-down**（控制 FWER）是成熟方法：[Romano-Wolf 2005 JASA](https://www.econ.uzh.ch/dam/jcr:ffffffff-935a-b0d6-ffff-ffffd823d949/jasa.pdf)（被引 841）、[stepwise as data snooping, 2005](http://www-stat.wharton.upenn.edu/~steele/Courses/956/Resource/MultipleComparision/RomanoWolf05.pdf)（被引 1418）、[Clarke 2020 Stata 实现](https://ageconsearch.umn.edu/record/340383/files/Clarke.pdf)（被引 455）。
- **自适应/适应性试验设计**（rolling/blinded 样本量重校）是**另一支**文献：Tsiatis-Mehta、Cui-Hung-Wang、Jennison-Turnbull。
- **两者的交叉**——在滚动重校的自适应设计里专门应用 Romano-Wolf——**未检索到 landmark paper**。这是一个**新兴/小众地带**。

**对 Step 4 的含义**:
- Aionis 不能直接引用"自适应 + Romano-Wolf 是已被验证的组合"——因为没人这么做过。
- 两条诚实路径：
  - **路径 A（保守）**: Step 4 的 multiplicity 预算把"自适应每个重校点"都算作一个 hypothesis（家族膨胀），Romano-Wolf 在扩大的家族上跑。代价：power 进一步下降（但 Aionis 本就 null-favored，power 下降不毁结论）。
  - **路径 B（贡献）**: 把"自适应设计下 Romano-Wolf 的正确应用"本身作为 Aionis 的方法学贡献点（与 null 结果 + 反泄漏纪律并列）。这需要更仔细的论证（adaptive design 的 Type-I 控制文献 + RW 的 resampling 在 rolling 下的有效性）。
- **建议**: Step 4 预注册必须**显式声明**采用哪条路径，不能默认"Romano-Wolf 够用"。

---

## ③ RD-Agent(Q) 跟进（NeurIPS 2025）

- **论文**: [R&D-Agent(Q): A Multi-Agent Framework for Data-Centric Factors and Model Joint Optimization](https://arxiv.org/abs/2505.15155)（被引 37）。NeurIPS 2025 Datasets & Benchmarks track。
- **核心**: LLM 多 agent 自动化 quant 研究全环（factor 提案→假设→实现→回测/复现→评审）。报告 **2× baseline 性能**。
- **讨论入口**: [OpenReview thread](https://openreview.net/forum?id=9VxTXAUH7G)、[AlphaXiv](https://alphaxiv.org/abs/2505.15155)、[saulius.io 实战拆解](https://saulius.io/blog/automated-quant-research-ai-agents-rd-agent)。
- **相关**: [DeepFund（NeurIPS 2025 poster）](https://neurips.cc/virtual/2025/poster/121642)——LLM 驱动投资的实时评估基准。

**对 Aionis 的启示（与 `docs/qlib-reuse-audit.md` 一致，强化）**:
- RD-Agent(Q) 证明 LLM-proposed-factor loop 在 quant 有实证增益（2×）——支持 Aionis 探索 LLM 辅助（Step 4 的"低 token 选股公式"愿景）。
- **但 RD-Agent(Q) 不做 purge+embargo、不做 multiple-testing 校正、不 pre-register**——它的 2× 是 median 不是 CI，是 in-the-loop 的。Aionis 嫁接它的 factor-proposal seam 时，必须把这些反泄漏/诚实性外壳保留（已在 `docs/adaptive-design-research.md` §4 层嫁接里设计）。
- **2025-2026 无独立复现失败报告**（OpenReview/AlphaXiv 检索未见负面结果）——但 absence of evidence ≠ evidence of absence；谨慎。

---

## ④ 纪律边界：自适应 vs rerun-to-significance 的结构判据

文献 + 临床试验类比给出的**结构性判据**（Step 4 预注册必须全部满足，否则自适应退化为 rerun-to-significance）:

1. **预注册的适应规则**: 重校频率（如月/季）+ 算法（如 rolling refit 的窗口长度）在看到 OOS 前**冻结于 config**。规则改变 = 新 ledger 行。
2. **样本量预固定**: OOS 窗口的起止 + 长度在预注册时固定（临床类比：adaptive design 的 sample size 还是 pre-fixed，只是分配比例可调）。
3. **Lockbox OOS**: OOS 段在 PurgedGroupKFold+embargo 之外不可见；重校只用 in-fold/in-train 数据。
4. **家族膨胀显式化**: 把"每个重校点的一个检验"计入 multiple-testing 家族，Romano-Wolf 在扩大后的家族上跑（见 ② 路径 A）。
5. **两尾声明**: 自适应 vs 静态的 rank-IC 差分，两尾、预注册、HAC standard errors。
6. **H6 可复现**: `n_jobs=1`, seeds pinned, version-pinned。

**当且仅当**这 6 条全满足，"自适应"才结构上区别于 rerun-to-significance。任何一条松动（尤其中途改规则、或 OOS 见过才加/删特征）= 退化为 rerun-to-significance。

---

## ⑤ 复盘 Track Adaptive null + 前瞻

### 5.1 null verdict 的可信度（不被 Romano-Wolf × adaptive 缺口削弱）

Track Adaptive 已出 **null**（IC_diff −0.0037，p=0.26，b7621e6b，2026-08-09）。关键统计直觉：

- **多重检验校正保护的是"阳性"判定，不保护"阴性"**。一个 null 结果（CI 跨零）**不会**因为"少做了某一种校正"而变得不可信——校正只会让阳性更难通过（更严），从不让 null 变成假 null。
- 因此：Track Adaptive 的 frozen config §8 只用 DSR/PBO（未显式加 Romano-Wolf step-down）这一"缺口"**不影响 null verdict 的有效性**。即使补上 Romano-Wolf，IC_diff −0.0037 + p=0.26 仍是 null（Romano-Wolf 只会把 p 推得更大，verdict 不变）。
- **结论**: Track Adaptive 的 null **稳健**——与 ① 节文献共识（rolling 重校 OOS 不优于静态）一致，与 GKX 2020 "更新频率非主导" 一致，与 Aionis power floor 一致。这是**第三条独立 null**（Track C climax #49 + Track B #54/track-adaptive + 此处的文献对照），相互强化。

### 5.2 缺口的前瞻价值（仅当未来出现阳性）

② 节的"Romano-Wolf × adaptive 未开垦"只在**未来某个自适应变体出现阳性 IC_diff** 时才成为风险——那时需回答"该阳性在多大 trial 家族下仍显著？" Track Adaptive 用 DSR(1) + PBO 做了第一层（b7621e6b result 含 `dsr_n1` 字段）；若未来 n_trials > 1 的自适应实验出现阳性，应在 analysis 时**追加 Romano-Wolf step-down**（家族 = 所有 trial 的 IC_diff 检验），而非事后改 frozen config。

### 5.3 给未来自适应线的方法学备忘（非 pending 决策）

若业主未来授权**新**的自适应研究线（如 online-GBM 变体、不同 cadence、不同 universe），pre-reg 应：
- 显式声明 multiplicity 家族定义（每个 trial × 每个 cadence 变体 = 家族成员）+ 校正方法（建议 DSR **+** Romano-Wolf 双层，因缺口存在）。
- 预冻结 `n_trials` 上限。
- 两尾 + HAC + H6 不变。

**这不是对 Track Adaptive 的事后修改**（它已 null，不可动），而是对未来同类线的 pre-reg 模板。

### 5.4 与业主既定 framing 的一致性

Track Adaptive null 完全契合 `aionis-publication-framing-option-a`（null + 纪律 + power-limit）。它额外贡献一条：**"更新机制本身也不破 null"**——强化（非削弱）power-floor 结论。业主无需做新决策；此处的 framing 是确认性的。

---

## 限制

- 主会话 WebSearch，未深读全部原文（arxiv 2505.15155、Clarke 2020、Romano-Wolf 2005 仅读 abstract/摘要）。如业主冻结 Step 4 前要更深的原文核验，需逐篇 WebFetch。
- "Romano-Wolf × adaptive 无 landmark paper"基于 WebSearch 检索负结果——可能存在未检索到的工作；冻结前建议由 document-specialist 或人工再核（Google Scholar / SSRN 定向搜）。
- RD-Agent(Q) "2× baseline"来自 NeurIPS poster 摘要，非我独立复现。

**作者**: 主会话（opus，WebSearch 合成；subagent 因 GLM [1210] web-tool 路径失败改主会话）
