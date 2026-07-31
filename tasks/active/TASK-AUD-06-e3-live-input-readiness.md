# AUD-06 — Add a fail-closed E3 live-input readiness gate

- 编号: AUD-06
- 标题: Prove that an E3 commit targets the requested live session with complete PIT inputs before any score can be sealed.
- 状态: **awaiting owner steer — blocks E3 Slice 6/7 launch acceptance**
- Priority: **P0**
- Size: **M**
- Risk: **HIGH**（E3 首次前向序列不可逆；当前 runner 可对旧 labeled date 生成伪“当前”分数）
- 建议 agent role / model tier: **Engineer / strong**；Verifier / strong；Reviewer / strong。
- 目标: 建立一个单一 fail-closed preflight/readiness gate；它在 fit、LLM call、artifact/ledger write 之前
  验证 requested predict session、未实现标签的 test cross-section、PIT universe、input freshness、event text
  与 provider metadata。此任务不启动 shadow 或 headline。
- 背景:
  - runner 只读静态 Phase-B/D caches；price cache 可能早于 requested session，membership 也可能陈旧。
  - `_clean_panel` 会 drop `y_fwd_ret` NaN，真实当前 cross-section 因 future label 未实现而消失。
  - `run_forward_commit` 取 panel max labeled date，不使用 requested `predict_ts`；live call 未传 membership。
  - `_events_df` 将 text 全置空，LLM edge 被静默跳过；`provider_cutoff` 被填成 predict timestamp。
- 依赖: AUD-01 PASS；实现可先开始，但 launch readiness 只有 AUD-04/AUD-05 PASS 后才能 PASS；
  之后才进入 existing E3 Slice 6 scheduler 与 Slice 7 E2E。
- 允许修改: `src/aionis/eval/forward_commit_runner.py`、`src/aionis/eval/forward_commit.py`；
  仅为“train drop unresolved labels / test retain unknown label”可最小新增 forward-specific panel helper，
  不得改变历史 `_clean_panel` 行为；相关 `tests/test_forward_commit_{core,runner,invariants}.py`，可新增
  `tests/test_forward_live_readiness.py`。必要的新 readiness dataclass/helper 限 `src/aionis/eval/`。
- 禁止修改: B/C/D/E1 pipeline、historical two-arm behavior、features/learner params、frozen prereg/ADR、
  `runs/ledger.jsonl`、`runs/results/**`、`runs/forward/**`、`data/**`；禁止真实 network/LLM、forward commit/
  reveal、phase run，禁止写 config/score artifact。
- 前置条件:
  - owner 在 headline 前另行批准 membership freshness contract（明确 max age 或 authoritative refresh）；
    本任务不得自行把 2026-04 snapshot 当作 2026-07 足够新。
  - provider metadata 语义明确：model id/version 与可核实 knowledge cutoff 分开；未知 cutoff 记录
    `unknown` 并由 owner 决定是否阻断，绝不可伪填 predict timestamp。
- 实施要求:
  - `predict_session` 由 requested timestamp + NYSE calendar 得到；test rows 必须正好等于该 session。
  - train 只包含已实现 `y_fwd_ret` 且满足 21-session embargo；test 保留尚未实现的 label。
  - price max session 必须覆盖 predict session；fundamental/macro/13D/8-K 每项记录 max source timestamp、
    snapshot timestamp、sha256，且不得晚于 freeze clock；未来/空/过期按合同 fail closed。
  - `membership` 必须传入 fit path，test tickers 与 `constituents_on(t)` 精确一致；记录实际 snapshot date。
  - hybrid config 含 LLM event channel时，所需 primary-document text 为空则 fail closed，不得把全零 edge 当成功。
  - readiness 失败发生在任何 fit、API call、parquet write、ledger append 之前，返回可行动 reason codes。
- 验收标准:
  - [ ] synthetic current panel 在 label unknown 时仍有 requested-date test rows，train 不含 unresolved/future labels。
  - [ ] stale price、future-dated input、缺 membership contract、universe mismatch、empty event text、虚假 provider cutoff
    均在 fit/write 前被确定性拒绝。
  - [ ] requested date 与 panel last labeled date 不同时，绝不回退到后者提交。
  - [ ] readiness PASS manifest 包含各输入 coverage timestamp/hash、membership snapshot date、provider model metadata。
  - [ ] tests spy 证明 failure path 的 fit/LLM/write/ledger call count 全为 0。
  - [ ] 全部验证只用 labeled synthetic fixtures/temp dirs；真实 `runs/`、`data/`、ledger 不变。
- 必须运行的测试: forward readiness 定向 tests；现有 forward core/runner/invariant tests；
  `uv run pytest -q`；`uv run ruff check`；`git diff --check`；只读确认
  `git diff -- runs/ledger.jsonl 'docs/phase-*-preregistration.md'` 为空。
- 失败处理: 任一 live input 无 authoritative PIT/freshness contract 即 BLOCKED/HOLD E3 Slice 6；不得降级为
  warning、旧 cache 或空 LLM edge。两轮后交 owner 选择 source refresh、pure-zero-LLM 新 sequence 或停止。
- 预期产物: forward-specific unlabeled test-panel path、readiness manifest/gate、fail-closed reason codes、
  synthetic integration tests；不产生一次真实 prediction。
- 完成后需要更新: existing `TASK-E3-launch.md` 的 Slice 6/7 dependency、`state/current.md`、
  `state/handoff.md`；headline 仍需 AUD-07 + separate owner GO。
- see: `forward_commit_runner.py:118`、`:142`、`:260`、`:287`；`forward_commit.py:301`；
  `two_arm.py:26`；`docs/phase-e3-implementation-plan.md` I3–I8。
