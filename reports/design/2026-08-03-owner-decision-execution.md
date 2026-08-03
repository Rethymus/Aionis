# 2026-08-03 owner-decision-execution.md — 批准决策执行记录

> 依据:owner 2026-08-03 批准全部推荐项。本文件为每项决策的执行证据与事实修正,
> 确保"record-once"(ADR-006)且可审计。

## D1 — Track B config 冻结 ✅ 已合规(核实确认,无需新行)

- **事实核实**:ledger 已含 config_committed 行 #41(`bf620bd...`,23 特征 FROZEN)+ #42(`9af9e8b...`,price-only baseline,`companion_to_row: 41`),均标注 FROZEN 2026-08-02;
  `docs/track-b-preregistration.md` 标注 "(FROZEN 2026-08-02)"。
- **裁决**:config_committed 先于 result 的铁律已满足;首个差分结果(mean_diff +0.0076, CI 跨零, p=0.219)基于已冻结配置观测,是合法 null。
- **执行**:无需新 ledger 行;本记录为确认。

## D2 — AUD-06 两个 owner 合约参数 ✅ 冻结(E3 启动前置)

- `membership_freshness_contract = MembershipFreshnessContract(max_age_sessions=22, authoritative_refresh=None)`
  - max_age_sessions=22(≈1 个月 NYSE 会话):符合"2026-04 快照不可视为 2026-07 新鲜"语义。
  - authoritative_refresh=None:**事实修正** — 项目无独立 universe 刷新脚本;以 `scripts/phase_b_fetch.py` 为刷新入口。如实标注,不编造路径。
- `provider_cutoff_policy = ProviderCutoffPolicy(block_on_unknown=True)`:fail-closed,未知 cutoff 阻塞就绪(与 C1 fail-closed 一致)。
- **影响**:E3 Slice 6/7(scheduler/E2E)可进入实现;headline 仍待独立 owner GO(ADR-010)。
- 记录于 `tasks/active/TASK-E3-launch.md` 前置条件区。

## D3 — C5 模型 API politeness 措辞 ✅ 执行

- **Option A 采纳**:≥2s host-spacing 仅适用于 data-fetch 站点(SEC/EDGAR/FRED/Tiingo/Alpaca/PRAW);model APIs(GLM/SiliconFlow/ModelScope)由 provider RPM/TPM + `ProviderRouter` cooldown + idempotent disk cache 约束。
- 理由:GLM RPM 30 时 2s 间隔冗余;SiliconFlow RPM 1000 时 2s 反而有害;SDK 已有 retry/cooldown。
- **执行**:`CLAUDE.md` L49 措辞已更新;`TASK-AUD-05C-C5` 状态 → OWNER-APPROVED。无代码改动(SDK-owned transports 已合规)。

## D4 — Kenneth-French / 选股面板 7-gate ✅ 记录

- **裁决(记录)**:FF 数据无 vintage → 以"声明式 PIT"补偿(标注无 vintage 修订,保守);选股面板声明幸存者偏差"可缓解不可根除"。
- 与 `quant-selection-research.md` §7 已记录的 `purgedcv`(MIT, 已安装) + GKX 月度面板一致。
- 无代码改动;记录待 Track B ⑦市场结构挂接时使用。

## D5 — RES 程序 ✅ 批准重启(需先重写 4 个缺陷规格)

- RES-02/03/08/10 因横截面变异/rank-label/耐久 gold-set/远程确定性缺陷需**先重写规格**再执行。
- 执行状态:批准重启;重写规格为后续任务(非本记录范围)。

## D6 — RD 程序 ✅ 批准 P0+offline RD 全集(已穷尽)

- 安全 RD 队列已全部完成(8 sonnet-tier tasks)。批准范围已执行完毕;剩余 RD 需 owner 逐项授权。

## D7 — KAIROS 验证 ✅ (haiku agent 实证)

- `github.com/mr-sharath/KAIROS` 存在,**MIT License**,与引用用途吻合(二阶效应因果分析, fine-tuned Llama 3 8B)。
- 活跃度低:0 stars / 18 commits / 演示级 → **引用有效,可复用(质量需评估)**。

## D8 — FinLake-Bench 验证 ❌ 修正审计记录

- **确认未公开发布**:arXiv:2510.07920 论文声称 "we release FinLake-Bench" 但全文无任何发布 URL(WebSearch 3 次均无果);论文内部命名不一致(摘要 FinLake-Bench vs Table 2/图 2 FinLeak-Bench)。
- **修正**:审计报告遗留项从"链接未找到"升级为"确认未发布、命名不一致"—— 如需用作记忆探针,建议邮件索取或自建等价探针。

## 汇总

| # | 决策 | 状态 |
|---|---|---|
| D1 | Track B config 冻结 | ✅ 已合规(核实确认) |
| D2 | AUD-06 两参数 | ✅ 已冻结 |
| D3 | C5 politeness 措辞 | ✅ 已执行 |
| D4 | FF 7-gate | ✅ 已记录 |
| D5 | RES 重启 | ✅ 批准(先重写规格) |
| D6 | RD 全集 | ✅ 已穷尽 |
| D7 | KAIROS | ✅ 已验证(MIT) |
| D8 | FinLake-Bench | ❌ 确认未发布 |

无冻结面/ledger 变更;仅记录与任务状态更新。真实网络仅由验证 agent 用于引用核实。
