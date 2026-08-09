# Track LLM 预注册 — EDGAR-10-K LLM filings-tone 作为第 42 列（PROPOSED，未冻结）

> **状态：PROPOSED — 未冻结。** 在 owner 审阅 + `config_committed`（sha256 入 ledger）之前，
> **禁止**在任何 OOS 数据上跑 LLM 增强估计量、禁止做 prompt/filing-type/scalar 变体实验。
> 这是反泄漏硬锚（`config_committed BEFORE result`）。Phase-0 可行性已证（见 §0）。
>
> **证据背书**：[`reports/design/2026-08-09-track-llm-feasibility-pilot.md`](../reports/design/2026-08-09-track-llm-feasibility-pilot.md)
> — G1 CIK 解析 100%（OOS 窗口 533/533）+ G2 token 投影 ~11.71M（一次性）。两本地门 GREEN。
>
> **命名澄清**：本 "Track LLM" 与既有 **Track B（七主题平台）/ Track C（确认性）/ Track Adaptive**（均 FROZEN）无关。
> 与 memory `aionis-publication-framing-option-a` 的"勿追新 alpha"锁的关系：类比 Track Adaptive 的
> 2026-08-08 addendum——owner 显式授权**仅限**"EDGAR-filings 单变量、1 trial、DSR-干净、与冻结面硬隔离"
> 的纪律化路径；**无纪律的 prompt-sweep / 多源文本 alpha-chasing 仍禁**。

## 0. Phase-0 可行性（已证，本地门 GREEN）

- **G1 CIK 解析**：US OOS 窗口 2021-2026，533 distinct tickers，**100% 解析**到 SEC CIK。cik_resolver 的 ~60% gap
  是**历史全宇宙**（1996-2025）问题，OOS 窗口不绑定。
- **G2 token 成本**：~5576 filings（OOS 2911 + train 2665）× 2100 tok ≈ **11.71M token，一次性**（idempotent accession-keyed cache）。
- **待 owner（需凭证）**：G3 真实 per-call token 校准 + G4 temp=0 稳定性（`--measure-llm N`）。

## 1. 单一可证伪 claim（两尾、预注册、**null-expected**）

**H0（两尾）**：在 frozen Track-C 41 列 learner 上加一列 `llm_filings_tone`（EDGAR 10-K MD&A 抽取的 scalar tone，
filed-date PIT + embargo 21 sessions），月频截面 rank-IC 与 **41 列 frozen 基线无可靠差异**。

- 估计量：`IC_diff = mean(IC_{41+LLM}) − mean(IC_{41-frozen})`，月频，配对/月，HAC SE，两尾。
- 方向：**两尾**（LLM 信号可能改善 *或* 恶化 IC；不接受单方向救场）。
- **诚实预期 = null**：power floor σ(IC)≈0.10 对任何月频截面信号封顶；LLM 在已有 41 特征之上的**边际 IC** 通常小
  （噪声文本信号）；但这是项目里唯一有非平凡正概率的方向（2024-2025 文献 OOS alpha 实证 + filings-text 与价格/基本面正交）。
- **价值定位**：null = 第三条独立 null（月频 #49 / 周频 #54 / LLM），**强化** power-floor 论证，非削弱。

### 1.1 为何不是"追新 alpha / 救 equivalence"

Track C climax（#49 null）与 Track Adaptive（#54 null）已坐实。Track LLM 不"救"它们——它问一个**新问题**：
"正交的文本信号能否在地板上加 IC？" 若 IC_diff CI 跨零（预期），则"LLM filings-tone 无增量"成为**第三条独立 null**。
单一新特征 = 单一 treatment 变量 = 1 trial = DSR 平凡通过。这不是 prompt-sweep fishing。

## 2. Universe（复用 Track C PIT，US-only for v1）

- 复用 Track C 的 PIT US S&P 500 universe（`constituents_on`），保证与 frozen 基线**同 universe**（干净配对）。
- **US-only**：CN filings 是不同制度（16-K 等价物），v1 不扩展 CN 臂。CN OOS 不被 Track LLM v1 触及。
- OOS 窗口与 Track C 对齐（71 月 OOS，与 IC_frozen 配对）。

## 3. Features（复用冻结 41 列 + **1 新列**——隔离"LLM 信号"单一变量）

- 复用 Track C frozen config #48 的 41 列（US 23 + CN 12 + macro 6 + regime 3）。**零改动**。
- **唯一新增**：`llm_filings_tone`（§4 构造）。**禁止**借 Track LLM 加其他特征/换 learner——那会混淆变量。

