# RES-07 — Economic-validity lens: delisting and capacity (M; owner-gated)

- 编号: RES-07
- 状态: **owner-gated — awaiting explicit authorization; DO NOT start without owner GO**
- Priority: **P2**（审计 §11 P2 后续研究方向；§4.3 策略收益透镜）
- Size: **M**（退市偏差修正 + 容量约束；3-4 周工作量）
- Risk: **HIGH**（退市数据获取复杂；容量估算需文献对齐）
- 建议 agent role / model tier: **Engineer (Sonnet) → Verifier (Sonnet) → Reviewer (Opus)**

## 目标 + 为什么重要

**目标**：在 Aionis 现有策略收益计算基础上，增加 **delisting adjustment 和 capacity constraint**，形成一个新的 strategy config，注册为 **STRATEGY-DC-001**（Delisting-Capacity）。

**为什么重要**（审计发现）：
- 审计 §4.3：ledger #31/#32 的策略收益 **gross-of-costs**，没有 turnover、next-open 成交、冲击、借券、**退市收益或容量**。
- 审计 §5.4：免费 S&P 历史成分仓库（Wikipedia/公开资料重建）本身由承认遗漏和早期不可验证性；有幸存者偏差。
- 审计 §8.2：CRSP 的 Calculations and Index Methodologies 与 Shumway (1997) 的 Delisting Bias in CRSP Data 提供了退市调整参考。
- 审计 §14.2：Shumway (1997) — delisting returns 可能 -30% 到 -100%；忽略会高估收益。
- **Gross Sharpe 0.621 不等于可交易**：未考虑退市偏差（小盘股退市率高）和容量约束（策略无法承受大资金）。

## 必须注册的新 trial

此任务完成后必须创建一个新的 trial registry entry：

```yaml
trial_id: STRATEGY-DC-001
trial_family: economic-validity-lens
type: exploratory-strategy-execution
primary_parent: "frozen Phase B/C strategy returns (ledger #31/#32)"
config_sig: <sha256 of the new config file>
execution_change:
  from: "no delisting adjustment + no capacity constraint"
  to: "delisting-adjusted + capacity-constrained"
primary_metric: "net Sharpe (after delisting + capacity)"
delisting_model: "Shumway (1997) delisting return adjustment"
capacity_model: "AUM 限制 × 交易量占比约束"
universe: "588 clean ticker PIT → delisting-adjusted"
n_jobs: 1
random_seed: 0
h6_determinism: true
status: "pending-owner-authorization"
registered_at: <timestamp of owner GO>
```

## 允许修改的文件

仅限以下文件的新增或修改：
- `src/aionis/ingest/delisting.py`（新建退市数据获取模块；探索性数据）
- `src/aionis/eval/strategy_returns.py`（新增 `apply_delisting_adjustment` 和 `apply_capacity_constraint` 函数）
- `config/strategy_dc_001.yaml`（新建配置文件，指定 delisting/capacity 参数）
- `scripts/res_07_strategy_dc_run.py`（新建 RES-07 专用 runner）
- `tests/test_strategy_delisting_capacity.py`（新建单元测试）
- `docs/economic-validity-lens.md`（更新 delisting/capacity 说明）
- `.omc/plans/plan-res-07.md`（可选：实施计划草稿）

## 禁止修改的文件

- `runs/ledger.jsonl`
- `docs/phase-*-preregistration.md`
- `decisions/ADR-*.md`
- `scripts/phase_{b,c,d,e1}_run.py`
- `scripts/strategy_eval_run.py`（frozen strategy runner）
- `data/**`、`runs/results/**`
- `state/current.md`、`state/handoff.md`

## 前置条件（owner gate）

1. **Owner 明确书面授权**：允许启动 STRATEGY-DC-001 trial。
2. **ADR-010 冻结已生效**。
3. **AUD-00 全部 P0 任务 COMPLETE**。
4. **可与其他 RES 并行**：不依赖其他 RES 任务（但优先级低于 S 任务）。

## 实施要求

### Engineer 职责（M 长度；3-4 周）
1. **Delisting 数据获取（探索性；困难）**：
   - 在 `src/aionis/ingest/delisting.py` 中新建退市数据获取模块。
   - **数据源**：
     - **EDGAR**（Form 15, 25）：部分退市事件有 filing。
     - **CRSP**（需付费；当前不使用）。
     - **公开资料**（Wikipedia、exchange announcements）：探索性使用。
   - **简化假设**：由于完整退市数据需付费（CRSP），当前使用简化规则：
     - 若某股票在 t 月末在 universe，但 t+1 月末不在 → 假设退市。
     - **退市收益**：Shumway (1997) 建议 **-30%**（保守估计；delisting return 通常是 -30% 到 -100%）。
2. **Delisting Adjustment**：
   - 在 `src/aionis/eval/strategy_returns.py` 中新增 `apply_delisting_adjustment` 函数。
   - **规则**：退市月份 `return_delisting = -0.30`（-30%）。
   - **注意**：此规则会惩罚小盘股（退市率更高）。
3. **Capacity Constraint**：
   - 新增 `apply_capacity_constraint` 函数。
   - **容量定义**：策略最大可承受 AUM（如 `$10M`）。
   - **约束规则**：
     - 单只股票权重 ≤ **日成交额的 5%**（避免冲击成本过高）。
     - 组合 AUM ≤ **容量上限**（超过部分按比例缩小）。
