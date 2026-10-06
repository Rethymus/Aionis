# 深度反思·第四轮（2026-10-07 凌晨，轮 214）— 对最新面的未守护点自审

> 第三轮（轮 205-213）管线全清后 8 轮新增面（PTR 预聚合/CSV 孪生/软败警报/
> barrel 预算/STALE-SOURCE/昨夜变更注册表）——本轮用新外部域扫描 + 对这些
> **新增物本身**做未守护点自审。

## 一、疏漏（本轮新发现，均有证据）

1. **panel_changes.json 的 API 目录缺口**：build-api 镜像全部 JSON →
   /api/v1/panels/panel_changes.json 已可访问，但 api_catalog（"one meta
   layer"承诺）未列它——一个未被目录记载的端点。**修复：catalog site 节
   增列（与 sitemap/atom 同类=站点级资源）。**
2. **retain-skip 导出器缺席变更注册表**：_safe_export 的 FileNotFoundError
   路径不追加 delta → CI-fresh 跑与本地跑的 n_tracked 不一致、被保留面板
   在"昨夜变更"条上不可见。**修复：except 路径追加 changed=false 条目并
   标 skipped（诚实缺席，与其它 skipped 披露同型）。**
3. 软败重试要等整整一天（23:53 恢复道在 ok_committed 时 SKIP）——
   news_feed 类源缓存漂移最坏陈旧 24h+。恢复道"仅重试软败步骤"策略变更
   影响面大（**backlog，owner 可见**）。

## 二、没把握

- panel_changes 的 n_tracked 语义（跑了多少导出器 vs 存在多少面板）——
  缺口 2 修复后两者一致，条上数字变为"注册表面板数"。
- GDELT 源缓存批次的复发频率未知——STALE-SOURCE 今晚首弹，观察 ≥3 晚
  才知道是否常态（persistent_soft_fails 警报自动显性化）。

## 三、失效模式（时间维度）

前三名不变（源轮换/单机通道/Next 升级），新增第四：**panel_changes 注册
表自身的膨胀**——每跑 ~50 条 × 每晚，单文件仍小（~10KB）；恒定重写不累
积，无风险。判定：不需要动作。

## 四、亮眼功能（外部域交叉）

- OpenBB 类 alerts/screeners 不适配静态站（需后端/账号）——维持不做，
  理由入册。
- 可复现性 2026 最佳实践"每跑三标识符"（git commit + 数据 hash + 数据集
  版本）——本仓等价物已具（SUMMARY commit + 逐面板 sha + uv.lock），链路
  分散在三处但都可机器读取；**判定：不再集中化**（为集中而集中无增益）。

## 五、效率

缺口 2 的修复同时修正条上数字的语义（诚实一致）；其余流程面在第三轮
已清。

## 本轮实施

| # | 项 | 来源 | 规模 |
|---|---|---|---|
| 1 | 本报告 | 主交付 | — |
| 2 | catalog site 节增列 panel_changes | 一.1 | S |
| 3 | 注册表 skipped 条目 | 一.2 | S |

边界：display/验证/docs lane；0 ledger / 0 frozen / 0 prereg / 0 OOS。
