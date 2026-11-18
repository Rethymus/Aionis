<!-- EXPLORATORY REPLAY — not a claim, not a gate (design: reports/design/2026-11-17-replay-training-ignition.md; zero runs/ledger.jsonl writes; research face untouched) -->
# T1 chunked replay — window [2026-03..2026-03] (1 year-chunks, 1 months)

## chunk 2026 [2026-03..2026-03] — 1 months
calibration buckets（记录性呈现——呈现≠校准，禁据此调 p 或定阈值；桶界为固定呈现常量）:
  - 分列不计桶：p<0.5 已对账 1 条（命中 1）、p 未填 0 条、pending 未对账 0 条
  - 汇总 mean Brier = 0.231（n=1，与逐条 (p−y)² 同口径取均值）
  - BSS components: bs=0.231471、bs_base=0.000000、BSS 无定义（p̄=0.0000 退化，诚实降级不造假分）

## full window [2026-03..2026-03] — 1 months
calibration buckets（记录性呈现——呈现≠校准，禁据此调 p 或定阈值；桶界为固定呈现常量）:
  - 分列不计桶：p<0.5 已对账 1 条（命中 1）、p 未填 0 条、pending 未对账 0 条
  - 汇总 mean Brier = 0.231（n=1，与逐条 (p−y)² 同口径取均值）
  - BSS components: bs=0.231471、bs_base=0.000000、BSS 无定义（p̄=0.0000 退化，诚实降级不造假分）
