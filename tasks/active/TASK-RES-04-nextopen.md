# RES-04 — Economic-validity lens: next-open execution (S; owner-gated)

- 编号: RES-04
- 状态: **owner-gated — awaiting explicit authorization; DO NOT start without owner GO**
- Priority: **P2**（审计 §11 P2 后续研究方向；§4.3 策略收益透镜）
- Size: **S**（执行时机调整；2 周工作量）
- Risk: **MEDIUM**（执行逻辑变更但仅探索性；不触碰 frozen B/C/D/E1 结果）
- 建议 agent role / model tier: **Engineer (Sonnet) → Verifier (Sonnet) → Reviewer (Opus)**

## 目标 + 为什么重要

**目标**：在 Aionis 现有策略收益计算基础上，将 **close-to-close 执行改为 next-open 执行**，形成一个新的 strategy config，注册为 **STRATEGY-NEXTOPEN-001**。

**为什么重要**（审计发现）：
- 审计 §4.3：ledger #31/#32 只含 B/C、placebo、sanity 五个策略；baseline gross 年化 Sharpe 约 0.621。这些结果 **gross-of-costs**，没有 turnover、next-open 成交、冲击、借券、退市收益或容量。
- 审计 §11 P2："[D] 加 next-open、turnover、slippage、liquidity、borrow、delisting 和 capacity；报告净值而非只报 IC。"
- 审计 §8.2：FINSABER 提供了 next-open、slippage、liquidity、LLM 成本工件参考。
- **当前 close-to-close 执行不可交易**：月末信号 → 当日 close 买入 → 假设无滑点。真实交易需要月末信号 → 次日 open 买入。

## 必须注册的新 trial

此任务完成后必须创建一个新的 trial registry entry：

```yaml
trial_id: STRATEGY-NEXTOPEN-001
trial_family: economic-validity-lens
type: exploratory-strategy-execution
primary_parent: "frozen Phase B/C strategy returns (ledger #31/#32)"
config_sig: <sha256 of the new config file>
execution_change:
  from: "close-to-close (月末信号当日 close 买入)"
  to: "next-open (月末信号次日 open 买入)"
primary_metric: "net Sharpe (after next-open execution)"
universe: "588 clean ticker PIT"
n_jobs: 1
random_seed: 0
h6_determinism: true
status: "pending-owner-authorization"
registered_at: <timestamp of owner GO>
```

## 允许修改的文件

仅限以下文件的新增或修改：
- `src/aionis/eval/strategy_returns.py`（新增 `next_open_execution` 函数；**不删除** frozen `close_to_close` 分支）
- `config/strategy_nextopen_001.yaml`（新建配置文件，指定 `execution="next_open"`）
- `scripts/res_04_strategy_nextopen_run.py`（新建 RES-04 专用 runner）
- `tests/test_strategy_nextopen.py`（新建单元测试）
- `docs/economic-validity-lens.md`（新建文档；记录 next-open 执行说明）
- `.omc/plans/plan-res-04.md`（可选：实施计划草稿）

## 禁止修改的文件

- `runs/ledger.jsonl`
- `docs/phase-*-preregistration.md`
- `decisions/ADR-*.md`
- `scripts/phase_{b,c,d,e1}_run.py`（禁止修改 frozen runner）
- `scripts/strategy_eval_run.py`（frozen strategy runner；禁止修改）
- `data/**`、`runs/results/**`
- `state/current.md`、`state/handoff.md`

## 前置条件（owner gate）

1. **Owner 明确书面授权**：允许启动 STRATEGY-NEXTOPEN-001 trial。
2. **ADR-010 冻结已生效**。
3. **AUD-00 全部 P0 任务 COMPLETE**。
4. **可与其他 RES 并行**：不依赖其他 RES 任务。

## 实施要求

### Engineer 职责（S 长度；2 周）
1. **Next-open 执行实现**：
   - 在 `src/aionis/eval/strategy_returns.py` 中新增 `next_open_execution` 函数。
   - **保留** `close_to_close` 分支（frozen B/C 策略仍使用此分支）。
   - **执行逻辑**：
     - 月末信号（t 日末）→ 次日 open（t+1 日开）买入。
     - 使用 **Tiingo next-open 价格**或 **Alpaca daily open**（禁止 yfinance/Stooq）。
     - 确保 **t+1 日 open 价格是 PIT**（不使用未来修订后的价格）。
2. **配置文件**：创建 `config/strategy_nextopen_001.yaml`：
   - `execution: "next_open"`
   - `rebalance_freq: "monthly"`（与 frozen B/C 相同）
   - `signal_source: "frozen Phase B/C predictions"`（使用 frozen 预测结果）
