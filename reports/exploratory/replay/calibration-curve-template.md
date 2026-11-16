<!-- EXPLORATORY REPLAY — not a claim, not a gate (design: reports/design/2026-11-17-replay-training-ignition.md; zero runs/ledger.jsonl writes; research face untouched) -->

# 校准曲线模板（125 点 reliability curve——T1 恢复数据在档后填充）

> 数据源=`runs/<ts>-t1/month-records.jsonl`（p、y、month、answer_coerced_from_string）；
> 分桶=冻结 config bucket_cuts=[0.5,0.6,0.7,0.8,0.9,1.0]（顶部桶含 1.0，与
> monthly_review 校准呈现同界）；BSS=1−BS/BS_base（p̄=全窗 y 命中率，
> scripts/monthly_review.py `_bss_components` 单一实现）。

## 表面（恢复续跑后由 jsonl 聚合渲染）

- **可靠性表**：p∈[0.5,0.6)/…/[0.9,1.0] 各桶 n/命中/Wilson 95% CI/p 原值计数
  （引擎 chunk_summary_lines 输出即此面，逐块+全窗两节）。
- **可靠性曲线点**：每桶 (桶中点, 经验命中率)，n≥5 的桶入图；n<5 如实注记不画。
- **分年轨迹**：2016→2025 各年 Brier/BSS/ECE（分年聚合，调参轨迹可归因面）。
- **诚实性读数**：BSS≈0=诚实成功（设计 §9），BSS>0 宣称须先排除算术 bug 与噪声
  拟合（arXiv:2406.16964 并排 T0 口径——T1 与 T0 基准 runs/20261116-175239-t0
  （训练窗 p̄=0.5167）并排呈现，禁单独引用 T1 BSS。
