# RD-12 — PIT universe membership 合成 oracle

- 编号: RD-12
- 标题: 固定月度截面 universe 的加入、移除、快照与 hash 不变量。
- 状态: **COMPLETE — Verifier FAIL (false BLOCKED; manifest data exists in universe.py) → fixed (additive constituents_manifest_on accessor + 3 unskipped oracles) → re-Verifier PASS + Reviewer APPROVE (2026-08-01)**
- Priority: **P1**
- Size: **M**（90–120 分钟）
- Risk: **HIGH**（survivorship 与 universe leakage load-bearing，但仅测试）
- 目标: 用 synthetic membership history 验证 `constituents_on(t)` 精确返回 t 时点成员，记录 snapshot
  date/age/hash，并拒绝未来 snapshot、静默 forward-fill 与把 588 union pool 当作每月 universe。
- 背景: 588 是可解析候选 ticker 的历史并集，不是每月约 500 个真实成分；后续任务必须保留区别。
- 允许修改: `tests/test_pit_universe_oracle.py`；必要时仅修复 `src/aionis/ingest/universe.py` 的明确缺陷。
- 禁止修改: universe 数据源/fetch、data/ledger/results/config/prereg/ADR/state、forward runner。
- 前置条件: owner 授权 RD-12。
- 实施要求: 覆盖同日加入/移除、边界日期、无历史 snapshot、未来 snapshot、重复记录、snapshot age；
  不联网、不读取真实 universe cache。
- 验收标准: 每月成员精确匹配 oracle；无 forward-fill；manifest 含 snapshot date/age/hash；union pool
  与 contemporaneous membership 的混用被测试拒绝。
- 必须运行的测试: `uv run pytest -q tests/test_universe.py tests/test_pit_universe_oracle.py`；
  `uv run ruff check`; `git diff --check`。
- 失败处理: 若需要新的权威 universe source 或 freshness 阈值，BLOCKED 并交 owner/AUD-06。
- 预期产物: synthetic membership fixtures 与 anti-survivorship oracle。
- 完成后需要更新: 由 Orchestrator 更新 state/handoff。
