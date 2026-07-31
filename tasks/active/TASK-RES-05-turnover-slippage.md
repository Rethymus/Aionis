# RES-05 — Economic-validity lens: turnover and slippage (S; owner-gated)

- 编号: RES-05
- 状态: **owner-gated — awaiting explicit authorization; DO NOT start without owner GO**
- Priority: **P2**（审计 §11 P2 后续研究方向；§4.3 策略收益透镜）
- Size: **S**（交易成本模型；2-3 周工作量）
- Risk: **MEDIUM**（交易成本估算但仅探索性；不触碰 frozen B/C/D/E1 结果）
- 建议 agent role / model tier: **Engineer (Sonnet) → Verifier (Sonnet) → Reviewer (Opus)**

## 目标 + 为什么重要

**目标**：在 Aionis 现有策略收益计算基础上，增加 **turnover 计算与 slippage 模型**，形成一个新的 strategy config，注册为 **STRATEGY-TS-001**（Turnover-Slippage）。

**为什么重要**（审计发现）：
- 审计 §4.3：ledger #31/#32 的策略收益 **gross-of-costs**，没有 turnover、next-open 成交、冲击、借券、退市收益或容量。
- 审计 §11 P2："[D] 加 next-open、turnover、slippage、liquidity、borrow、delisting 和 capacity；报告净值而非只报 IC。"
- 审计 §8.2：FINSABER 提供了 slippage 工件参考。
- **Gross Sharpe 0.621 不等于可交易**：未考虑交易成本（换手、滑点）。

## 必须注册的新 trial

此任务完成后必须创建一个新的 trial registry entry：

```yaml
trial_id: STRATEGY-TS-001
trial_family: economic-validity-lens
type: exploratory-strategy-execution
primary_parent: "frozen Phase B/C strategy returns (ledger #31/#32)"
config_sig: <sha256 of the new config file>
execution_change:
  from: "gross returns (无交易成本)"
  to: "net returns (turnover + slippage 模型)"
primary_metric: "net Sharpe (after turnover + slippage)"
turnover_model: "monthly percentage turnover"
slippage_model: "linear slippage (基点 × 交易量占比)"
universe: "588 clean ticker PIT"
n_jobs: 1
random_seed: 0
h6_determinism: true
status: "pending-owner-authorization"
registered_at: <timestamp of owner GO>
```

## 允许修改的文件

仅限以下文件的新增或修改：
- `src/aionis/eval/strategy_returns.py`（新增 `calculate_turnover` 和 `apply_slippage` 函数）
- `config/strategy_ts_001.yaml`（新建配置文件，指定 turnover/slippage 参数）
- `scripts/res_05_strategy_ts_run.py`（新建 RES-05 专用 runner）
- `tests/test_strategy_turnover_slippage.py`（新建单元测试）
- `docs/economic-validity-lens.md`（更新 turnover/slippage 说明）
- `.omc/plans/plan-res-05.md`（可选：实施计划草稿）

## 禁止修改的文件

- `runs/ledger.jsonl`
- `docs/phase-*-preregistration.md`
- `decisions/ADR-*.md`
- `scripts/phase_{b,c,d,e1}_run.py`
- `scripts/strategy_eval_run.py`（frozen strategy runner）
- `data/**`、`runs/results/**`
- `state/current.md`、`state/handoff.md`

## 前置条件（owner gate）

1. **Owner 明确书面授权**：允许启动 STRATEGY-TS-001 trial。
2. **ADR-010 冻结已生效**。
3. **AUD-00 全部 P0 任务 COMPLETE**。
4. **可与其他 RES 并行**：不依赖其他 RES 任务。

## 实施要求

### Engineer 职责（S 长度；2-3 周）
1. **Turnover 计算**：
   - 在 `src/aionis/eval/strategy_returns.py` 中新增 `calculate_turnover` 函数。
   - **定义**：月度 turnover = （本月买入金额 + 本金卖出金额）/ 2 / 组合市值。
   - **公式**：`turnover_t = sum(|w_t - w_{t-1}|) / 2`，其中 `w_t` 是 t 月末权重向量。
2. **Slippage 模型**：
   - 新增 `apply_slippage` 函数。
   - **线性 slippage 模型**：`slippage_bp = 基点 × 交易量占比`。
   - **假设**：大盘股 slippage 较低（10-20 bps），小盘股较高（30-50 bps）。
   - **简化**：使用 mktcap 分档（大盘/中盘/小盘）固定 slippage 基点。
3. **配置文件**：创建 `config/strategy_ts_001.yaml`：
   - `turnover_calculation: "monthly"`
   - `slippage_model: "linear_by_mktcap"`
   - `slippage_bps`：按 mktcap 分档指定（如 "large: 15, mid: 25, small: 40"）。
