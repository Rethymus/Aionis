# RES-02 — Strong baseline ladder: FF5 + DFF macro features (S; owner-gated)

- 编号: RES-02
- 状态: **REWRITTEN 2026-08-03 — cross-sectional-valid; ready for owner authorization**
- Priority: **P2**（审计 §11 P2 后续研究方向；§4.2 基线不足）
- Size: **S**（单个特征族添加；2-3 周工作量）
- Risk: **MEDIUM**（新增特征但仅探索性；不触碰 frozen B/C/D/E1 结果）
- 建议 agent role / model tier: **Engineer (Sonnet) → Verifier (Sonnet) → Reviewer (Opus)**

## 目标 + 为什么重要

> 2026-08-01 planning correction + 2026-08-03 rewrite（`tasks/active/TASK-ORCH-RES-02-rewrite-ff5.md`）：
> 原始月度 FF5/DFF 因子值是**市场-wide 时间序列**——同一月内对每只股票取值相同（横截面无差异），
> 无法直接对横截面排名，rank-IC 估计算子因此不可用。本 spec 已将特征列改为**股票特定滚动
> 暴露 / 交互**设计（rolling beta-to-factor + 因子载荷 × 个股特征交互），使 baseline 可横截面排名。
> 重写后的实施要求显式包含：**PIT 证明（无同月未来使用）**、**`TASK-RD-13` 横截面变异护栏**、
> **French 数据 7-gate 准入**（`docs/data-intake-rubric.md`）。

**目标**：在 Aionis 现有九列基本面基线（mktcap/pb_ratio/roa + 六项基本面）基础上，增加
**股票特定的 Fama-French 5 因子滚动暴露与交互特征**（rolling beta-to-factor + 因子载荷 ×
个股特征交互）以及 **DFF（联邦基金有效利率）的股票特定利率暴露**，形成一个新的 baseline
config，注册为 **BASELINE-FF5-001**。所有新增特征列均为**股票特定、月内横截面可变**——
**绝不再**把市场-wide 的原始月度因子列（MKTRF/SMB/HML/RMW/CMA/DFF）作为特征列。

**为什么重要**（审计发现）：
- 审计 §4.2：frozen `feature_cols` 只有 mktcap/pb_ratio/roa 和六项基本面，但 [phase-b-preregistration.md](../../docs/phase-b-preregistration.md) §2 描述两臂应共享 momentum/reversal/vol、**FF5 和 DFF 宏观** — **这些特征从未进入 headline config**。
- 审计 §8.1：Gu, Kelly, Xiu (2018) GKX-94 特征包含 FF5；当前弱基线使 differential 结论**无法外推到包含 FF5 的环境**。
- 审计 §11 P2："[D] 新 config/new ledger row 才可加入强数值基线；不静默修改旧结果。"

## 特征设计（横截面可排名——本任务的核心变更）

**原始缺陷**：MKTRF/SMB/HML/RMW/CMA/DFF 是市场-wide 时间序列，月内每只股票取值相同
（RD-13 诊断必为 CONSTANT）→ 零横截面区分度 → 无法 rank-IC。

**替换设计**（全部股票特定、月内横截面可变，与 frozen panel 的预测日期约定一致：
月末计算、下月首个交易日可知）：

### A. 滚动因子暴露（rolling beta-to-factor，6 列）

- 对每只股票 i、每个月末 t：用**日频**数据在**截至 t 的最近 252 个交易日**（min_periods=126）
  滚动 OLS（或 cov/var 闭式解）：
  `r_i,d − RF_d = α + Σ_k β_k · F_k,d + ε`
- 产出 `beta_mkt`、`beta_smb`、`beta_hml`、`beta_rmw`、`beta_cma`（FF5 日频因子，
  Fama-French 2015 定义；与 `src/aionis/eval/ff5_residual.py` 因子集一致）。
- `beta_dff`：同一窗口内股票日收益对 ΔDFF（ALFRED as-of 日频序列的日变化）的滚动敏感性。

### B. 因子载荷 × 个股特征交互（5 列）

- `beta_smb_x_size` = beta_smb × ln(mktcap)（规模载荷 × 规模特征）
- `beta_hml_x_value` = beta_hml × pb_ratio（价值载荷 × 价值特征）
- `beta_rmw_x_prof` = beta_rmw × roa（盈利载荷 × 盈利特征）
- `beta_cma_x_invest` = beta_cma × Δfund_assets/fund_assets（投资载荷 × 资产增长；
  filed-date 对齐的连续两次 filings 计算，PIT）
