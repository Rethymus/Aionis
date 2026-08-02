# Track B 冻结点推荐值（供 owner 一次性裁断）

> 日期：2026-08-02
> 状态：**推荐**——owner 裁断后即可冻结 config sha256（config_committed BEFORE result）
> 对象：[`docs/track-b-preregistration.md`](../../docs/track-b-preregistration.md) §12 的 5 个 owner-decision 点

## 推荐：全部 KEEP proposed 默认值

5 个冻结点均有理论或已冻结 ADR 支撑，且偏向保守（null-favored 项目的正确姿态）。owner 一次性确认即可冻结。

| # | 冻结点 | 推荐值 | 理由 | 改动风险 |
|---|---|---|---|---|
| 1 | **SESOI** | **±0.010**（KEEP） | ADR-010 已冻结；J-T 门（look-specific RCI 99.44/97.64/95.00）构建其上；±0.010 = 交易成本后的经济等价门槛 | 改值需新 ADR + 重算 OBF zₖ；引入选择自由度 |
| 2 | **horizon** | **h=21**（KEEP，confirmatory） | 月频 rebalance 周期；与全家族一致；h=10/42 已声明 exploratory（不计入 verdict） | 钉多值会膨胀 multiplicity |
| 3 | **bin_count** | **5 (quintiles)**（KEEP） | RD-15 已选；ranking 理论稳健默认；deciles(10) 更激进、小盘易过拟合 | RD-15 decision packet 已论证 |
| 4 | **新闻情绪** | **S3 exploratory ablation**（KEEP，不作主 alpha） | 前沿共识：Profit Mirage（51–62% Sharpe 衰减）、Alpha Illusion、Lopez-Lira 2025（参数记忆泄漏）；E3 闭集抽取是唯一低泄漏入口 | 提前进 main claim 需更强泄漏审计，且违 null-favored |
| 5 | **universe** | **接受 2016+ 限制**（KEEP） | Jaccard<0.95 规则；pierrebrunelle 可复现窗口；1996–2016 只作敏感性 | 牺牲 ~5 年样本换可复现性 + 抗幸存者 |

## 不推荐的做法（会损害可复现性 / 增加 multiplicity）

- **冻结前调整 SESOI / horizon / bin_count** → 引入选择自由度，削弱预注册的防 p-hacking 价值。
- **把新闻情绪提前进 main claim** → LLM 参数记忆泄漏风险（Lopez-Lira 2025），且违背 null-favored 立场。
- **扩展 universe 到 1996 前** → hanshof 历史来源不透明 + 无免费退市价 → 幸存者偏差恶化。

## 冻结后的下一步（config_committed BEFORE result）

1. owner 裁断上述 5 点 → `docs/track-b-preregistration.md` 状态 PROPOSED → FROZEN。
2. 冻结 config sha256 写入 `runs/ledger.jsonl`（复用 `reporting.save_run.commit_config`）——**先于任何 OOS rank-IC 观测**。
3. 此后才跑 S0/S1 真实数据（chronological walk-forward）。

## 依赖

- 冻结点 5 的 Jaccard **已由 S0-S① 实测**（[`reports/audits/track-b-universe-audit.md`](../audits/track-b-universe-audit.md)）：min **0.8544 < 0.95**（@2016-01-01，mean 0.9272，已独立复跑核验）→ **强化"接受 2016+ 限制"推荐**。
