# RES-06 — Economic-validity lens: liquidity and borrow costs (S; owner-gated)

- 编号: RES-06
- 状态: **owner-gated — awaiting explicit authorization; DO NOT start without owner GO**
- Priority: **P2**（审计 §11 P2 后续研究方向；§4.3 策略收益透镜）
- Size: **S**（流动性约束 + 借券成本；2-3 周工作量）
- Risk: **MEDIUM**（流动性约束但仅探索性；不触碰 frozen B/C/D/E1 结果）
- 建议 agent role / model tier: **Engineer (Sonnet) → Verifier (Sonnet) → Reviewer (Opus)**

## 目标 + 为什么重要

**目标**：在 Aionis 现有策略收益计算基础上，增加 **liquidity 约束与 borrow cost 模型**，形成一个新的 strategy config，注册为 **STRATEGY-LB-001**（Liquidity-Borrow）。

**为什么重要**（审计发现）：
- 审计 §4.3：ledger #31/#32 的策略收益 **gross-of-costs**，没有 turnover、next-open 成交、冲击、**借券、退市收益或容量**。
- 审计 §11 P2："[D] 加 next-open、turnover、slippage、**liquidity、borrow**、delisting 和 capacity；报告净值而非只报 IC。"
- **Gross Sharpe 0.621 不等于可交易**：未考虑做空借券成本（hard-to-borrow stocks 更高）和流动性约束（小盘股交易受限）。

## 必须注册的新 trial

此任务完成后必须创建一个新的 trial registry entry：

```yaml
trial_id: STRATEGY-LB-001
trial_family: economic-validity-lens
type: exploratory-strategy-execution
primary_parent: "frozen Phase B/C strategy returns (ledger #31/#32)"
config_sig: <sha256 of the new config file>
execution_change:
  from: "unconstrained long-short (无流动性/借券约束)"
  to: "liquidity-filtered + borrow-cost-adjusted"
primary_metric: "net Sharpe (after liquidity filtering + borrow costs)"
liquidity_filter: "average daily volume > 阈值"
borrow_cost_model: "hard-to-borrow fee (按 mktcap/short interest 分档)"
universe: "588 clean ticker PIT → liquidity-filtered subset"
n_jobs: 1
random_seed: 0
h6_determinism: true
status: "pending-owner-authorization"
registered_at: <timestamp of owner GO>
```

## 允许修改的文件

仅限以下文件的新增或修改：
- `src/aionis/ingest/market.py`（新增 `get_liquidity_metrics` 和 `get_borrow_costs` 函数；仅探索性数据）
- `src/aionis/eval/strategy_returns.py`（新增 `apply_liquidity_filter` 和 `apply_borrow_costs` 函数）
- `config/strategy_lb_001.yaml`（新建配置文件，指定 liquidity/borrow 参数）
- `scripts/res_06_strategy_lb_run.py`（新建 RES-06 专用 runner）
- `tests/test_strategy_liquidity_borrow.py`（新建单元测试）
- `docs/economic-validity-lens.md`（更新 liquidity/borrow 说明）
- `.omc/plans/plan-res-06.md`（可选：实施计划草稿）

## 禁止修改的文件

- `runs/ledger.jsonl`
- `docs/phase-*-preregistration.md`
- `decisions/ADR-*.md`
- `scripts/phase_{b,c,d,e1}_run.py`
- `scripts/strategy_eval_run.py`（frozen strategy runner）
- `data/**`、`runs/results/**`
- `state/current.md`、`state/handoff.md`

## 前置条件（owner gate）

1. **Owner 明确书面授权**：允许启动 STRATEGY-LB-001 trial。
2. **ADR-010 冻结已生效**。
3. **AUD-00 全部 P0 任务 COMPLETE**。
4. **可与其他 RES 并行**：不依赖其他 RES 任务。

## 实施要求

### Engineer 职责（S 长度；2-3 周）
1. **Liquidity 数据获取（探索性）**：
   - 在 `src/aionis/ingest/market.py` 中新增 `get_liquidity_metrics` 函数。
   - **数据源**：**Tiingo** 或 **Alpaca** 日频数据（禁止 yfinance/Stooq）。
   - **指标**：平均日成交量（`avg_daily_volume_20d`）、平均日成交额（`avg_daily_dollar_volume_20d`）。
   - **Politeness**：强制 `≥2s` 间隔；有界退避。
2. **Borrow cost 数据（探索性；简化假设）**：
   - 新增 `get_borrow_costs` 函数。
   - **简化假设**：按 **mktcap** 和 **short interest** 分档固定 borrow fee（如 "large cap + low short interest: 10 bps/year; small cap + high short interest: 100 bps/year"）。
   - **注意**：真实 borrow cost 数据（如 Markit、Data Explorers）需要付费；当前使用简化模型。
3. **Liquidity 过滤**：
   - 在 `src/aionis/eval/strategy_returns.py` 中新增 `apply_liquidity_filter` 函数。
   - **规则**：剔除 `avg_daily_dollar_volume_20d < 阈值` 的股票（如 `< $1M`）。