- `beta_dff_x_lev` = beta_dff × (fund_long_term_debt / fund_assets)（利率敏感 × 杠杆）

特征族合计 11 列，叠加 frozen 九列 → 20 列 config。窗口数据不足（<126 obs）→ NaN，
交给 LightGBM missing 策略（RD-15 §5）；收益缺值的样本不进入排名（RD-15 missing policy）。

### PIT 证明（无同月未来使用——必须显式满足）

1. **知识时点（knowledge date）**：所有特征输入只使用 ≤ 月末 t 最后交易日的观测——日收益、
   FF5 日频因子值、DFF as-of 值。FF5 日频文件按日更新（d 日值在 d+1 起可知；实际发布延迟
   以获取时的文件时间戳核实并记入 intake 记录 G2）。月 t 末计算的特征最早在 t+1 首个交易日
   可知 → **绝无同月未来使用**。
2. **DFF 用 ALFRED vintage as-of join**（`merge_asof(..., allow_exact_matches=False)`，
   与 `src/aionis/features/macro_surprise.py` 同模式）——绝不使用当前修订序列。
3. **基本面 filed-date PIT**（现有 `src/aionis/ingest/fundamentals.py:pit_align` 机制）。
4. **快照不可变（H6）**：首次获取的 FF5/DFF 快照落 `data/cache/` + sha256；rerun 只读快照
   （零 HTTP，bit-identical）；上游修订 = 新快照 + **新 ledger 行**，绝不静默覆盖（G3/G4）。
5. **可测不变量**（单元测试断言）：future-truncation invariance（删去 t 之后的数据，
   特征值不变）；knowledge-date 断言（预测日 t 的特征不依赖任何 >t 观测）；快照 sha256 断言。

### RD-13 横截面变异护栏（必须通过）

- 每个新增特征列按月跑 `src/aionis/features/diagnostics.py`（RD-13，已 COMPLETE）；
  月内 CONSTANT / NEAR_CONSTANT / ALL_MISSING / FEW_VALID → **fail closed**（该列不得进入
  config，reason code 记入 trial registry）。
- 市场-wide 原始因子列按构造即为月内 CONSTANT → **结构性不合格**，不参与候选；
  RD-13 明示 macro 输入只允许走 interaction 路径。
- 交互特征中的因子侧与特征侧分别诊断；交互后仍无截面变异的组合不进入 config。

### French 数据 7-gate 准入（必须显式完成）

按 `docs/data-intake-rubric.md` 落表 `docs/data-intake-french-ff5.md`（新建）：

- **G1（license）**：French Data Library = 免费学术使用，**不在** MIT/Apache/BSD/CC0/CC-BY-4.0
  白名单 → 落表记录 + **owner 签注**；该限制使 FF5 侧特征**仅 exploratory**，绝不 confirmatory。
- **G2（PIT）**：日频因子文件带发布日（d 日值 d+1 起可知）→ 可构造 as-of 时点 ✓。
- **G3（no-revision）**：French **不发布 vintage**，历史值可能被修订 → **不可证** →
  快照冻结 + sha256 + exploratory（与 `ff5_residual.py` 的 leakage 注记一致）。
- **G4（可复现）**：快照 + sha256 + source-URL + fetch-ts 入 ledger。
- **G5（exploratory-only）**：trial `mode: exploratory`，不进 headline。
- **G6（selection-honesty）**：FF5 是组合级因子（市值/等权组合收益差），非个股级 → 声明为
  scope 限制；交互特征的经济解释不扩大为因果声明。
- **G7（politeness）**：bulk ZIP 单次获取 + `≥2s` 间隔 + 有界退避 + fail closed。

DFF 走 FRED/ALFRED：US 政府公共领域（G1 ✓）、vintage 不可回改（G3 ✓）——与
`data-intake-rubric.md` 中 VIX 行同路径，无需额外许可签注。

## 必须注册的新 trial

此任务完成后必须创建一个新的 trial registry entry：

