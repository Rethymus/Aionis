# tuning-log — 训练期调参日志（EXPLORATORY REPLAY，append-only）

> 纪律（设计 §4）：年界检查点内逐轮不调参；每条 delta 记 旧值/新值/依据轮次区间。
> 隐式试验计数（arXiv:2608.27734 口径）：每旋钮类累计改动次数——**含未落 delta 的
> 隐式试错**（改了又改回、prompt 微调重试）——训练轨迹搜索强度可审计。

## 隐式试验计数器（累计，逐次 +1，含隐式试错）

- prompt_template: 0
- bucket_cuts: 0
- top_n_lessons: 0
- bounded_context: 0
- thresholds: 1

## 调参 delta 表（append-only，不回改；写错=文末勘误行）

| 日期 | 检查点(年界) | 旋钮类 | 旧值 | 新值 | 依据轮次区间 | 计数器变化 |
|---|---|---|---|---|---|---|
| 2026-11-17 | 块2016（月 2016-02 契约失败触发） | thresholds（回复契约层） | 无容错 | answer 精确小写 "true"/"false" 字符串→布尔+逐回复 answer_coerced_from_string 标记 | scripts/replay_blackbox.py beb32cd42a | thresholds 0→1 |

## 检查点状态（append-only）

- 2026-11-17 05:42 收档（业主协议 ④ 降级 C）：块级检查点 0/10 到达——零完成块
  （GLM 账户/平台限速阻塞，见 t1-breakpoint.md 时间线）；块2016 尝试中到达的月级
  观察=月 2016-02 契约失败→上表 delta ①（唯一 delta）。无完成块=无分桶/BSS 检查点
  数据面，零调参信号其余旋钮零改动如实记录。