4. **Borrow cost 调整**：
   - 新增 `apply_borrow_costs` 函数。
   - **做空收益调整**：`net_short_return = gross_short_return - annual_borrow_fee / 12`。
5. **配置文件**：创建 `config/strategy_lb_001.yaml`：
   - `liquidity_filter: "avg_daily_dollar_volume_20d >= 1000000"`（阈值可调）。
   - `borrow_cost_model: "tiered_by_mktcap_short_interest"`。
   - `borrow_fee_bps`：按 mktcap/short interest 分档。
6. **Runner 脚本**：`scripts/res_06_strategy_lb_run.py`：
   - 使用 `config/strategy_lb_001.yaml`。
   - 读取 frozen B/C 的预测结果。
   - **禁止**运行 confirmatory headline（仅 exploratory）。
7. **单元测试**：`tests/test_strategy_liquidity_borrow.py` 至少包含：
   - liquidity filter 正确性测试。
   - borrow cost 调整正确性测试。
   - H6 确定性测试。
8. **文档**：`docs/economic-validity-lens.md` 更新：
   - liquidity 数据源 + 阈值假设。
   - borrow cost 简化模型说明（分档；非实时数据）。
     - 局限性：真实 borrow cost 需付费数据；当前是探索性简化。

### Verifier 职责
1. **Liquidity 数据源合规**：确认使用 Tiingo/Alpaca；**禁止** yfinance/Stooq。
2. **Borrow cost 模型简化性**：确认使用分档固定 fee；**禁止**假设实时 borrow cost 数据。
3. **配置隔离**：确认 `config/strategy_lb_001.yaml` 是**新文件**。
4. **H6 确定性**：运行 `uv run pytest tests/test_strategy_liquidity_borrow.py -v` → **PASS**。
5. **禁用确认**：`git diff --name-only` → **禁止**出现 frozen 文件。

### Reviewer 职责
1. **流动性约束合理性**：核实 liquidity 阈值（如 `$1M` 日成交额）是否符合 S&P 500 大盘股实际。
2. **Borrow cost 简化假设合理性**：确认分档固定 fee 在探索性研究中可接受。
3. **不碰结果**：确认没有任何代码读取或写入 `runs/results/**`。
4. **owner gate 检查**：确认 owner 已明确授权 STRATEGY-LB-001 trial。
5. **trial registry 准备**：验收时必须准备 YAML trial entry。

## 验收标准

- [ ] `uv run pytest tests/test_strategy_liquidity_borrow.py -v` → **PASS**。
- [ ] `uv run ruff check src/aionis/ingest/market.py src/aionis/eval/strategy_returns.py` → **clean**。
- [ ] `git diff --name-only` → **仅**出现允许修改的文件。
- [ ] `config/strategy_lb_001.yaml` 指定 liquidity/borrow 参数。
- [ ] `docs/economic-validity-lens.md` 更新 liquidity/borrow 说明 + 局限性。
- [ ] **owner 已明确授权** STRATEGY-LB-001 trial。
- [ ] **trial registry YAML 已准备**。

## 失败处理

（同 RES-01；略）

## 必须运行的测试

- `uv run pytest tests/test_strategy_liquidity_borrow.py -v`
- `uv run ruff check`（相关文件）
- `git diff --name-only`
- `git diff -- runs/ledger.jsonl docs/phase-*-preregistration.md decisions/ADR-*.md`（必须为空）

## 预期产物

1. **代码文件**：`src/aionis/ingest/market.py`（新增 liquidity/borrow 函数）
2. **代码文件**：`src/aionis/eval/strategy_returns.py`（新增 filter/adjust 函数）
3. **配置文件**：`config/strategy_lb_001.yaml`
4. **Runner 脚本**：`scripts/res_06_strategy_lb_run.py`
5. **单元测试**：`tests/test_strategy_liquidity_borrow.py`
6. **文档**：`docs/economic-validity-lens.md`（更新 liquidity/borrow）
7. **Trial registry YAML**（准备但**不写入 ledger**）

## 完成后需要更新

1. 本文件头部 `状态` 从 "owner-gated" 更新为 "completed"。
2. Orchestrator 更新 `state/handoff.md`，记录 STRATEGY-LB-001 trial 准备完成。
3. 任务完成后移入 `tasks/completed/TASK-RES-06-liquidity-borrow.md`。

## 依赖顺序

```text
AUD-00 COMPLETE
├── AUD-01~05A COMPLETE
├── RES-01/02/03 (baseline ladder) → owner GO → COMPLETE（并行）
├── RES-04 (next-open) → owner GO → COMPLETE（并行）
├── RES-05 (turnover/slippage) → owner GO → COMPLETE（并行）
└── RES-06 (liquidity/borrow) → owner GO → COMPLETE（与 RES-04/05 并行）
```

## See also

- `reports/audits/2026-07-31-quant-llm-research-audit.md` §4.3, §8.2, §11 P2
- `decisions/ADR-010-sesoi-tost-sequential-gate.md`
- FINSABER (Li et al. 2025) — liquidity/slippage 工件参考
- `runs/ledger.jsonl` #31/#32（frozen B/C strategy returns）
