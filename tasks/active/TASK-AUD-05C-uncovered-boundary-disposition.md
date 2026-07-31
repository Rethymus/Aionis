# AUD-05C — Disposition uncovered transport boundaries

- 编号: AUD-05C
- 状态: **DISPOSITION COMPLETE (awaiting owner review of C1-C5 sub-tasks)**
- Priority: **P0**
- Size: **M**
- Risk: **HIGH**
- 目标: 为每个未覆盖边界给出可执行 disposition：BLOCKED、disable、wrapper task 或 owner decision；本任务
  不集成 adapter、不建设 blocked source transport、不运行网络/研究。
- 边界: BLS CPI/NFP、VIX `fetch_vix`/`_download_vix_vintages`、selection-panel FRED/Fama-French、PRAW、
  `scripts/health_check.py`、GLMEmbedder、GLMCausalEdgeClient、OpenAICompatClient/provider router。
- 允许 durable outputs: 本任务文件、`reports/audits/http-request-site-inventory.md`、`state/blockers.md`、
  `state/current.md`/`handoff.md`、必要的独立 decision/task files；不得修改研究代码，除非后续被拆成新的
  C1/C2/C3/C4 Engineer task 并重新过 owner gate。
- 预期 dispositions:
  - C1 P0/S: 禁用 BLS live transport，cache miss fail-closed；不得替换为 BLS polite adapter。
  - C2 P0/S-M: approved FRED SDK wrapper，保持 VIX PIT/no-revision/cache/ledger 语义。
  - C3 P0/S owner-held: PRAW wrapper，source/API terms 先过 7-gate。
  - C4 P0/S owner-held: health-check 去除 blocked/unapproved probes，再决定 shared policy 接入。
  - C5 P0/S decision: 明确 ≥2s 是否适用于 GLM/SiliconFlow/ModelScope model APIs，保持 provider set 不变。
  - Kenneth French/Fama-French：owner/data-intake decision；未批准前 cache miss BLOCKED 或 disable。
- 验收: 每个边界有文件/owner/依赖/停止条件；BLS 明确 blocked+disable；未做任何网络/结果观察；当前状态
  不宣称”all fetches compliant”。
- 依赖顺序: 05B APPROVE → disposition record → owner gates → C1/C2/C3/C4/C5 各自独立任务与验证；05C
  Reviewer APPROVE 后才能解除 AUD-06 的 fetch-readiness 依赖。

## 2026-07-31 Disposition execution evidence

### Per-boundary dispositions produced

1. **BLS CPI/NFP** → **C1: BLOCKED + disable**
   - File: `tasks/active/TASK-AUD-05C-C1-disable-bls-transport.md`
   - Disposition: Remove `requests.get()` to `www.bls.gov`; cache miss → fail-closed
   - Owner gate: BLS blocked per CLAUDE.md data-source constraints
   - Stop-condition: No BLS adapter allowed

2. **VIX `fetch_vix` / `_download_vix_vintages`** → **C2: approved FRED SDK wrapper**
   - File: `tasks/active/TASK-AUD-05C-C2-wrap-vix-fred-adapter.md`
   - Disposition: Wrap `pandas_datareader.get_data_fred()` with shared policy; preserve ADR-003 VIX PIT/no-revision/cache/ledger
   - Owner gate: VIX is critical risk-premium feature; FRED is approved source
   - Stop-condition: Preserve cache/ledger/vintage semantics

3. **selection-panel FRED / Fama-French** → **OWNER-DECISION: data-intake gate**
   - Disposition: NO C-task (owner decision required)
   - Until approved: cache miss BLOCKED or disable
   - Owner gate: Clear 7-gate rubric (`docs/data-intake-rubric.md`) first
   - Stop-condition: Kenneth French data-intake approval

4. **PRAW (Reddit)** → **C3: owner-held (7-gate clearance)**
   - File: `tasks/active/TASK-AUD-05C-C3-praw-wrapper-7gate.md`
   - Disposition: 7-gate (G1-G7) must pass before wrapper integration
   - Owner gate: G6 (selection-honesty) + Reddit ToS/content license approval
   - Stop-condition: If 7-gate fails → disable PRAW live transport

5. **`scripts/health_check.py`** → **C4: owner-held (probe inventory)**
   - File: `tasks/active/TASK-AUD-05C-C4-health-check-probes.md`
   - Disposition: Remove blocked probes (akshare/EastMoney) first; then decide shared-policy hookup
   - Owner gate: Probe inventory + keep-independent vs. integrate-shared-policy decision
   - Stop-condition: Keep approved sources only

6. **GLMEmbedder / GLMCausalEdgeClient / OpenAICompatClient / ProviderRouter** → **C5: owner decision**
   - File: `tasks/active/TASK-AUD-05C-C5-model-api-transport-disposition.md`
   - Disposition: Clarify if ≥2s host-spacing rule applies to model APIs (SDK-exempt vs. all HTTP)
   - Owner gate: Politeness rule scope clarification
   - Stop-condition: Preserve provider set (GLM/SiliconFlow/ModelScope only)

### Disposition table added to inventory

- Updated `reports/audits/http-request-site-inventory.md` with complete disposition table
- Table columns: Boundary | Current state | Disposition | C-task | Owner/dependency | Stop-condition

### C1-C5 sub-task files materialized

- `TASK-AUD-05C-C1-disable-bls-transport.md` (S, LOW risk, disable-only)
- `TASK-AUD-05C-C2-wrap-vix-fred-adapter.md` (M, MEDIUM risk, preserve ADR-003)
- `TASK-AUD-05C-C3-praw-wrapper-7gate.md` (S, MEDIUM risk, 7-gate owner-held)
- `TASK-AUD-05C-C4-health-check-probes.md` (S→M, LOW risk, owner-held)
- `TASK-AUD-05C-C5-model-api-transport-disposition.md` (S→M, MEDIUM risk, owner decision)

### Owner decisions surfaced

1. **C3 (PRAW)**: 7-gate clearance (G6 selection-honesty + Reddit ToS/content license)
2. **C4 (health_check)**: Remove akshare/EastMoney; keep independent vs. integrate shared policy
3. **C5 (model APIs)**: ≥2s rule scope (model APIs exempt vs. all HTTP calls)
4. **Kenneth French (Fama-French)**: Data-intake approval (7-gate rubric)

### Confirmation of constraints

- **NO research code modified** (read-only on ingest/eval/features/extraction/dashboard)
- **NO frozen spec/ledger/data/forward modified**
- **NO state/current.md or state/handoff.md modified** (Orchestrator owns those)
- **NO network/research runs performed**
- **NO E3 outcome metrics observed**

### Next steps

1. Owner reviews C1-C5 dispositions and sub-task files
2. Owner decisions made on C3/C4/C5/Kenneth-French
3. Owner gives GO for C1/C2 (C3/C4/C5 await owner gates)
4. Engineer executes approved tasks independently
5. Independent Verifier validates each task
6. Reviewer approves each task
7. AUD-05C marked COMPLETE → AUD-06 fetch-readiness dependency unblocked

