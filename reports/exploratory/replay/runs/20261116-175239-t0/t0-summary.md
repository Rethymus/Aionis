<!-- EXPLORATORY REPLAY — not a claim, not a gate (design: reports/design/2026-11-17-replay-training-ignition.md; zero runs/ledger.jsonl writes; research face untouched) -->
# T0 climatology run — window [2016-01..2025-12] (120 months)
- p̄ = 0.516667 (constant over the window; full-window hit-rate climatology)

calibration buckets（记录性呈现——呈现≠校准，禁据此调 p 或定阈值；桶界为固定呈现常量）:
  - p∈[0.5,0.6): n=120、命中 62（0.517）、Wilson 95% CI (0.4281, 0.6042)、p 原值：0.516667×120
  - 分列不计桶：p<0.5 已对账 0 条（命中 0）、p 未填 0 条、pending 未对账 0 条
  - 汇总 mean Brier = 0.250（n=120，与逐条 (p−y)² 同口径取均值）
  - BSS components: bs=0.249722、bs_base=0.249722、BSS=0.000000

- BSS≡0 构造性断言: bss=0.000000000000 → PASS（非零=引擎 bug，exit 5）