## 4. LLM 信号构造（**Track LLM 的 treatment 变量；冻结前定死**）

- **来源**：SEC EDGAR **10-K 的 MD&A 段**（filed-date PIT，SEC 公共域、不修订）。**禁**新闻/社媒（forward-only，回测不了）。
- **选择规则**：对每个 `(ticker, month_end T)`，取 `filed_date ∈ [T − lookback_12m, T − embargo_21sessions]` 内**最近一次** 10-K；
  窗口内无 → NaN；窗口内 forward-fill（一次 filing 的 tone 持续到下次 supersedes）。
- **抽取 prompt（冻结）**：固定系统提示 + MD&A excerpt（截断 ≤ `excerpt_max_tokens`）+ `temperature=0`（greedy）+ pinned model version。
- **scalar 推导（冻结公式）**：GLM 输出结构化 JSON `{bullish: 0-1, bearish: 0-1}` → `llm_filings_tone = clip(bullish − bearish, −1, +1)`。
- **反泄漏**：filed-date PIT + embargo 防 outcome 泄漏；prompt 冻结防"换 prompt 追 IC"（DSR/PBO 抓）。
- **冗余检查**：建好特征后**冻结前**算 `llm_filings_tone` 与既有 momentum/volatility 列的 Spearman 相关 → 写进 prereg。
  若 |ρ| > 0.8 → 诚实标注"大概率冗余"（仍跑，null 也是结论）。

## 5. Learner（复用冻结 LightGBM——零改动）

- LightGBM lambdarank，**与 Track C #48 完全相同超参**。唯一变化：特征数 41 → 42。
- 不调超参、不换 objective（避免混淆"新特征"与"新模型"两个变量）。

## 6. Validation（chronological walk-forward，配对）

- chronological walk-forward；IC_{41+LLM} 与 IC_{41-frozen} 在**同一 OOS 月、同 universe** 上配对。
- 配对差 `d_t = IC_{41+LLM,t} − IC_{frozen,t}`；HAC 回归 `d_t ~ 1`（Newey-West）给 mean + SE + CI。

## 7. Horizon

月频。OOS 月数 = Track C 的 71 月（配对）。

## 8. SESOI / 门（两尾，**显式 null-expected**）

- **主门（significance，两尾）**：`|mean(IC_diff)| / SE_hac` 的 HAC p-value；α = 0.05 两尾。预期不拒绝 H0（null）。
- **次门（equivalence，若 null）**：IC_diff 的 RCI 是否落在 ±SESOI_diff 内（复用 ±0.010 或基于 IC_diff 实证 σ）。
- **禁止**：主门不显著就"降级"宣等价救场（rerun-to-significance 禁）。两门都预注册在前。

## 9. Multiplicity（**n_trials = 1**——Track LLM 的纪律核心）

- **1 trial**：一个新特征、一个 estimand、一个 prompt、一个 filing type。DSR 平凡通过（N=1），PBO 不需要。
- **反多重检验硬规则**：任何变体（换 prompt / 加 8-K / 换 scalar 公式 / 换 excerpt 段）= **新 `config_committed` 行**，
  绝不静默改。这把"追 alpha"边界划清：一次预注册、一个新特征。

## 10. Baseline（冻结 Track-C #48 learner 作为比较器）

- 比较器 = Track C frozen #48 learner（41 列）在同 OOS 窗口的 IC 序列（`IC_frozen`，bit-identical 复现）。

## 11. H6 确定性（cache-pin 契约）

- LLM 非确定，但 **idempotent accession-keyed cache（key = accession + model_version + prompt_hash）** 把首次抽取值钉死 →
  研究相（跑 OOS）**只读 cache** → IC bit-identical。`temperature=0` + pinned version 压抽取相方差。
- **诚实披露（写进 config）**：H6 对**研究相**成立（纯 cache 读）；**抽取相**是一次性、cache 后冻结，不重跑。
  与项目既有 idempotent-cache 契约（Option A）一致。

## 12. frozen config（**待 owner `config_committed` 冻结**）

