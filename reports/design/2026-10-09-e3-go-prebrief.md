# E3 点火 GO 路径——业主预审简报（2026-10-09，轮 242）

> 性质：业主解锁"E3 点火 GO 路径"后的第一份交付。目的：把 10-31 评估点的 GO 裁决
> 变成一次 10 分钟可读的决策。**本简报不含任何 outcome-bearing 指标观测**（ADR-010
> 边界：揭盲前不得作 confirmatory 检视；影子数据仅作运行证据）。
> 正式证据包由 10-31 自动化（automation-094c3b3a）产出：
> `reports/audits/2026-10-31-headline-goe-evaluation.md`。

## 1. 🔴 本简报的核心发现：10-31 面临确定性 fail-closed（可修，须在 10-31 前修）

**9-30 fail-closed 根因**（`runs/ops_local_refresh/2026-10-01-shadow-runbook.log`）：

```
readiness_predict_session_not_in_panel
  panel_max=2026-07-31  requested=2026-09-30   → READINESS FAILED, 未 fit/commit
```

**根因不是数据坏，是链上没有时间轴推进器**：

- E3 消费 `data/cache/phase_b_prices_e3.parquet`（时间边 = 基础研究面板的边）
- 基础面板 `phase_b_prices.parquet` 由冻结 config 钉死（H6：重跑逐位一致，**设计上不前伸**）
- runbook 步 ⓪b 的 `e3_extend_prices.py` **只补缺失 ticker 列到现有边**
  （`predict_session = px.index.max()`——代码证实从不延长行），残留 gap 检查也因此恒空
- 当前 E3 面板时间边 = **2026-08-31**（本简报实测）

**推论**：若无干预，10-31 的 ③ 步将在 `requested=2026-10-30 > panel_max` 上
**确定性复现同类 fail-closed**——两个影子月全部无 readiness PASS，GO 评估只能
NO-GO/延后。08-31 影子月当时 PASS 是因为面板边恰好 = 08-31（历史一次性对齐）。

**修复提案（下一轮实施，S/M 级）**：`e3_extend_prices.py` 增加 `--through YYYY-MM-DD`
——对全部面板 ticker 自边+1 拉到目标日（复用 `fetch_price_series` 双源兜底+礼貌），
**只延长 `_e3` 面板的行**（冻结基础面板一个字节不动，H6 无涉；预注册 §8 "E3 是
LIVE PROCESS"明文允许数据前伸）；10-31 runbook 的 ⓪b 改带 `--through 2026-10-30`。
修后可用 9-30 做干跑验证：面板补到 09-30 后重放 `--run-date 2026-09-30` 应越过该
具体门（后续门另计）。

## 2. GO 裁决判据全集（预注册锚点逐条）

| # | 判据 | 锚点 | 当前状态（预填） | 10-31 将变什么 |
|---|---|---|---|---|
| 1 | **影子 ≥2 个月且 readiness PASS** | 业主 2026-07-30 决策（TASK-STRAT：shadow 1–2 mo）；轮 59 | 08-31 PASS ✓；9-30 fail-closed（数据新鲜度，非方法学） | +10-31 实况；**若 §1 不修则 0/2 PASS** |
| 2 | AUD-06 两契约冻结 | `forward_live_readiness.py` 参数化 owner contracts | ✅ 已冻（2026-08-03 业主批准：membership_freshness / provider_cutoff） | 不变 |
| 3 | ADR-010 序贯门冻结（SESOI ±0.010 / HAC-TOST 90% / OBF / n_trials=30） | ADR-010 四冻结值 | ✅ 已冻（registry 级） | 10-31 起 look-1 读数入证据包 |
| 4 | 前向随机走带判据（live 形式的"可区分于 0"） | 预注册 §6 | 累积月数尚少（带内游走=与零技能不可区分） | look-1 RCI 读数 |
| 5 | 账本纪律（commit-then-reveal、append-only、零回写） | 预注册 §9 | ✅ 9-30 实战零写入（SHA 前后一致 0924ce2b） | 10-31 同款核验 |
| 6 | headline 仍为业主人工门 | ADR-010 明文 "does not ignite E3" | 本简报即服务该门 | 证据包+建议呈业主 |

## 3. 9-30 fail-closed 的 GO 含义（如实）

- readiness 门**按设计工作**：拒绝在陈旧价格上 fit——这是防泄漏纪律的胜利，不是事故
- 但"影子满 2 月"的字面满足（跑了两次 runbook）≠ 判据 1 的实质（2 个 readiness PASS）；
  10-31 证据包已预定将 9-30 如实呈现为 NOT-APPLICABLE/FAIL
- **修复 §1 后**：9-30 可授权干跑重放（面板补到 09-30 → 该月 readiness 可 PASS →
  判据 1 变 1/2 起步 + 10-31 实况凑满）——是否重放 9-30 属业主一次决策
  （预注册影子语义下，重放须在 10-31 证据包产出前完成并如实标注"补跑"）

## 4. 建议骨架（10-31 证据包将展开）

- **GO**：判据 1-5 全 PASS 且 look-1 RCI 在序贯界内 → 点火前向累积（仍从点火日起零月）
- **NO-GO/延后**：任一硬判据 FAIL（如 §1 未修导致 0/2 PASS）
- **GO 与信号无关**：GO = 允许开始累积前向证据；不是"有信号"——null 仍是合法最可能结局

## 5. 边界

本简报 = docs/研究 lane；0 ledger / 0 frozen / 0 OOS；未观测任何 outcome-bearing 指标。
