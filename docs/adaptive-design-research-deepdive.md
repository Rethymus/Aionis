# 纪律化自适应 A+B 合题：深度证据补强（Step 4 prep）

**状态**: PROPOSED / 研究（未冻结、未决策）。为业主 Step 4（自适应 vs 静态两尾预注册）决策准备的证据补强。
**日期**: 2026-08-11
**方法**: 主会话 WebSearch（subagent web-tool 路径本日因 GLM [1210] 失败，改主会话执行）。引用真实可验证 URL；深度受限处标注。

> 续 `docs/adaptive-design-research.md`（A+B 合题）+ `docs/qlib-reuse-audit.md`。本 doc 不重复既有内容，只补外部证据 + 明确 Step 4 决策门。

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

## ⑤ Step 4 决策建议

**判决**: Step 4 自适应主张**证据上有支撑**（文献弱-中一致支持 rolling 优于静态），**但统计有效性有一未开垦门**（Romano-Wolf × adaptive 无 landmark paper，②）。

**推荐**（待业主裁）:
- **A（推荐）**: Step 4 可行，预注册采用 ②路径 A（保守，把重校点计入 multiplicity 家族）+ ④全部 6 条结构判据。预期仍是 null-favored（power 因家族膨胀下降 → 更难达 significance → 与 Aionis 的 null-发表定位一致）。贡献 = null + 纪律 + "自适应在反泄漏下也未必破 null"的本方法学负面证据。
- **B**: 若业主愿承担方法学论证成本，走 ②路径 B（把 adaptive×RW 当贡献点）——更高 ceiling，更长论证链。
- **C（不推荐）**: 不预声明 multiplicity 处理 → 模糊地带 → 退化为 rerun-to-significance 嫌疑。

**与业主既定 framing 的一致性**: 业主已定帧（memory `aionis-publication-framing-option-a`）= null + 纪律 + power-limit。Step 4 路径 A **完全契合**（null 预期 + 纪律强化 + power-limit 在家族膨胀下更凸显）。路径 B 是 framing(a) 的潜在升级，但非必须。

**下一步业主门**: 业主裁 A/B/C。若 A，则起草 Step 4 预注册（②路径 A + ④6 条）→ 冻结 config sha256 → 才能跑任何真实数据。

---

## 限制

- 主会话 WebSearch，未深读全部原文（arxiv 2505.15155、Clarke 2020、Romano-Wolf 2005 仅读 abstract/摘要）。如业主冻结 Step 4 前要更深的原文核验，需逐篇 WebFetch。
- "Romano-Wolf × adaptive 无 landmark paper"基于 WebSearch 检索负结果——可能存在未检索到的工作；冻结前建议由 document-specialist 或人工再核（Google Scholar / SSRN 定向搜）。
- RD-Agent(Q) "2× baseline"来自 NeurIPS poster 摘要，非我独立复现。

**作者**: 主会话（opus，WebSearch 合成；subagent 因 GLM [1210] web-tool 路径失败改主会话）
