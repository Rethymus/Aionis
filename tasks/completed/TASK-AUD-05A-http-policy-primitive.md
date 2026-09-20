# AUD-05A — Build the shared HTTP politeness primitive

- 编号: AUD-05A
- 标题: Add a host-scoped, testable request-spacing and bounded-retry policy without adapter integration.
- 状态: **COMPLETE — repair round 1; substantive Verifier PASS with uv launcher exception; Reviewer APPROVE**
- Priority: **P0**
- Size: **S**
- Risk: **MEDIUM**（共享基础件，但本切片尚不改变任何真实 fetch 路径）
- 建议 agent role / model tier: **Engineer / medium**；Verifier / strong；Reviewer / strong。
- 目标: 提供 monotonic-clock、按 host 协调的 >=2.0s 请求间隔与 bounded exponential backoff 基础件，
  用 fake clock/sleeper 密封测试合同；adapter 接入留给 AUD-05B。
- 依赖: AUD-04 COMPLETE。AUD-05B 必须等待本任务 Reviewer APPROVE。
- 允许修改: 新增 `src/aionis/ingest/http_policy.py`、新增 `tests/test_http_policy.py`、新增
  `reports/audits/http-request-site-inventory.md`；更新本任务执行证据。
- 禁止修改: 任何现有 adapter、feature、script、config、provider、ledger/result/data、frozen prereg/ADR；
  禁止真实 HTTP、真实 sleep、后台进程或 adapter 接入。
- 实施要求:
  - monotonic clock + sleeper 可注入；首请求立即通过，同 host 后续请求前间隔 >=2.0s。
  - host key 必须规范化；不同 host 独立；并发调用不能绕过同 host 合同。
  - retry 次数硬上限；退避至少 2/4/8... 秒；`Retry-After` 更长时优先；429/5xx 可重试，
    其他 4xx fail fast；不得记录 secret/header/token。
  - inventory 只记录真实 request sites、host/type/current delay/后续 05B 或 05C disposition，使用
    Fact/Inference/Hypothesis 边界；不得宣称 adapters 已合规。
- 验收标准:
  - [ ] fake-clock tests 覆盖首请求、同/异 host、并发、429/5xx、`Retry-After`、永久 4xx、retry bound。
  - [ ] 所有定向测试零网络、零真实等待且无 nondeterministic wall-clock assertion。
  - [ ] inventory 覆盖 AUD-05 preflight 已识别的 market、SEC、FRED/ALFRED、Fed、GitHub membership、
    feature adapter 边界，并明确 BLS/SDK/model/health-check 未覆盖处置。
  - [ ] diff 仅包含三个允许文件；frozen/ledger/result/data diff 为空。
- 必须运行的测试: `uv run pytest -q tests/test_http_policy.py`；`uv run ruff check
  src/aionis/ingest/http_policy.py tests/test_http_policy.py`；`git diff --check`；只读 frozen-surface diff。
- 失败处理: 若并发合同不能由该 primitive 单独保证，返回 BLOCKED 及最小可行锁模型；不得弱化 >=2s。
- 预期产物: 可独立复核的 policy primitive、fake-time regression tests、durable request-site inventory。

## 2026-07-31 execution evidence

- Engineer added only the three allowed new files. The primitive provides normalized host keys, per-host
  locking, injectable monotonic time/sleeper, >=2s spacing, bounded 2/4/8 retry, Retry-After handling,
  fail-fast non-retryable 4xx, and status-only errors.
- Engineer checks: 14 targeted tests, scoped ruff, diff check and frozen-surface check PASS; no network or
  real sleep. Root integration check with isolated `/tmp` UV cache also passes the targeted tests.
- Independent Verifier found no implementation defect and confirmed the three-file boundary and behavioral
  contract, but its sandbox could not open the default uv cache. This is an environment evidence gap; rerun
  with an explicit writable cache is required before Reviewer approval. Residual risk: host state maps have
  no eviction, and adapters are intentionally not integrated in 05A. A second read-only verifier also found
  and repaired inventory inaccuracies (actual VIX function names and omitted selection-panel SDK boundaries).
  Root isolated-cache verification passes the 14 targeted tests and all-repo checks; the read-only sandbox
  remains unable to execute `uv` because its `/tmp` is mounted read-only. Reviewer APPROVE classified this as
  an environment exception, relying on the root isolated-cache execution evidence.
