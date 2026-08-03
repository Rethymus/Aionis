# Baseline Ladder — BASELINE-FF5-001（RES-02）

> 状态：**v0.1 · 2026-08-03 · 准备完成（prepared），owner 授权前不注册、不写 ledger**。
> 对应任务：`tasks/active/TASK-RES-02-baseline-ff5.md`（REWRITTEN 2026-08-03 — cross-sectional-valid）。
> 7-gate 数据准入落表：`docs/data-intake-french-ff5.md`（**owner 签注 PENDING**）。

---

## 1. 目标

在 frozen Phase B 九列数值基本面基线（mktcap/pb_ratio/roa + 六项基本面）之上，增加
**股票特定的 Fama-French 5 因子滚动暴露与交互特征**（rolling beta-to-factor + 因子载荷 ×
个股特征交互）以及 **DFF 的股票特定利率暴露**，形成新 baseline config **BASELINE-FF5-001**
（frozen 九列 + 11 新列 = 20 列）。全部新列为**股票特定、月内横截面可变**——**绝不再**把
市场-wide 原始月度因子列（MKTRF/SMB/HML/RMW/CMA/DFF）作为特征列。

动机（审计）：frozen `feature_cols` 缺少 pre-reg §2 承诺的 momentum/reversal/vol、FF5、DFF
宏观（审计 §4.2）；弱基线使 differential 结论无法外推到含 FF5 的环境（§8.1 GKX-94）；§11 P2
要求新 config / 新 ledger 行才可加入强数值基线。

## 2. 数据源 + PIT

| 源 | 频率 | PIT 纪律 | 快照 | 层级 |
|---|---|---|---|---|
| French FF5（bulk ZIP，日频） | 日 | d 日值 d+1 起可知；月末 t 窗口只用 `date <= t` | `data/cache/ff5_daily_snapshot.csv` + `.sha256`（G3 冻结；漂移 = 硬错误） | **exploratory**（G1 非白名单 + G3 无 vintage） |
| FRED DFF（ALFRED vintage） | 日 | `merge_asof(allow_exact_matches=False)`：level(d) = 严格早于 d 的最新 first print（同日 16:30 ET 发布 = d 日未来信息） | `data/cache/alfred_DFF.json`（ALFRED 缓存） | confirmatory-tier（US 公共领域；vintage 不可回改） |
| 基本面（filed-date） | 季/年 | `aionis.ingest.fundamentals.pit_align`（filed ≤ d；绝不用 period-end） | 既有 Phase B 缓存 | frozen |

**Knowledge date 契约**：特征在月末 t 计算（只用 ≤ t 最后交易日的观测），最早在 **t+1 首个
交易日**可知。`broadcast_monthly_exposures` 把月末值只广播到严格晚于 t 的 session
（`allow_exact_matches=False`）——月内 session 永远看不到当月数据算出的值（无同月未来使用）。

## 3. 特征设计（11 列，全部股票特定）

### A. 滚动因子暴露（6 列）— `aionis.features.ff5.rolling_factor_exposures`

每只股票 i、月末 t：截至 t 的最近 **252 交易日**（min_periods=**126**）日频窗口：

```
r_i,d − RF_d = α + Σ_k β_k·F_k,d + ε        (FF5 多元 OLS)
r_i,d − RF_d = α + β_dff·ΔDFF_d + ε         (ΔDFF 一元 OLS)
```

→ `beta_mkt, beta_smb, beta_hml, beta_rmw, beta_cma, beta_dff`（FF5 2015 定义；
`np.linalg.lstsq`，n_jobs=1，H6 确定性）。窗口 <126 obs → NaN（LightGBM missing 策略）。

### B. 因子载荷 × 个股特征交互（5 列）— `build_ff5_interactions`

| 列 | 公式 | 个股特征（PIT） |
|---|---|---|
| `beta_smb_x_size` | beta_smb × ln(mktcap) | mktcap = close × shares_out（filed ≤ d） |
| `beta_hml_x_value` | beta_hml × pb_ratio | pb = close×shares / equity |
| `beta_rmw_x_prof` | beta_rmw × roa | roa = net_income / assets |
| `beta_cma_x_invest` | beta_cma × Δfund_assets/fund_assets | 连续两次 filings（`asset_growth_from_filings`，filed-date PIT） |
| `beta_dff_x_lev` | beta_dff × (fund_long_term_debt / fund_assets) | 杠杆 |

域守卫：mktcap ≤ 0 → ln NaN；assets ≤ 0 / 缺 → 杠杆 NaN；NaN 传播，绝不静默填充。

## 4. RD-13 横截面变异护栏（fail closed）

