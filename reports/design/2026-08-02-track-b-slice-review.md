# 轨道 B 切片计划——独立复审

> 日期：2026-08-02
> 复审对象：[`2026-08-02-track-b-s0-s1-slice-plan.md`](2026-08-02-track-b-s0-s1-slice-plan.md)（planner-b 产出）
> 复审者：编排者（代 slice-reviewer——该 agent 在内容回传时触发 `[1301]` 中文安全过滤误判，无法取回；由编排者依据全文直接完成复审）
> 状态：研究建议；不修改任何冻结面/ledger/E3。

## 总体判断

**REQUEST CHANGES — 1 HIGH + 1 MEDIUM + 1 LOW，无 CRITICAL。**

反泄漏不变量完备、OSS 许可证声明准确、依赖图无环——**计划可用，修完 HIGH 即可进入实施**。

## 🔴 HIGH（应修——方法论正确性）

### H-1：§3.2 / S1-M② 等权 baseline 概念错误【已在 (b) 2026-08-02 修订】

**问题**：计划把"等权 baseline"同时表述为"rank-IC=0 概念验证"和"等权组合 forward_return 的 rank-IC"。等权组合没有排序，其 rank-IC 在概念上无定义（恒为 0），**不能**作为 price-only rank-IC 的对照对象。

**正确做法**：等权是**组合收益**基准——与 price-only top-quantile **组合收益**比较；Diebold-Mariano 检验的对象是**收益损失**（loss on portfolio returns），不是 rank-IC。

**修订**：删除"等权 IC"表述，将 S1-M② 重定义为"等权组合收益 vs price-only 组合收益的 DM 检验（loss = 组合收益预测误差）"。

## 🟡 MEDIUM

### M-1：§2.4 / S0-S③ FF5 "vintage 标记"验收具误导性

**问题**：验收标准写"每个 FF5 因子附带 vintage 标记（as-of date）"。Kenneth-French 数据库**不发布 ALFRED 式 vintage**（§6.5 已承认此限制，与验收标准自相矛盾）。

**修订**：改为"记录 FF5 下载日期 + 与历史快照对比修订幅度（若可得）"，并在论文中声明 FF5 因子为"潜在轻微泄漏源"。

## 🟢 LOW

- **L-1**：§3.5 / S1-M③ "新**e**y-West" → **Newey-West**（拼写）。
- **L-2**（Track A 文件，非本计划）：`2026-08-02-track-a-slice-plan.md` 中 "Jennison-Turn**u**bb"（多处）→ **Jennison-Turnbull**。
- **L-3**（Track A 文件）：A1 代码骨架**曾**假设 `chronological_split` / `paired_differential_ic` 函数名——【已修订 2026-08-02：骨架已对齐真实签名 `purged_walk_forward_splits` / `LightGBMFrozen` / `rank_ic_summary` / `differential` / `commit_config`】。

## ✅ 附加确认（无问题）

| 维度 | 结论 |
|---|---|
| **反泄漏不变量** | 完备正确：PIT 对齐（`features.index <= labels.index`）、purged CV 折共享、`fit_start/end` 钉折内训练段（qlib `RobustZScoreNorm` 陷阱已识别）、`forward_return_h` 仅作 label、幸存者屏蔽（`constituents_on(row_date)`）。 |
| **OSS 许可证** | 准确：FINSABER / alphalens-reloaded / pyfolio-reloaded = Apache-2.0；purgedcv / qlib / edgartools = MIT。均通过 permissive-only 规则。 |
| **依赖图（§5）** | 无环；S1-L①/L②/M③/S① 正确依赖 Wave 2（S1-M①）；S1-M③ 正确依赖 S0-S③ + S1-L①。 |
| **qlib Yahoo 数据替换（§6.2）** | 正确，与 v0.2 §6 一致。 |
| **幸存者偏差裁决（§6.1）** | "可缓解不可根除" + 论文诚实措辞，与 v0.2 §8.4 一致。 |

## 建议

修完 **H-1**（S1-M② 重定义为组合收益 DM 检验）即可冻结 (b) 进入实施。M-1 / L-1..3 可在实施时顺带修订，不阻断。
