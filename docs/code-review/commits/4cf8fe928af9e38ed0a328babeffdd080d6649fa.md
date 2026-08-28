# Commit 4cf8fe928af9e38ed0a328babeffdd080d6649fa 审查报告

**提交信息**: docs(results): Phase D null — 3/3 publishable (agent update)（2026-07-29，Rethymus）
**改动范围**: 1 个文件，+28/-23；`docs/RESULTS.md` 把 Phase D 从 PENDING 更新为 confirmatory #3（NULL SUPPORTED，可发表），并同步快照表/证据索引。

## 四维度结论
| 维度 | 结论 | 一句话说明 |
|---|---|---|
| 稳定性 | ✅ | 纯文档 |
| 可扩展性 | ✅ | 表结构沿既有三列模板扩展，证据索引追加 #33/#34 |
| 生产可用 | ✅ | 全部数字与 ledger 逐项对账一致（见下） |
| 高内聚低耦合 | ✅ | 只改结果快照文档，不涉代码 |

## 对照参考
不适用（文档更新）。对账验证：arm_rel 0.01233 / arm_base 0.01531 / differential −0.00298 / DM-p 0.597 / CI [−0.01371, 0.00775] / ci_half 0.01073 / placebo DM-p 0.538 / LOO（去 peer_mom +0.0022、去 stakes −0.0062）全部与本 commit `runs/ledger.jsonl` 第 34 行（confirmatory:first D，sig d3158063…）精确一致；`#33 config_committed` 先于 `#34` 存在，顺序正确。文档所写产物路径 `runs/results/d3158063…/{ic_state,ic_base}.parquet` 与 `eval/phase_d.py:237-238` 的 `save_run(sig, ic_state=ic_r, …)` 一致（ic_state 是 legacy 兼容键、内容为 arm_rel，代码内有注释）。

## 问题清单
### P3-1 「三阶段最紧」的比较基准不完全同类
- 描述：一句话结论称 Phase D differential "CI 半宽 0.0107 < 0.015 且跨 0，**三阶段最小**"。但 Phase B 的 differential 自身 ci_half 从未单独入账（同表"注"已承认），"三阶段最小"实际是 D(0.0107) vs C(0.0130) 的 differential 对比加上 B 的**单臂** ci_half（0.0150–0.0160）——严格说 B 的 differential 半宽是未知项，措辞略超证据。
- 位置：`docs/RESULTS.md:29-31`（一句话结论）
- 影响范围：仅表述精度；表格"注"已如实披露 B 缺项。
- 修复建议：改为"已记录的 differential 中最紧（B 未单列，见注）"。
- 修复成本：低
- 状态：未修复

## 领域红线核查
- 账本纪律 ✅：文档更新基于已入账的 #33（config 先行）→ #34（结果）顺序，无"先看结果后补冻结"痕迹；"无 Phase D 策略行"的诚实标注避免了夸大 strategy-return 覆盖面。
- 双尾纪律 ✅：CI 跨 0 未宣称正向，null 判定以 CI 半宽门（<0.015）表述一致。

## 总体评分
9/10 — 数字全部可对账、判读克制、诚实披露 B 缺项；仅一处措辞略超证据（P3）。