```yaml
trial_id: BASELINE-FF5-001
trial_family: baseline-ladder
type: exploratory-baseline-enhancement
primary_parent: "frozen Phase B (numeric fundamentals)"
config_sig: <sha256 of the new config file>
feature_addition:
  - beta_mkt: rolling market-excess exposure (252d trailing daily OLS, min 126 obs)
  - beta_smb: rolling SMB factor exposure (同窗口)
  - beta_hml: rolling HML factor exposure (同窗口)
  - beta_rmw: rolling RMW factor exposure (同窗口)
  - beta_cma: rolling CMA factor exposure (同窗口)
  - beta_dff: rolling short-rate (ΔDFF) exposure (ALFRED as-of)
  - beta_smb_x_size: SMB loading × ln(mktcap)
  - beta_hml_x_value: HML loading × pb_ratio
  - beta_rmw_x_prof: RMW loading × roa
  - beta_cma_x_invest: CMA loading × Δfund_assets/fund_assets
  - beta_dff_x_lev: ΔDFF exposure × (fund_long_term_debt / fund_assets)
objective: "regression" (保持与 B/C/D/E1 一致)
universe: "588 clean ticker PIT" (与 frozen 相同)
n_jobs: 1
random_seed: 0
h6_determinism: true
mode: "exploratory" (FF5 G3 不可证 → 快照冻结 + exploratory；DFF via ALFRED 为 confirmatory-tier)
rd13_gate: "all feature cols pass per-month variation diagnostics (no CONSTANT/NEAR_CONSTANT/ALL_MISSING/FEW_VALID)"
status: "pending-owner-authorization"
registered_at: <timestamp of owner GO>
```

**关键约束**：此 trial 是**新的 exploratory 基线增强**，必须由 owner 明确授权后才可写入
`runs/ledger.jsonl`。不得使用此 trial 静默修改 B/C/D/E1 的任何结果。

## 允许修改的文件

仅限以下文件的新增或修改：
- `src/aionis/ingest/ff5.py`（新建：FF5 **日频**因子获取 + 快照/sha256；复用
  `src/aionis/eval/ff5_residual.py` 的 fetch/parse 模式）
- `src/aionis/ingest/macro_dff.py`（新建：DFF ALFRED vintage 获取；或扩展现有 macro_surprise.py）
- `src/aionis/features/ff5.py`（新建：滚动暴露 + 交互特征构造）
- `scripts/phase_b_fetch.py`（如需添加 FF5/DFF fetch；保持 politeness ≥2s）
- `scripts/res_02_baseline_ff5_run.py`（新建 RES-02 专用 runner）
- `tests/test_ff5_ingest.py`、`tests/test_macro_dff.py`、`tests/test_ff5_exposures.py`（新建单元测试）
- `config/baseline_ff5_001.yaml`（新建配置文件，记录特征列）
- `docs/data-intake-french-ff5.md`（新建：7-gate 落表 + owner 签注）
- `docs/baseline-ladder.md`（新建并更新：FF5/DFF 数据源、PIT、特征设计）
- `.omc/plans/plan-res-02.md`（可选：实施计划草稿）

## 禁止修改的文件（绝对禁止）

- `runs/ledger.jsonl`（禁止写入；必须由 owner 在授权后独立写入新 trial row）
- `docs/phase-*-preregistration.md`（禁止修改 frozen pre-registration）
- `decisions/ADR-*.md`（禁止修改 ADR）
- `src/aionis/eval/learner.py`（禁止修改 frozen LightGBM 配置）
- `scripts/phase_{b,c,d,e1}_run.py`（禁止修改 frozen runner）
- `src/aionis/features/diagnostics.py`（RD-13 已 COMPLETE；只读调用，不修改）
- `src/aionis/eval/ff5_residual.py`（现有 track_b 探索工具；只读复用模式，不修改）
- `data/**`、`runs/results/**`（禁止触碰任何数据或结果）
- `state/current.md`、`state/handoff.md`（仅 Orchestrator 可更新；本任务不触碰）

## 前置条件（owner gate）

此任务在以下条件**全部满足**前必须保持 HOLD：
1. **Owner 明确书面授权**（state/handoff 或单独决策文档）：允许启动 BASELINE-FF5-001 trial
   （按本 spec 的股票特定滚动暴露/交互设计）。
2. **7-gate intake 落表 + owner 签注**：`docs/data-intake-french-ff5.md` 中 G1（免费学术使用、
   非白名单许可）与 G3（无 vintage → 快照冻结）的判定被 owner 接受。
3. **ADR-010 冻结已生效**（已满足，ADR-010 2026-07-31 accepted）。
4. **AUD-00 全部 P0 任务 COMPLETE**（当前部分完成；需等 AUD-01~05A APPROVE）。
5. **RES-01 可并行**：RES-01 和 RES-02 可并行启动（文件不重叠）。

## 实施要求

