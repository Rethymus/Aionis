# 综合升级方案 — 科学的选股策略研究系统（前沿调研 × 金融理论 × AI 合规贯彻）

> 业主诉求（2026-08-12）：视觉整体排查 + 深入调研前沿项目与研究设计 + 金融学×市场研究理论联动
> + 深入贯彻 AI 能力 + 最终实现高质量符合科学的选股策略研究系统。
>
> 本文档 = 调研结论 + 理论锚定 + 合规路径 + 执行清单。**PROPOSED → 立即执行 display 层**。
> 约束（不可妥协）：反泄漏（CLAUDE.md）、null-favored（memory `aionis-publication-framing-option-a`：
> 勿追 alpha、勿拓宽 SESOI）、LLM 入 OOS = 已知泄漏（见 §3）。

## 1. 视觉整体排查结论（puppeteer DOM 实测，3 页 + 源码全扫）

| 项 | 发现 | 严重度 | 处置 |
|---|---|---|---|
| `/confirmation` 水平溢出 | 1421px > 1280px 视口，内容右沿 1372px；sidebar+main 未约束 | 真 bug（pre-existing，非本轮引入） | **立即修**：main 容器 `max-w` + 表格 `overflow-x-auto` |
| Guard 页 `/discipline` 无高亮守卫标 | SegmentHeader 在 guard 页不显 guard chip（条件 `segment !== "guard"`） | UX 缺口 | **立即修**：guard 页高亮 guard 段 |
| 论证链卡片 desc 用 `truncate` | 移动端长 title（"估计量·模型…"）可能截断 | 轻微 | **立即修**：改 `line-clamp-2` |
| Overview verdict 卡 title=`evidence.role` | "裁决 · 研究结论是什么？" 作卡片 title 略别扭 | 轻微 | **立即修**：用段名短 label |
| `/themes`·`/picks`·`/track` DOM | α 词正确、面包屑高亮正确、provenance 实显 | ✅ 无问题 | — |
| 源码全扫 funnel/七主题/闭环 | 0 真命中 | ✅ 无残留 | — |

## 2. 前沿调研（巨人，主会话核源）

### 2.1 Agentic AI 因子发现闭环（Fan 2026 arXiv 2603.14288）— 可复用方法学
**闭环 C_k**：H_k(假设) →Gen→ F_k(因子) →Eval→ M_k(rank-IC t, LS Sharpe) →Gate→ D_k(promote/hold/retire)。
- **constrained autonomy**：固定变量宇宙 + 有界表达式复杂度 + 严格 no-look-ahead。
- **IS/OOS 严格分离**：promotion gate 只用 IS，OOS 是 blind test（max(T_IS)<min(T_OOS)）。
- **economic rationale 必须**（ReAct: reasoning trace r_t 先于 action a_t）= 经济正则化抗 p-hacking。
- **multi-objective gate**（IC + LS Sharpe + turnover + 信息冗余）= Deflated Sharpe Ratio 启发式代理。
- **symbolic regression**：透明可审计因子公式。
- **截面 z-score/winsorize date-by-date**；时序算子 only up-to-date（与 Aionis PIT 一致）。

⚠️ **警示（勿照搬结果）**：Fan 报 Sharpe 3.11 / 年化 59.53% / 16 季度全正——与 Aionis ledger #49
**NULL**（IC −0.0088, p=0.484）尖锐对比。Aionis null 是反泄漏诚实结果；Fan 数字极可能含隐性
multiple-testing 或 IS/OOS 软分隔。**复用方法学框架，不追其 alpha。**

### 2.2 LLM look-ahead bias 文献群（2024-2026，关键约束）
ChronoBERT（He 2025 arXiv 2502.21206）/ Look-Ahead-Bench（HAL 2025）/ DatedGPT（AFA 2025）/
"Lookahead Bias in Pretrained LMs"（SSRN 4754678）：**LLM 预训练语料含未来信息 = 已知泄漏通道**。
→ **memory `aionis-erl-leakage-design`（ERL structural-only）+ `aionis-edgar-efts-sc13d-frozen` 已印证**。
**判定：任何 LLM 特征进冻结 OOS = 泄漏，禁。** AI 贯彻须在 OOS 外。

