# Preregistration ↔ 冻结契约只读一致性核验（周期 2 · 轮 50）

- **日期**: 2026-08-30
- **性质**: 只读核验报告（零文件改写；证据=各文件 grep/解析实测，逐条附出处）
- **范围**: `config/e3_live_contracts.yaml`（业主批准的 live-readiness 契约）↔ 预注册文档 ↔ 业主决策/探针记录
- **结论**: **一致**——冻结契约的每个值都有明确出处链，无漂移；预注册文档不含操作性契约值属设计分工，非缺失。

## 1. 冻结契约值 ↔ 出处链（逐值）

| 契约值 | YAML 实测 | 业主决策出处 | 一致 |
|---|---|---|---|
| `membership_freshness_contract.max_age_sessions` | `22`（YAML 解析实测） | `reports/design/2026-08-03-owner-decision-execution.md:15`（`max_age_sessions=22`，D2 决策：23 的 PROPOSED 值未被采纳） | ✅ |
| `membership_freshness_contract.authoritative_refresh` | `None` | 同上 `:15`（`authoritative_refresh=None`；刷新入口保持 phase_b_fetch.py） | ✅ |
| `provider_cutoff_policy.block_on_unknown` | `True` | 同上 `:18`（fail-closed，与 C1 一致） | ✅ |
| `provider_cutoff_policy.provider_cutoff` | `"2023-03-10"`（YAML:62，provenance=EMPIRICAL-PROBE-v1 保守下界，YAML:55-57 记录探针结果：KNOWS 2023-03-10 SVB / 未知 2024-11-06+） | `reports/design/2026-08-29-e3-cutoff-advisory.md`（advisory 决策树 B 分支=经验探针）+ 轮㊲ 在墙记录 | ✅ |

## 2. 预注册文档分工核验

`docs/phase-e3-preregistration.md` **不含**操作性契约值（grep `22`/`block_on_unknown`/`provider_cutoff`/`2023-03-10`/`authoritative_refresh` 均 0 命中）——**属设计分工而非漂移**：预注册定义可证伪主张（estimand/h=21/两尾/门），操作性 live-readiness 参数由 AUD-06 走 YAML+ADR-06 通道（业主 D2 批准），两者互不越权。e3-forward.yml cron 保持 disabled（YAML 头注与文件状态一致）。

## 3. 触发器-契约运行时一致性（今日实测）

`scripts/e3_forward_trigger.py` 于 2026-08-30 运行（PHASE_E3_NO_LEDGER=1）：加载 YAML 契约成功、判定 2026-08-30 ≠ NYSE 月末交易日（2026-08-31）→ 确定性 NO-OP（exit 0）——运行时契约装载路径与 YAML 值一致（详见 state handoff zz16）。

## 4. 遗留

无漂移项。厂商日后若发布 GLM cutoff 声明，覆盖 YAML:62 的 probe 值并升级 provenance 为 vendor（P0-3，被动等待）。