### Engineer 职责（S 长度；2-3 周）
1. **FF5 数据获取**（**日频**；月频仅作交叉核对）：
   - 从 **French 数据库官方** bulk ZIP 获取 FF5 日频因子（`F-F_Research_Data_5_Factors_2x3_daily_CSV.zip`
     命名模式；实际 URL/文件名以获取时为准并记入 intake 记录 G4）。复用
     `src/aionis/eval/ff5_residual.py` 的 fetch/parse 模式。
   - **Politeness**：强制 `≥2s` 间隔；有界退避；失败时 fail closed。
   - **快照 + sha256**：首次获取即冻结（G3/G4）；rerun 只读快照（H6）。
2. **DFF 宏观获取**：FRED（ALFRED）`DFF` 日频序列，**vintage as-of join**
   （参考 `src/aionis/features/macro_surprise.py` 的 ALFRED 模式）；绝不使用当前修订后的序列。
3. **特征映射**（`src/aionis/features/ff5.py`）：
   - 滚动暴露：每只股票、每个月末，252 交易日窗口（min_periods=126）滚动 OLS/cov-var
     `r_i,d − RF_d = α + Σ_k β_k·F_k,d + ε` → beta_mkt/smb/hml/rmw/cma/dff（确定性计算，n_jobs=1）。
   - 交互：上文 B 节 5 个交互列；个股特征一律用 filed-date 对齐的最新值（PIT）。
   - 输出 `(month, ticker)` 面板，与 frozen panel 对齐。
4. **RD-13 gate**：对每个新增列按月跑 `src/aionis/features/diagnostics.py`；
   CONSTANT/NEAR_CONSTANT/ALL_MISSING/FEW_VALID → fail closed（该列不入 config，
   reason code 记入 registry）。
5. **PIT 不变量测试**：future-truncation invariance、knowledge-date 断言、快照 sha256 断言。
6. **配置文件**：`config/baseline_ff5_001.yaml` = frozen 九列 + 通过 RD-13 的新列。
7. **Runner 脚本**：`scripts/res_02_baseline_ff5_run.py` 只运行 **purged cross-fitted CV**
   （与 frozen B/C/D/E1 同等证据强度）。
8. **单元测试**：`test_ff5_ingest.py`（礼貌性、快照不变、PIT）、`test_macro_dff.py`
   （ALFRED vintage 正确性、PIT）、`test_ff5_exposures.py`（滚动窗口边界、交互列手算 fixture、
   RD-13 诊断 verdict、future-truncation）。
9. **文档**：`docs/baseline-ladder.md`（数据源、PIT、特征设计）；`docs/data-intake-french-ff5.md`
   （7-gate 落表）。

### Verifier 职责（只读证据收集）
1. **7-gate intake 复核**：`docs/data-intake-french-ff5.md` 的 G1~G7 判定与证据一致；
   owner 签注存在。DFF 来自 FRED/ALFRED；**禁止** yfinance/Stooq/BLS。
2. **Politeness 检查**：审查 fetch 代码是否强制 `≥2s` 间隔；是否有退避机制。
3. **PIT 不变性**：
   - FF5：确认发布日（d+1 可知）纪律 + 快照冻结；无同月未来使用。
   - DFF：确认使用 ALFRED vintages；禁止使用当前修订后的序列。
4. **RD-13 输出**：每个新列的 per-month 诊断 verdict 均非 CONSTANT/NEAR_CONSTANT/
   ALL_MISSING/FEW_VALID；config 中**不存在**市场-wide 原始因子列。
5. **配置隔离**：确认 `config/baseline_ff5_001.yaml` 是**新文件**。
6. **禁用确认**：`git diff --name-only` → **禁止**出现 `runs/ledger.jsonl`、frozen 文件。

### Reviewer 职责（diff + 风险评估）
1. **FF5 文献对齐**：核实滚动暴露估计与 Fama-French (2015) 因子定义一致；窗口/最小观测数
   的经济合理性。
2. **DFF PIT 合规**：确认 DFF 使用 ALFRED vintages；**禁止**使用当前修订序列（leakage）。
3. **数据源许可**：French 数据库为免费学术使用（非白名单许可）→ 确认 intake 记录 + exploratory
   tier 判定正确；DFF 走 FRED 公共领域路径。
4. **交互设计**：因子载荷 × 特征交互的经济解释成立、无同月未来使用（filed-date + as-of）。
5. **不碰结果**：确认没有任何代码读取或写入 `runs/results/**`、`data/**`。
6. **owner gate 检查**：确认 owner 已明确授权 BASELINE-FF5-001 trial（含 intake 签注）。
7. **trial registry 准备**：验收时必须准备 YAML trial entry，但**不写入 ledger**。

## 验收标准