### 2.3 资产定价理论锚（与 Aionis 同构，非新追 alpha）
- Harvey-Liu-Zhu (2016 RFS) "…and the cross-section"：t>3.0 多重检验门槛（Aionis 用 HAC + J-T + power floor）。
- Harvey-Liu (2020 JF) "False/Missed discoveries"；Harvey-Liu (2021 JFE) "Lucky factors" + Scaled Intercept。
- López de Prado (2018) Deflated Sharpe Ratio / False Strategy Theorem（Aionis memory `aionis-finsaber-backtrader-gpl` 已引）。
- Gu-Kelly-Xiu (2020 RFS) ML asset pricing（LightGBM = Aionis 冻结 learner）；Kelly-Xiu (2023) Fin ML survey。
- Kelly-Pruitt-Su（IPCA，Aionis conviction 已用 dispersion 方法）。
**结论：Aionis 的 null + power-floor 披露 = 这些文献的标准诚实做法，非缺陷。**

## 3. 金融理论 × 市场研究理论 × AI 的合规贯彻路径

**核心原则**：AI 作**研究助手**（exploratory/hypothesis/文献/归因），**绝不**进冻结 OOS 造 alpha。
每个 AI 生成的候选因子 = 新预注册 + 新 config_committed ledger 行 + 独立 OOS，非 silently 改冻结面。

### 三条 AI 贯彻轨道（合规分层）

| 轨道 | AI 角色 | 接触 OOS？ | 复用 Fan 方法 | Aionis 新增工作量 |
|---|---|---|---|---|
| **A. 因子假设生成器**（exploratory） | LLM 生成经济可解释因子公式 + rationale（ReAct r_t 先于 a_t） | **否**（仅 IS 候选池，promote 需新预注册） | §2.1 闭环前半 | 接 GLM/SiliconFlow router（已有 `extraction/providers.py`） |
| **B. 归因/解释助手**（display-only） | LLM 给当前 null 一个经济叙事（"为何 IC≈0"），不生成预测 | **否**（只读已冻结结果） | — | 终端新增"AI 归因"卡（display） |
| **C. 文献/异常地图**（display-only） | LLM 维护"factor zoo"已知异常 vs Aionis 测过的，标覆盖缺口 | **否** | — | 终端新增"覆盖地图"（display） |

**禁止轨道（明确）**：LLM 特征直接进 LightGBM OOS panel = 泄漏（§2.2）。Track LLM（memory
`aionis-tcr-theory-pivot`）若要复活，必须 (1) 新预注册 (2) frozen 截止日后才见 OOS (3) 独立 ledger 行。

## 4. 立即执行（display 层，本轮交付）

### Phase D1 — 视觉 bug 修复（§1 表，tsc+build 验）
1. `/confirmation` 溢出修：main 容器约束 + smart-money 表 `overflow-x-auto`。
2. Guard 页高亮守卫段（SegmentHeader `segment==="guard"` 时显 guard 高亮）。
3. ArgumentChainDiagram desc `truncate` → `line-clamp-2`。
4. Overview verdict 卡 title 用段名短 label（非 `evidence.role`）。

### Phase D2 — AI 研究助手层（display-only，轨道 B 先行，低风险高可见）
新增 `/track` 下 "AI 归因" 卡：读**已冻结** null 结果（ledger #49 IC/p/CI），LLM 生成一段经济叙事
（"为何此主张 null：噪声地板 σ≈0.106 >> SESOI 0.010；IC CI 跨零；power floor 不可达"）。
**display-only，不写 ledger，不进 OOS，不生成预测**。复用 `extraction/providers.py` GLM router。

### Phase D3 —（待业主门，本轮不启）
轨道 A 因子生成器（需新预注册 + config freeze，owner-GO 门）；轨道 C 覆盖地图（需 factor zoo 数据集）。

## 5. 边界与诚实标注
- 本文档：纯 `reports/design/` + memory；0 ledger/frozen/config/OOS 改动。
- 调研在主会话（规避 [1210]）；源：Fan 2026 arXiv、ChronoBERT、Look-Ahead-Bench、DatedGPT、HLZ/HL/LdP/GKX/KX。
- D2 的 LLM 归因调用 = 外发（GLM API），但**只读已公开冻结结果**生成叙事，非外发未公开数据；
  仍按 `aionis-owner-process-correction`：外发不可逆动作前确认——D2 实施前我会再向业主确认 LLM 调用。
- **不追 alpha**（memory `aionis-publication-framing-option-a`）：本方案强化 null 披露与反泄漏，
  不拓宽 SESOI、不救 equivalence、不追新 alpha 信号。
