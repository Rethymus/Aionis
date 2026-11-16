<!-- EXPLORATORY REPLAY — not a claim, not a gate (design: reports/design/2026-11-17-replay-training-ignition.md; zero runs/ledger.jsonl writes; research face untouched) -->

# lessons 库（回放独立 lessons 文件，distilled-from-replay 溯源）

> **用途**：T1 训练期年界检查点蒸馏的**校准教训**沉淀库；真实期（2026-11-30 起）月末
> 会话以 `distilled-from-replay` 溯源标签热启动（设计 §5 件 1）。注入引擎通道=
> `scripts/replay_blackbox.py --lessons`（JSON 数组，top-N 注入预算按冻结 config
> top_n_lessons=3）。
>
> **准入判据（预声明，防噪声拟合）**（replay 铁律 1：拟合度=校准拟合非方向命中）：
> 仅收**校准教训**（p 与经验命中率错配的修正指引，如「此类情境 p 压向 0.5」）；
> **方向规律零准入**（「X 月 IC 偏正」类=噪声拟合，铁律 1 明令禁止）；每条须标注
> 来源块与数据面（哪年哪月记录的 (p,y) 错配）。调参在检查点之间禁用（设计 §4）。
>
> **蒸馏者注记（诚实）**：引擎 v1 的 --lessons 通道=算子侧蒸馏（外部驱动，冻结 config
> injection_budget.source 在案）；GLM 侧反思-蒸馏循环=设计 §5 完整版，待引擎演进批。

## 条目（append-only；空库=零完成块如实状态）

（截至 2026-11-17 05:42 收档：T1 0/10 块完成——GLM 账户/平台限速阻塞，见
t1-breakpoint.md；零完成块=零 (p,y) 错配数据面=零蒸馏证据，空库为诚实状态非疏漏。
恢复续跑后按上列准入判据逐检查点补录。）
