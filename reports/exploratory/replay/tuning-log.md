# tuning-log — 训练期调参日志（EXPLORATORY REPLAY，append-only）

> 纪律（设计 §4）：年界检查点内逐轮不调参；每条 delta 记 旧值/新值/依据轮次区间。
> 隐式试验计数（arXiv:2608.27734 口径）：每旋钮类累计改动次数——**含未落 delta 的
> 隐式试错**（改了又改回、prompt 微调重试）——训练轨迹搜索强度可审计。

## 隐式试验计数器（累计，逐次 +1，含隐式试错）

- prompt_template: 0
- bucket_cuts: 0
- top_n_lessons: 0
- bounded_context: 0
- thresholds: 0

## 调参 delta 表（append-only，不回改；写错=文末勘误行）

| 日期 | 检查点(年界) | 旋钮类 | 旧值 | 新值 | 依据轮次区间 | 计数器变化 |
|---|---|---|---|---|---|---|
