<!-- EXPLORATORY REPLAY — not a claim, not a gate (design: reports/design/2026-11-17-replay-training-ignition.md; zero runs/ledger.jsonl writes; research face untouched) -->
# T1 chunked replay — window [2016-10..2016-10] (1 year-chunks, 1 months)

## chunk 2016 [2016-10..2016-10] — 1 months
calibration buckets（记录性呈现——呈现≠校准，禁据此调 p 或定阈值；桶界为固定呈现常量）:
  - p∈[0.8,0.9): n=1、命中 0（0.000）、Wilson 95% CI (0.0000, 0.7935)、p 原值：0.85×1
  - 分列不计桶：p<0.5 已对账 0 条（命中 0）、p 未填 0 条、pending 未对账 0 条
  - 汇总 mean Brier = 0.722（n=1，与逐条 (p−y)² 同口径取均值）
  - BSS components: bs=0.722500、bs_base=0.000000、BSS 无定义（p̄=0.0000 退化，诚实降级不造假分）

## full window [2016-10..2016-10] — 1 months
calibration buckets（记录性呈现——呈现≠校准，禁据此调 p 或定阈值；桶界为固定呈现常量）:
  - p∈[0.8,0.9): n=1、命中 0（0.000）、Wilson 95% CI (0.0000, 0.7935)、p 原值：0.85×1
  - 分列不计桶：p<0.5 已对账 0 条（命中 0）、p 未填 0 条、pending 未对账 0 条
  - 汇总 mean Brier = 0.722（n=1，与逐条 (p−y)² 同口径取均值）
  - BSS components: bs=0.722500、bs_base=0.000000、BSS 无定义（p̄=0.0000 退化，诚实降级不造假分）