4. **配置文件**：创建 `config/strategy_dc_001.yaml`：
   - `delisting_adjustment: "fixed -30% for delisting events"`
   - `capacity_constraint: "max_AUM 10M; max_position 5% of daily_volume"`
   - `delisting_return: -0.30`（可调参数）。
5. **Runner 脚本**：`scripts/res_07_strategy_dc_run.py`：
   - 使用 `config/strategy_dc_001.yaml`。
   - 读取 frozen B/C 的预测结果。
   - **禁止**运行 confirmatory headline（仅 exploratory）。
6. **单元测试**：`tests/test_strategy_delisting_capacity.py` 至少包含：
   - delisting adjustment 正确性测试（退市月份 → -30%）。
   - capacity constraint 正确性测试（超 AUM → 按比例缩小）。
   - H6 确定性测试。
7. **文档**：`docs/economic-validity-lens.md` 更新：
     - delisting 数据源 + 简化假设（无 CRSP；使用固定 -30%）。
     - capacity 约束定义（AUM 上限 + 单只股票权重上限）。
     - 局限性：真实退市数据需付费（CRSP）；当前是探索性简化。

### Verifier 职责
1. **Delisting 数据源探索性**：确认使用 EDGAR/公开资料；**禁止**假设完整 CRSP 数据。
2. **Delisting Adjustment 保守性**：确认 -30% 是保守估计（Shumway 1997 建议）。
3. **Capacity Constraint 合理性**：确认 AUM 上限（`$10M`）和单只股票权重上限（5% 日成交额）符合 S&P 500 大盘股实际。
4. **配置隔离**：确认 `config/strategy_dc_001.yaml` 是**新文件**。
5. **H6 确定性**：运行 `uv run pytest tests/test_strategy_delisting_capacity.py -v` → **PASS**。
6. **禁用确认**：`git diff --name-only` → **禁止**出现 frozen 文件。

### Reviewer 职责
1. **Delisting 文献对齐**：核实 Shumway (1997) delisting return 建议是否正确应用（-30% 保守估计）。
2. **Capacity 文献对齐**：核实容量约束（AUM 上限 + 5% 日成交额）是否与交易成本文献（Almgren-Chriss 2001）一致。
3. **不碰结果**：确认没有任何代码读取或写入 `runs/results/**`。
4. **owner gate 检查**：确认 owner 已明确授权 STRATEGY-DC-001 trial。
5. **trial registry 准备**：验收时必须准备 YAML trial entry。

## 验收标准

- [ ] `uv run pytest tests/test_strategy_delisting_capacity.py -v` → **PASS**。
- [ ] `uv run ruff check src/aionis/ingest/delisting.py src/aionis/eval/strategy_returns.py` → **clean**。
- [ ] `git diff --name-only` → **仅**出现允许修改的文件。
- [ ] `config/strategy_dc_001.yaml` 指定 delisting/capacity 参数。
- [ ] `docs/economic-validity-lens.md` 更新 delisting/capacity 说明 + 局限性。
- [ ] **owner 已明确授权** STRATEGY-DC-001 trial。
- [ ] **trial registry YAML 已准备**。

## 失败处理

（同 RES-01；略）

## 必须运行的测试

- `uv run pytest tests/test_strategy_delisting_capacity.py -v`
- `uv run ruff check`（相关文件）
- `git diff --name-only`
- `git diff -- runs/ledger.jsonl docs/phase-*-preregistration.md decisions/ADR-*.md`（必须为空）

## 预期产物

1. **代码文件**：`src/aionis/ingest/delisting.py`（新建）
2. **代码文件**：`src/aionis/eval/strategy_returns.py`（新增 delisting/capacity 函数）
3. **配置文件**：`config/strategy_dc_001.yaml`
4. **Runner 脚本**：`scripts/res_07_strategy_dc_run.py`
5. **单元测试**：`tests/test_strategy_delisting_capacity.py`
6. **文档**：`docs/economic-validity-lens.md`（更新 delisting/capacity）
7. **Trial registry YAML**（准备但**不写入 ledger**）

## 完成后需要更新

1. 本文件头部 `状态` 从 "owner-gated" 更新为 "completed"。
2. Orchestrator 更新 `state/handoff.md`，记录 STRATEGY-DC-001 trial 准备完成。
3. 任务完成后移入 `tasks/completed/TASK-RES-07-delisting-capacity.md`。

## 依赖顺序

```text
AUD-00 COMPLETE
├── AUD-01~05A COMPLETE
├── RES-01/02/03 (baseline ladder; S) → owner GO → COMPLETE（并行）
├── RES-04/05/06 (economic lens; S) → owner GO → COMPLETE（并行）
└── RES-07 (delisting/capacity; M) → owner GO → COMPLETE（与 RES-04/05/06 并行；优先级较低）
```

## See also

- `reports/audits/2026-07-31-quant-llm-research-audit.md` §4.3, §5.4, §8.2, §14.2, §11 P2
- `decisions/ADR-010-sesoi-tost-sequential-gate.md`
- Shumway (1997) — The Delisting Bias in CRSP Data
- CRSP — Calculations and Index Methodologies
- Almgren, Chriss (2001) — Optimal Execution of Portfolio Transactions
- `runs/ledger.jsonl` #31/#32（frozen B/C strategy returns）
