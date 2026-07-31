# AUD-05 — Enforce the >=2-second fetch politeness contract

- 编号: AUD-05
- 标题: Centralize and test minimum request spacing plus bounded exponential backoff for research fetchers.
- 状态: **coordination only; AUD-05A/05B COMPLETE; 05C C1/C2/C3/C5 downstream gates remain**
- Priority: **P0**
- Size: **L — split into policy primitive, approved-adapter integration, and uncovered-boundary disposition**
- Risk: **HIGH**（横跨 live ingest；错误实现可导致封禁、重复请求或不可测试的长 sleep）
- 建议 agent role / model tier: **Engineer / strong**；Verifier / strong；Reviewer / strong。
- 目标: 用可注入 clock/sleeper 的共享 policy 实现“同一 host 任意连续 fetch ≥2s + bounded exponential
  backoff”，并让 B–E3 的真实数据 fetch 路径统一采用，测试零真实等待/零网络。
- 背景: 项目规则要求所有 fetch ≥2s；当前 Tiingo/Alpaca 为 1s、yfinance 0.4s、SEC 路径 0.15s，
  `events.py`/`universe.py` 等单次调用也没有统一 contract。散落 sleep 无法证明跨函数/host 的间隔。
- 依赖: AUD-01 PASS；AUD-04 先移除 blocked market adapters，避免为禁用路径建设 policy。
- 允许修改: 可新增 `src/aionis/ingest/http_policy.py`；仅为接入共享 policy 可最小修改
  `src/aionis/ingest/{market,fundamentals,events,universe,stakes_13d,stakes_13d_efts,event_text,cik_resolver}.py`、
  `src/aionis/features/macro_surprise.py`、相关 hermetic tests。若 inventory 发现其他 research fetcher，
  先在任务证据中列出并请求 Planner 扩白名单，不得越界。
- 禁止修改: LLM provider选择/模型、feature/label/config、forward ledger、phase scripts、frozen prereg/ADR、
  `runs/**`、`data/**`；禁止真实 HTTP、长时间 sleep 测试或无限 retry。
- 前置条件: 生成 durable request-site inventory，区分 data HTTP、LLM API、health-check；本任务覆盖
  B–E3 research data fetch，未覆盖项必须显式 BLOCKED/backlog，不得声称“all fetches”已完成。
- 实施要求:
  - policy 以 monotonic clock 计时、按 host 协调，首请求可立即发出；后续请求发出前保证 ≥2.0s。
  - retry 次数有硬上限，延迟为至少 2/4/8... 秒的指数退避，可尊重更长 `Retry-After`；4xx（除 429）fail fast。
  - clock/sleep 可注入；单元测试推进 fake time，不执行真实 2 秒等待。
  - cache hit 不发请求也不 sleep；异常日志不包含 key/secret；并发情况下 contract 不被绕过。
  - 不把 SEC “≤10 req/s”当成覆盖项目更严格的 ≥2s 规则。
- 验收标准:
  - [ ] inventory 内每个 covered request site 通过共享 policy，代码不再有 0.15/0.4/1.0s 自定义间隔。
  - [ ] fake-clock tests 验证同 host ≥2s、不同 host policy、429/5xx backoff、永久 4xx fail-fast、retry bound、cache hit。
  - [ ] 全套 tests 在正常时间内完成，无真实网络/真实 sleep。
  - [ ] E3 forward collectors 通过其复用的 SEC/FRED path 继承相同 policy，且无重复 rate limiter。
  - [ ] secrets/data/ledger/results 无变化。
- 必须运行的测试: 新 policy 定向 tests；受影响 ingest/feature tests；`uv run pytest -q`；
  `uv run ruff check`；`rg -n "sleep\((0\.15|0\.4|1\.0)" src/aionis`；`git diff --check`。
- 失败处理: 若某 SDK/host 无法通过共享 wrapper 强制间隔，STOP 并把该 site 标为 BLOCKED；不得
  用注释宣称合规。两轮后仍有 uncovered real fetch path，交 owner 决定禁用该 path 或另建 S-task。
- 预期产物: durable request-site inventory、共享 politeness primitive、全部 covered adapters 与 fake-time tests。
- 完成后需要更新: `state/current.md`、`state/handoff.md`；完成后从 backlog 删除本候选。
- see: `CLAUDE.md` Politeness；`docs/data-intake-rubric.md` G7；`market.py:73`/`:122`；
  `fundamentals.py:92`；`stakes_13d.py:84`；`stakes_13d_efts.py:125`。

## 2026-07-31 read-only preflight

- Request sites span market, SEC, FRED/ALFRED, Fed, GitHub membership, and feature adapters; E3 reuses the
  SEC/FRED paths. The current M-sized task is too broad for one Engineer.
- Required order: policy primitive + fake-clock tests; approved adapter integration; then explicit
  disable/backlog decisions for blocked BLS and uncovered SDK/model/health-check boundaries.
- Do not build a compliant transport for a blocked source. AUD-04 must finish first, and each resulting
  slice needs its own Engineer, Verifier, and Reviewer.

## Resliced execution order

1. `TASK-AUD-05A-http-policy-primitive.md` — COMPLETE.
2. `TASK-AUD-05B-approved-adapter-integration.md` — P0/M; ready for Engineer.
3. `TASK-AUD-05C-uncovered-boundary-disposition.md` — P0/M; held until 05B APPROVE.
