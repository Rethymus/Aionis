# RD-14 — 无指标 reproducibility capsule

- 编号: RD-14
- 标题: 汇总代码、lock、config、schema、parser 与输入 manifest hash。
- 状态: **PLANNED — not implementation-authorized**
- Priority: **P1**
- Size: **M**（90–150 分钟）
- Risk: **MEDIUM**
- 目标: 生成不含 outcome/IC/return 的 versioned capsule，固定 `uv.lock`、git tree/config、validation
  manifest、gold schema、parser、provider metadata 与 raw-response hash，支持离线 replay 审计。
- 背景: 远程模型即使 temperature=0 也不保证重调 bit-identical；H6 应固定已观察原始响应和解析栈。
- 允许修改: `src/aionis/reporting/reproducibility.py`、`tests/test_reproducibility_capsule.py`。
- 禁止修改: provider client、真实 cache/data、ledger/results/forward/config/prereg/ADR/state。
- 前置条件: RD-02、RD-04、RD-07 APPROVE；owner 授权 RD-14。
- 实施要求: 调用者显式传入 paths/hashes；原子写、默认拒绝覆盖；不得自动调用 git/network/model；
  capsule schema 不允许指标字段。
- 验收标准: 同输入 byte-identical；任一 hash 变化产生新 capsule id；缺 load-bearing hash fail closed；
  扫描确认无 IC/return/outcome payload。
- 必须运行的测试: `uv run pytest -q tests/test_reproducibility_capsule.py`; `uv run ruff check`。
- 失败处理: 若需读取真实结果或 ledger，BLOCKED 并缩小实现。
- 预期产物: capsule builder、schema、hash mutation tests。
- 完成后需要更新: 由 Orchestrator 更新 state/handoff。
