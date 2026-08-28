# Commit 0aeac7d0099ee2d7de2aebc3a4cfb1180bc582eb 审查报告

**提交信息**: feat(web): track record (prediction vs reality) + A-share board tiers（2026-08-07，Rethymus）
**改动范围**: 11 个文件，+858/-41；export_picks_backtest（近 6 个月 top-5 选股 vs 实测前瞻收益，hit_rate/超额）、A股板块层级代理（`_board_classification` 代码前缀分类替代 Unclassified）、picks-view TrackRecord 区块、2 个新契约测试、picks_backtest.json。

## 四维度结论
| 维度 | 结论 | 一句话说明 |
|---|---|---|
| 稳定性 | ⚠️ | backtest 导出无守卫直读两个 panel parquet（第三次重复读取），缺缓存即全脚本中断 |
| 可扩展性 | ✅ | 板块分类纯函数、N_MONTHS/TOP_N 集中常量；methodology 字符串同步披露层级代理性质 |
| 生产可用 | ✅ | "预测 vs 现实"诚实审计（hit_rate 40%、超额 −0.003 如实展示跑输）——null 结论可视化到位 |
| 高内聚低耦合 | ✅ | 仍守 display-only 边界，只读 runs/ 与 data/cache 工件 |

## 对照参考
A股代码段规则（上交所 600/601/603/605 主板、688 科创板、900 B 股；深交所 000/001/002/003 主板、300/301 创业板；北交所旧 8xx/4xx、2025 起 920 段——国都证券/雪球公开资料、各交易所规则页）对照 `_board_classification`：688/300/301/6xx/000/002/003 判定正确；**9 前缀被判为北交所是错的**（900=沪 B 股），**001 落入"其他"也是错的**（001=深主板）。track-record 的 top-N vs 全市场均值对照法与量化回测通用实践（等权基准=当月横截面均值）一致。

## 问题清单
### P3-1 板块前缀分类两处误判（900 B 股→北交所；001 深主板→其他）
- 描述：`if head in {"8", "4", "9"}: return "北交所 (BSE)"`——9 前缀中 900xxx 是上交所 B 股（且 2025 起北交所新码段 920 才是 9 开头），一律归北交所错误；`001xxx`（深主板新段）不匹配任何分支落入"其他 (Other)"——实际 sector_breakdown.json 已出现该桶。
- 位置：`scripts/build_ticker_metadata.py:102-104`
- 影响范围：/sectors 页 A 股分组准确性（展示层；CSI300 宇宙内命中概率低）。
- 修复建议：688→STAR、600/601/603/605→沪主板、900→B 股单独桶或排除、000/001/002/003→深主板、300/301→创业板、920/8x/43x→北交所。
- 修复成本：低
- 状态：未修复（main 同版）

### P3-2 export_picks_backtest 无守卫读取 panel，第三次重复读同一 parquet
- 描述：`pd.read_parquet(Path("data/cache/track_b_panel.parquet"))`（及 cn）无存在性检查——fresh checkout 上 main() 在此处崩溃，且这是同一次导出中第三次读取同一对 panel（export_picks、export_sector_breakdown、export_picks_backtest 各一次）。
- 位置：`scripts/export_terminal_data.py:271-274`
- 影响范围：导出脚本在缓存缺失环境的可用性与重复 I/O。
- 修复建议：calibration/panel 读取上提到 main() 一次并传参；缺文件时 awaiting_fetch 降级。
- 修复成本：低
- 状态：已在 a08ec16 部分修复（`_safe_export` 包装仅吞 FileNotFoundError；重复读取未消除）

### P3-3 注释与行为不符（"exclude the very latest if partial"）
- 描述：`# Last N_MONTHS realized months (exclude the very latest if partial).`——实际排除机制是前置 dropna(forward_return_h)（未实现月份自然消失），并非显式排除最新月；注释误导维护者以为有额外排除逻辑。
- 位置：`scripts/export_terminal_data.py:287`
- 影响范围：可维护性。
- 修复建议：改注释为"未实现月份经 dropna 自然排除"。
- 修复成本：低
- 状态：待人工复核（后续版本注释演变需比对）

## 总体评分
8/10 — "预测 vs 现实"审计是本项目诚实纪律的最佳展示（如实挂出 40% 命中与负超额）；扣分在板块前缀两处误判与导出脚本的重复无守卫读取延续。
