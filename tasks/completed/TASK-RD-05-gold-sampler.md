# RD-05 — Gold-set 确定性采样 manifest（离线）

- 编号: RD-05
- 标题: 构建不含真实文本的确定性分层采样 manifest。
- 状态: **COMPLETE — Verifier PASS + Reviewer APPROVE (2026-08-01)**
- Priority: **P1**
- Size: **M**（90–120 分钟）
- Risk: **MEDIUM**
- 目标: 从 labeled synthetic filing metadata 生成按 event type/year/sector 分层的确定性 sample manifest，
  为未来人工标注准备，不拉取或复制真实文本。
- 背景: gold set 若先看模型输出或结果再选样本，会产生选择偏差；采样规则必须 outcome-blind 冻结。
- 允许修改: `src/aionis/extraction/gold_sampler.py`、`tests/test_gold_sampler.py`。
- 禁止修改: `data/**`、EDGAR fetchers、真实缓存、ledger/results/config/prereg/ADR/state。
- 前置条件: RD-04 APPROVE；owner 授权 RD-05。
- 实施要求: 输入字段固定为 `event_id,event_type,filed_ts,sic_sector,source_text_sha256`；调用者显式传入
  `as_of_ts` 与 `quota_by_stratum[(event_type, year, sic_sector)]`，本任务不使用运行时当前时间，也不
  发明默认样本量。拒绝 `filed_ts > as_of_ts`。先按
  `(event_id,source_text_sha256)` 去重（冲突 hash 直接拒绝），再在每个 stratum 按
  `sha256("0|" + event_id + "|" + source_text_sha256)` 升序，hash 并列按 event_id 升序，取前 quota。
  稀疏 strata 取全部并在 `shortfalls` 记录 requested/selected；未在 quota map 的 strata 不抽样并记录
  `unrequested`。manifest 行按 `(event_type,year,sic_sector,selection_hash,event_id)` 排序；manifest id
  是对 UTF-8、sorted-key、紧凑 JSON lines（末尾单一换行）的 sha256。拒绝未来/缺 filed time/非法 hash。
- 验收标准: 固定配额手算结果、输入排列不变、重复/冲突、稀疏/未请求 strata、canonical manifest hash
  全部有 oracle；不含文档正文或 outcome。
- 必须运行的测试: `uv run pytest -q tests/test_gold_sampler.py`; `uv run ruff check`。
- 失败处理: 真实语料许可或采样总体不清时 HOLD；不得临时联网补样本。
- 预期产物: sampler、manifest schema、synthetic tests。
- 完成后需要更新: 由 Orchestrator 更新 state/handoff。