- 每个新列按月跑 `aionis.features.diagnostics`（RD-13，COMPLETE 只读调用）；
  **CONSTANT / NEAR_CONSTANT / ALL_MISSING / FEW_VALID → 该列不入 config**（reason code 入
  trial registry）。
- 市场-wide 原始因子列按构造即月内 CONSTANT → **结构性不合格**，不参与候选；macro 输入只
  允许走 interaction 路径。
- 交互中的因子侧与特征侧分别诊断；交互后仍无截面变异的组合不进入 config。
- runner 对通过列集计算 config sig；**通过列为空 → BLOCKED（STOP，owner 设计输入）**。

## 5. Config（20 列）

`config/baseline_ff5_001.yaml`：frozen 九列（mktcap/pb_ratio/roa/fund_assets/fund_revenue/
fund_net_income/fund_equity/fund_shares_out/fund_long_term_debt）+ RD-13 通过的新列
（beta_mkt…beta_dff_x_lev）。runner 的 `FROZEN_FEATURE_COLS` + RD-13 过滤后的
`NEW_FEATURE_COLS` 为可执行真值；YAML 为可审计登记（`tests/test_ff5_exposures.py` 锁定两边
一致且无原始因子列）。

## 6. Runner 与 ledger 纪律

`scripts/res_02_baseline_ff5_run.py`：快照-first → 日收益 → 月末滚动暴露 → filed-date PIT
个股特征 → 交互 → session 网格 PIT 广播 → RD-13 fail-closed → **purged cross-fitted CV**
（5-fold PurgedGroupKFold，group=month，embargo=21 sessions；与 frozen B/C/D/E1 同等证据
强度；frozen LightGBM；n_jobs=1）。

- runner **绝不写 `runs/ledger.jsonl`**；非 `RES_02_NO_LEDGER=1` 时，若 ledger 中不存在
  **相同 config_sig 的 config_committed 行**（owner 授权后写入），runner 直接 ABORT
  （config_committed BEFORE result）。
- trial `mode: exploratory`（FF5 G3 不可证 → 快照冻结）；DFF via ALFRED 为 confirmatory-tier。

## 7. Trial registry entry（已准备，**未注册、未写 ledger**）

> 依据 `evals/trials/README.md`（RD-17）：此 YAML 是任务 spec 要求的 registry 准备件；正式
> 注册由 **owner 授权后**由 Orchestrator 物化为 `evals/trials/baseline-ff5-001.json`
> （TrialIntent schema，`planned_config_sha256` = 本条目 `config_sig`，`validation_kind:
> purged_cross_fit`，`estimand: rank_ic`），并**另行** append `runs/ledger.jsonl`
> config_committed 行。**本条目不具备 config_committed 效力。**

```yaml
trial_id: BASELINE-FF5-001
trial_family: baseline-ladder
type: exploratory-baseline-enhancement
primary_parent: "frozen Phase B (numeric fundamentals)"
config_sig: <sha256 of config/baseline_ff5_001.yaml + runner RD-13 gate output — 运行时确定>
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

## 8. 验收证据（hermetic）

- `uv run pytest tests/test_ff5_ingest.py tests/test_macro_dff.py tests/test_ff5_exposures.py -v` → **PASS**
- `uv run ruff check src/aionis/ingest/ff5.py src/aionis/features/ff5.py` → clean
- RD-13 非-常量证明：`tests/test_ff5_exposures.py::test_all_ff5_columns_vary_cross_sectionally_and_pass_rd13`
  （合成横截面上 11 列逐月全 VARIATION；市场-wide 列被 CONSTANT 拒绝；
  `test_rd13_gate_excludes_market_wide_and_all_missing_columns`）
- PIT 证明：`test_future_truncation_invariance`、`test_exposure_at_t_ignores_every_observation_after_t`、
  `test_future_vintages_never_move_past_as_of_values`、快照 sha256 不变量
- `git diff --name-only` → 仅允许修改的文件

## 9. References

- `tasks/active/TASK-RES-02-baseline-ff5.md`（spec）、`docs/data-intake-french-ff5.md`（7-gate 落表）
- `tasks/active/TASK-RD-13-cross-sectional-variation-guard.md`（COMPLETE）、
  `tasks/active/TASK-RD-17-trial-intent-registry.md`（COMPLETE）
- `reports/audits/2026-07-31-quant-llm-research-audit.md` §4.2 / §8.1 / §11 P2
- Fama-French (2015) — A Five-Factor Asset Pricing Model
- `src/aionis/eval/ff5_residual.py`（既有 FF5 工具：fetch/parse 复用 + G3 无 vintage 注记）