3. **Runner 脚本**：`scripts/res_04_strategy_nextopen_run.py`：
   - 使用 `config/strategy_nextopen_001.yaml`。
   - 读取 frozen B/C 的预测结果（不重新训练模型）。
   - **禁止**运行 confirmatory headline（仅 exploratory）。
4. **单元测试**：`tests/test_strategy_nextopen.py` 至少包含：
   - next-open 执行逻辑测试（t 日信号 → t+1 日 open 执行）。
   - PIT 价格测试（确保不使用未来价格）。
   - H6 确定性测试（seed=0 下结果可复现）。
5. **文档**：`docs/economic-validity-lens.md` 记录：
   - next-open 执行逻辑（t 日信号 → t+1 日 open）。
   - 数据源（Tiingo next-open / Alpaca daily open）。
   - PIT 合规说明（不使用未来修订价格）。

### Verifier 职责
1. **执行逻辑正确性**：审查 `strategy_returns.py` 的 `next_open_execution` 实现 → 确认 t 日信号 → t+1 日 open 执行。
2. **PIT 不变性**：确认价格数据使用 **Tiingo next-open** 或 **Alpaca daily open**；禁止 yfinance/Stooq。
3. **Frozen 分支保留**：确认 `close_to_close` 分支**未被删除或修改**。
4. **配置隔离**：确认 `config/strategy_nextopen_001.yaml` 是**新文件**。
5. **H6 确定性**：运行 `uv run pytest tests/test_strategy_nextopen.py -v` → **PASS**。
6. **禁用确认**：`git diff --name-only` → **禁止**出现 frozen 文件。

### Reviewer 职责
1. **交易逻辑合理性**：核实 next-open 执行是否符合真实交易场景（月末信号 → 次日 open 买入）。
2. **数据源合规**：确认只使用 Tiingo/Alpaca；**禁止** yfinance/Stooq。
3. **不碰结果**：确认没有任何代码读取或写入 `runs/results/**`。
4. **owner gate 检查**：确认 owner 已明确授权 STRATEGY-NEXTOPEN-001 trial。
5. **trial registry 准备**：验收时必须准备 YAML trial entry。

## 验收标准

- [ ] `uv run pytest tests/test_strategy_nextopen.py -v` → **PASS**。
- [ ] `uv run ruff check src/aionis/eval/strategy_returns.py` → **clean**。
- [ ] `git diff --name-only` → **仅**出现允许修改的文件。
- [ ] `config/strategy_nextopen_001.yaml` 指定 `execution="next_open"`。
- [ ] `docs/economic-validity-lens.md` 记录 next-open 执行逻辑 + PIT 合规。
- [ ] **owner 已明确授权** STRATEGY-NEXTOPEN-001 trial。
- [ ] **trial registry YAML 已准备**。

## 失败处理

（同 RES-01；略）

## 必须运行的测试

- `uv run pytest tests/test_strategy_nextopen.py -v`
- `uv run ruff check`（相关文件）
- `git diff --name-only`
- `git diff -- runs/ledger.jsonl docs/phase-*-preregistration.md decisions/ADR-*.md`（必须为空）

## 预期产物

1. **代码文件**：`src/aionis/eval/strategy_returns.py`（新增 `next_open_execution` 分支）
2. **配置文件**：`config/strategy_nextopen_001.yaml`
3. **Runner 脚本**：`scripts/res_04_strategy_nextopen_run.py`
4. **单元测试**：`tests/test_strategy_nextopen.py`
5. **文档**：`docs/economic-validity-lens.md`（新建）
6. **Trial registry YAML**（准备但**不写入 ledger**）

## 完成后需要更新

1. 本文件头部 `状态` 从 "owner-gated" 更新为 "completed"。
2. Orchestrator 更新 `state/handoff.md`，记录 STRATEGY-NEXTOPEN-001 trial 准备完成。
3. 任务完成后移入 `tasks/completed/TASK-RES-04-nextopen.md`。

## 依赖顺序

```text
AUD-00 COMPLETE
├── AUD-01~05A COMPLETE
├── RES-01/02/03 (baseline ladder) → owner GO → Engineer → Verifier → Reviewer → COMPLETE（并行）
└── RES-04 (next-open) → owner GO → Engineer → Verifier → Reviewer → COMPLETE（与 RES-01/02/03 并行）
```

## See also

- `reports/audits/2026-07-31-quant-llm-research-audit.md` §4.3, §8.2, §11 P2
- `decisions/ADR-010-sesoi-tost-sequential-gate.md`
- FINSABER (Li et al. 2025) — next-open、slippage、liquidity 工件参考
- `runs/ledger.jsonl` #31/#32（frozen B/C strategy returns）
