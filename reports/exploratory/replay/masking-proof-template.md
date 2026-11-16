<!-- EXPLORATORY REPLAY — not a claim, not a gate (design: reports/design/2026-11-17-replay-training-ignition; zero runs/ledger.jsonl writes; research face untouched) -->

# 掩蔽证明汇总（模板——T1 恢复续跑后逐块填充）

> **结构掩蔽的可审计事实面**（设计 §2 铁律 3：掩蔽证明随轮归档，arXiv:2601.13770
> 标准类 LLM 参数化前视不可假设消除→「没偷看」=可审计事实非声称）。本模板定义汇总
> 结构；数据由 `runs/<ts>-t1/month-records.jsonl` 的 per-month 字段聚合（引擎已逐月
> 记录 snapshot_sha256/rows_used/masking_ok + prompt 全文）。

## 汇总表（逐月一行；恢复续跑后由 month-records.jsonl 聚合）

| 月 | rows_used | 行数断言 rows_used==|{m<t}∩series| | context 快照 SHA256(前 12 位) | prompt_sha256(前 12 位) | coercion 标记 |
|---|---|---|---|---|---|
| （待续跑填充） | | | | | |

## 验证协议（恢复续跑后执行，本批未跑=如实注记）

1. 行数断言复算：对每月 t，`rows_used == len([m for m in series if m < t])`
   （引擎 assert_masking 已强制，exit 7 兜底；汇总层复算=二次证明）。
2. 快照 SHA 复现：`snapshot_sha256(truncated_context(series, t, recent_k))` 重算
   与月记录 snapshot_sha256 逐月比对——「上下文恰为 t-1 前自产统计」可由任何第三方
   从冻结 config 的 y 源与 recent_k 复现。
3. prompt 审计：逐月 prompt 全文在 jsonl 在档——人工抽查「仅自产滚动统计、零宏观
   叙述/日历锚定叙事」（bounded context 契约，2601.13770 口径）。
4. coercion 审计：answer_coerced_from_string 标记计数如实呈现（非静默转换）。