预指定（冻结前定，无 outcome 选择）：
- estimand: `IC_diff = mean(IC_{41+LLM}) − mean(IC_{41-frozen})`，HAC，两尾。
- universe（US S&P 500 PIT，D1）+ OOS 窗口（与 Track C 配对）。
- feature_cols = Track C #48 的 41 列 + `llm_filings_tone`（**仅此 1 列新增**）。
- 抽取 spec：filing type（D2）/ excerpt 长度（D3）/ prompt（冻结）/ scalar 公式（D4）/ model+temp（D5）。
- purge+embargo（复用 Track C，embargo=21 sessions）。
- SESOI_diff（次门）。
- H6 cache-pin 契约 + version pin。
- **cost-gate**：G3/G4 校准后的真实 per-call token + 总成本，freeze 进 config（超预算 → 缩 scope 再冻）。

`config_committed` 行写入 `runs/ledger.jsonl` **后**才允许首次抽取 + OOS 跑。

## 13. 显式 non-goals

- **不**做 prompt-sweep / 多源文本（news/社媒）——DSR/PBO 与 framing 锁双禁。
- **不**修改 Track C / Track Adaptive / Track B(seven-theme) / D / E1 任一冻结面。
- **不**在 OOS 窗口内调超参追 IC。
- **不**把 LLM 信号输出喂进**研究管线**的 confirmatory 估计量（Track LLM 是独立估计量）。
- **不**扩展 CN（v1 US-only）。
- **不**启用 E3 / forward ledger。

## 14. stacking(C) 条件触发（**仅当 D 显示信号**）

- **trigger（冻结进 prereg）**：**仅当** §8 主门 IC_diff 的 HAC CI **不跨零**（LLM 列显示出可靠正边际 IC）→ 才开
  Track Stacking（Bayesian/stacking over {41-col learner, LLM-only learner}，walk-forward 权重，新 prereg）。
- **否则跳过 C**，结论 = "filings-tone 未突破 power floor"。这避免"先做近乎必 null 的纯 C"的浪费。

## 15. owner-decision 点（**PROPOSED，待裁断**）

- **D1**：universe = US S&P 500 PIT（默认）/ 缩到 S&P 100（若 G3 成本超预算）？
- **D2**：filing type = 10-K MD&A only（默认）/ +8-K item 2.02 / +10-Q（sensitivity 臂，各 = 新 ledger 行）？
- **D3**：excerpt 长度 = ≤2000 tok（默认）/ 其他？
- **D4**：scalar 公式 = `clip(bullish − bearish, −1, +1)`（默认）/ 其他？
- **D5**：model + temp = GLM-flash（或 router）+ temperature=0？
- **D6**：G3/G4 校准后，总成本可接受？→ 审 prereg → `config_committed` 冻结 → 首次抽取 + OOS。

## 16. 不越界声明（PROPOSED，未冻结）

本轮纯新建 `docs/track-llm-preregistration.md`（PROPOSED）+
`scripts/track_llm_feasibility_pilot.py`（+ tests，本地 G1+G2 可行性工具）+
`reports/design/2026-08-09-track-llm-feasibility-pilot.md` + state；**0 ledger / frozen / prereg-freeze / ADR / config / OOS 产物 / E3** 改动；
未跑任何 LLM 增强估计量；未观察任何 Track LLM OOS metric；未做任何 GLM API 调用（G3/G4 待 owner 凭证）；
Track C / Track Adaptive / Track B 冻结面完全未触。

## 17. 引用

- Gu-Kelly-Xiu 2020 (RFS) — 月 OOS R² 1.08–1.80%；"模型类 > 更新频率"（边际 IC 小的先例）。
- Loughran-McDonald financial sentiment — filings-text 信号的方法学先例（可作 prompt 设计参考，非依赖）。
- [Testing LLM-Generated Factors (2000-2024)](https://www.researchgate.net/publication/396995973) ·
  [MarketSenseAI (SSRN)](https://papers.ssrn.com/sol3/Delivery.cfm/6607760.pdf?abstractid=6607760) ·
  [LLM disclosure alpha (arXiv 2510.03195)](https://arxiv.org/html/2510.03195v5) — LLM 文本因子 OOS alpha 实证。
- [AFA — LLM 过外推近期收益](https://afajof.org/management/viewp.php?n=170324) — 过外推风险（§4 冗余检查的动机）。
- `decisions/ADR-010-sesoi-tost-sequential-gate.md` — SESOI/J-T 门（精神复用）。
- `docs/track-adaptive-preregistration.md` — 预注册模板（结构复用）。
- `src/aionis/ingest/cik_resolver.py` — CIK 解析（G1 工具）+ 已知历史 gap（§0 澄清）。
- `reports/design/2026-08-09-track-llm-feasibility-pilot.md` — Phase-0 证据。
