# Commit 8fa8b10bdbdfb3eccb4ca19ef6777edd472cae89 审查报告

**提交信息**: docs(phase-e2): pre-reg v0.1 — LLM macro-causal (cutoff-controlled) design（2026-07-29，Rethymus）
**改动范围**: 1 个文件，+262/-0；新增 Phase E2 预注册设计文档（LLM 宏观因果链假设生成器，run DEFERRED）。

## 四维度结论
| 维度 | 结论 | 一句话说明 |
|---|---|---|
| 稳定性 | ✅ | 纯文档，无运行代码；明确 run DEFERRED、不含任何 OOS 结果 |
| 可扩展性 | ✅ | 冻结清单/账本规则/控制门结构清晰，v0.2+ 扩展点已显式预留 |
| 生产可用 | ✅ | 防泄漏设计承重（cutoff 门 + structural-only + LAP 审计 + E3 前向兜底）符合项目红线 |
| 高内聚低耦合 | ✅ | 复用 two_arm / pit_audit / phase_c_controls / universe 等既有模块，未引入新耦合 |

## 对照参考
不适用（纯设计文档，无新逻辑实现）。文档自身的统计学设计（双尾 differential、MBB-DM + HAC、placebo 重连、cutoff-era 分层）与 OSF/CLAIR 预注册最佳实践方向一致；§7 功率算术（1.96×0.06/√15≈0.030）自洽。

## 问题清单
### P3-1 §6 标题「N=4」与正文「N=5」不一致
- 描述：标题为「多重检验审计（**第 4 条 confirmatory → N=4**）」，但正文写「**E2 = 第 5 条 → family N=5**（B=1, C=2, D=3, E1=4, E2=5）」。标题疑为从 E1 预注册复制后未更新，按正文口径 E2 加入后家族应为 N=5。
- 位置：`docs/phase-e2-preregistration.md:141`（§6 标题行）
- 影响范围：仅文档可读性；若读者按标题理解家族规模，会低估多重检验校正的 N。
- 修复建议：标题改为「第 5 条 confirmatory → N=5」。
- 修复成本：低
- 状态：未修复（git log 确认该文件此后无任何 commit 改动）

## 总体评分
9/10 — 防泄漏纪律与诚实声明（缓解非消除、功率塌缩自曝）质量很高的设计文档，仅存一处标题级计数不一致。
