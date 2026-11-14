# state/calibration-months.md — 月末对账快照存档（append-only durable registry，ADR-006 合规）

> iterate 轮 12 `cross-month-evolution` 新建（2026-11-14）。**属月判据=对账月**（outcome
> 到达月，与对账时点纪律同族）。每月末会话从 `--lessons` 月报 §5「本月快照行」**人工
> append** 一行入本档（呈报-入册分离：引擎只渲染、绝不写本档——与 backlog 卡区人工
> 维护同模式）。**零 resolved 月不存档**（基线月无截面可记）。
>
> 行契约（机器可解析，`parse_calibration_snapshots` 消费）：
>
> `- YYYY-MM: p∈[0.5,0.6): n=1、hit 0.000 | …各 populated 桶… | Brier=0.270、BSS=-0.125、p̄=0.400`
>
> 退化月（全部 y 同值，BSS 无定义）尾段：`Brier=…、BSS 无定义（p̄=… 退化）、p̄=…`。
> 行 append-only 不回改；写错=文末勘误行更正（handoff 同款纪律）。
>
> 演进消费：下月 `--lessons` §5「跨月校准演进」自动对照本档最近 prior 月渲染两窗口
> 变化行（`calibration_evolution_lines`）——仅方向与幅度呈现，禁趋势拟合/斜率宣称/
> 显著性，不设自动判优/劣门（runbook「演进视图口径」子节）。

## 快照行（append-only，自 2026-11 起）

<!-- 2026-11 基线月：prediction:/outcome: 双零 0/0（2026-11-14 实测），零 resolved
     不存档——首个快照行预期 2026-12 月末对账后落地 -->