4. **Runner 脚本**：`scripts/res_05_strategy_ts_run.py`：
   - 使用 `config/strategy_ts_001.yaml`。
   - 读取 frozen B/C 的预测结果。
   - **禁止**运行 confirmatory headline（仅 exploratory）。
5. **单元测试**：`tests/test_strategy_turnover_slippage.py` 至少包含：
   - turnover 计算正确性测试（已知权重 → 计算 turnover）。
   - slippage 应用正确性测试（已知 slippage bps → 计算 net returns）。
   - H6 确定性测试。
6. **文档**：`docs/economic-validity-lens.md` 更新：
   - turnover 定义与公式。
   - slippage 模型假设（线性、分档）。
   - 局限性说明（简化模型；未使用 order book 数据）。

### Verifier 职责
1. **Turnover 公式正确性**：审查 `calculate_turnover` 实现 → 确认使用标准公式 `sum(|w_t - w_{t-1}|) / 2`。
2. **Slippage 模型合理性**：确认线性 slippage 假设 + mktcap 分档符合文献（参考 FINSABER 或经典交易成本文献）。
3. **配置隔离**：确认 `config/strategy_ts_001.yaml` 是**新文件**。
4. **H6 确定性**：运行 `uv run pytest tests/test_strategy_turnover_slippage.py -v` → **PASS**。
5. **禁用确认**：`git diff --name-only` → **禁止**出现 frozen 文件。

### Reviewer 职责
1. **交易成本文献对齐**：核实 turnover/slippage 定义是否与 Almgren-Chriss、FINSABER 或其他文献一致。
2. **简化假设合理性**：确认线性 slippage + mktcap 分档在探索性研究中可接受。
3. **不碰结果**：确认没有任何代码读取或写入 `runs/results/**`。
4. **owner gate 检查**：确认 owner 已明确授权 STRATEGY-TS-001 trial。
5. **trial registry 准备**：验收时必须准备 YAML trial entry。

## 验收标准

- [ ] `uv run pytest tests/test_strategy_turnover_slippage.py -v` → **PASS**。
- [ ] `uv run ruff check src/aionis/eval/strategy_returns.py` → **clean**。
- [ ] `git diff --name-only` → **仅**出现允许修改的文件。
- [ ] `config/strategy_ts_001.yaml` 指定 turnover/slippage 参数。
- [ ] `docs/economic-validity-lens.md` 更新 turnover/slippage 说明。
- [ ] **owner 已明确授权** STRATEGY-TS-001 trial。
- [ ] **trial registry YAML 已准备**。

## 失败处理

（同 RES-01；略）

## 必须运行的测试

- `uv run pytest tests/test_strategy_turnover_slippage.py -v`
- `uv run ruff check`（相关文件）
- `git diff --name-only`
- `git diff -- runs/ledger.jsonl docs/phase-*-preregistration.md decisions/ADR-*.md`（必须为空）

## 预期产物

1. **代码文件**：`src/aionis/eval/strategy_returns.py`（新增 turnover/slippage 函数）
2. **配置文件**：`config/strategy_ts_001.yaml`
3. **Runner 脚本**：`scripts/res_05_strategy_ts_run.py`
4. **单元测试**：`tests/test_strategy_turnover_slippage.py`
5. **文档**：`docs/economic-validity-lens.md`（更新 turnover/slippage）
6. **Trial registry YAML**（准备但**不写入 ledger**）

## 完成后需要更新

1. 本文件头部 `状态` 从 "owner-gated" 更新为 "completed"。
2. Orchestrator 更新 `state/handoff.md`，记录 STRATEGY-TS-001 trial 准备完成。
3. 任务完成后移入 `tasks/completed/TASK-RES-05-turnover-slippage.md`。

## 依赖顺序

```text
AUD-00 COMPLETE
├── AUD-01~05A COMPLETE
├── RES-01/02/03 (baseline ladder) → owner GO → COMPLETE（并行）
├── RES-04 (next-open) → owner GO → COMPLETE（并行）
└── RES-05 (turnover/slippage) → owner GO → COMPLETE（与 RES-04 并行）
```

## See also

- `reports/audits/2026-07-31-quant-llm-research-audit.md` §4.3, §8.2, §11 P2
- `decisions/ADR-010-sesoi-tost-sequential-gate.md`
- FINSABER (Li et al. 2025) — slippage 工件参考
- Almgren, Chriss (2001) — Optimal Execution of Portfolio Transactions
- `runs/ledger.jsonl` #31/#32（frozen B/C strategy returns）