- [ ] `uv run pytest tests/test_ff5_ingest.py tests/test_macro_dff.py tests/test_ff5_exposures.py -v` → **PASS**（含 future-truncation / knowledge-date / 快照 sha256 不变量）。
- [ ] `uv run ruff check src/aionis/ingest/ff5.py src/aionis/features/ff5.py` → **clean**。
- [ ] `git diff --name-only` → **仅**出现允许修改的文件。
- [ ] `config/baseline_ff5_001.yaml` 仅含**股票特定**特征列（frozen 九列 + 通过 RD-13 的新列）；
      **不存在**任何市场-wide 原始月度因子列。
- [ ] 每个新列通过 RD-13 per-month 横截面变异诊断（无 CONSTANT/NEAR_CONSTANT/ALL_MISSING/FEW_VALID）。
- [ ] PIT 证明成立：future-truncation 与 knowledge-date 测试通过；FF5 快照 sha256 不变。
- [ ] `docs/data-intake-french-ff5.md` 7-gate 落表完成 + **owner 签注**。
- [ ] `docs/baseline-ladder.md` 更新 FF5/DFF 数据源 + PIT + 特征设计说明。
- [ ] **owner 已明确授权** BASELINE-FF5-001 trial。
- [ ] **trial registry YAML 已准备**（但不写入 ledger）。

## 失败处理

（同 RES-01；略）——此外：若滚动暴露/交互设计在 RD-13 或 PIT 验证中失败（例如全部交互列
被诊断拒绝、或无法构造无同月未来使用的暴露），STOP 并将 `状态` 改为
**"REWRITE BLOCKED — needs owner design input"**，由 owner/强模型重新规划，不自行发明替代设计。

## 必须运行的测试

- `uv run pytest tests/test_ff5_ingest.py tests/test_macro_dff.py tests/test_ff5_exposures.py -v`
- `uv run ruff check`（相关文件）
- `git diff --name-only`
- `git diff -- runs/ledger.jsonl docs/phase-*-preregistration.md decisions/ADR-*.md`（必须为空）

## 预期产物

1. **代码文件**：`src/aionis/ingest/ff5.py`、`src/aionis/ingest/macro_dff.py`、`src/aionis/features/ff5.py`
2. **配置文件**：`config/baseline_ff5_001.yaml`
3. **Runner 脚本**：`scripts/res_02_baseline_ff5_run.py`
4. **单元测试**：`tests/test_ff5_ingest.py`、`tests/test_macro_dff.py`、`tests/test_ff5_exposures.py`
5. **intake 记录**：`docs/data-intake-french-ff5.md`（7-gate 落表 + owner 签注）
6. **文档**：`docs/baseline-ladder.md`（新建并更新）
7. **Trial registry YAML**（准备但**不写入 ledger**）

## 完成后需要更新

1. 本文件头部 `状态` 在 owner 授权并完成后更新为 "completed"。
2. Orchestrator 更新 `state/handoff.md`，记录 BASELINE-FF5-001 trial 准备完成。
3. 任务完成后移入 `tasks/completed/TASK-RES-02-baseline-ff5.md`。

## 依赖顺序

```text
AUD-00 COMPLETE
├── AUD-01~05A COMPLETE
├── RD-13 COMPLETE (横截面变异 guard — 本任务特征列的前置闸门)
├── RD-15 (rank objective contract — owner freeze 后供后续 rank 基线；本 trial 保持 regression)
├── RES-01 (baseline momentum) → owner GO → Engineer → Verifier → Reviewer → COMPLETE
└── RES-02 (baseline FF5) → owner GO → Engineer → Verifier → Reviewer → COMPLETE（可与 RES-01 并行）
```

## See also

- `reports/audits/2026-07-31-quant-llm-research-audit.md` §4.2, §8.1, §11 P2
- `docs/phase-b-preregistration.md` §2（应共享但未实现的 FF5/DFF）
- `decisions/ADR-010-sesoi-tost-sequential-gate.md`
- `tasks/active/TASK-RD-13-cross-sectional-variation-guard.md`（COMPLETE — 特征列前置闸门）
- `tasks/active/TASK-RD-15-rank-objective-contract.md`（rank 合约；本 baseline 供其输入）
- `docs/data-intake-rubric.md`（7-gate 准入矩阵）
- `src/aionis/eval/ff5_residual.py`（既有 FF5 工具：fetch/parse 复用 + G3 无 vintage 注记）
- `docs/quant-selection-research.md` §7（因子复用/许可记录）、§8.1（数据源注册表）
- Fama-French (2015) — A Five-Factor Asset Pricing Model
- French Data Library — [http://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html](http://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html)
