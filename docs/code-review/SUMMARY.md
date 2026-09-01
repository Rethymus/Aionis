# Aionis 全历史代码审查汇总（SUMMARY）

- 进度：**303 / 439**（已审 293，跳过 10，待审 136）
- 有效问题（不含已在后续 commit 修复）：**P0=0，P1=15，P2=109，P3=328**；另已在后续 commit 修复 72 条
- 平均评分：8.32/10（293 个已评分 commit）

## 按模块分布

| 模块 | 已审 | 跳过 | P0 | P1 | P2 | P3 | 均分 |
|---|---|---|---|---|---|---|---|
| features | 17 | 0 | 0 | 4 | 9 | 35 | 6.9 |
| data | 6 | 5 | 0 | 4 | 2 | 8 | 6.8 |
| eval | 36 | 2 | 0 | 1 | 17 | 48 | 7.8 |
| docs | 102 | 0 | 0 | 0 | 20 | 52 | 9.4 |
| other | 6 | 0 | 0 | 2 | 4 | 5 | 8.0 |
| ingest | 24 | 0 | 0 | 1 | 10 | 38 | 7.9 |
| scripts | 20 | 0 | 0 | 1 | 8 | 25 | 8.1 |
| site | 12 | 2 | 0 | 1 | 6 | 16 | 7.6 |
| tests | 7 | 0 | 0 | 1 | 6 | 7 | 7.9 |
| web | 33 | 1 | 0 | 0 | 10 | 37 | 8.0 |
| dashboard | 11 | 0 | 0 | 0 | 4 | 20 | 8.0 |
| reporting | 4 | 0 | 0 | 0 | 4 | 10 | 7.8 |
| ci | 6 | 0 | 0 | 0 | 3 | 10 | 7.5 |
| workers | 5 | 0 | 0 | 0 | 3 | 6 | 7.8 |
| extraction | 4 | 0 | 0 | 0 | 3 | 11 | 7.5 |

## 严重问题清单（P0/P1，未修复，详见各 commit 报告）

- **P1** `bdf3fd9b` harvey_liu_haircut 极端 p 值下灾难性消零 → +Infinity 且 survives=true（与自述结论相反）（src/aionis/eval/multiple_testing.py:484）
- **P1** `387ac021` 冻结 config 的 VIX 锚钉错文件：实际输入未入 sha256（scripts/phase_c_run.py:80）
- **P1** `d86ecd7d` fetch_realized_forward_returns 未 normalize 时间戳，live 路径揭示必然失败（src/aionis/eval/forward_score.py:47-53）
- **P1** `7e666d87` runner 默认把 provider_cutoff 伪造成 predict_ts —— 恰是 AUD-06 要拦的缺陷（src/aionis/eval/forward_commit_runner.py:279）
- **P1** `38457c62` Dimension 1（alphalens IC 时序图 + 分位收益图）产出为两张字节级相同的空白 PNG（scripts/build_static_site.py:100-119）
- **P1** `a287b178` 基本面 PIT 过滤为 no-op + filed_date 边界断言为死代码——「anti-leakage asserted」名不符实（src/aionis/features/panel_alignment.py:118-146）
- **P1** `30e2a2bc` 「binds config #41」无机制性绑定：不计算配置哈希、不校验账本、不钉数据指纹（scripts/track_b_a_run.py:10-11, 26-38）
- **P1** `5b561e48` opt-out 边界实现为闭区间，与自身文档/注释的半开区间 PIT 语义矛盾（剔除日当天仍算成员）（src/aionis/ingest/csi300_constituents.py:104）
- **P1** `97184c95` 面板未做 PIT CSI300 成员过滤——横截面=历史 ever-member 池，偏离冻结 universe 规格（scripts/build_cn_price_panel.py:37-56）
- **P1** `33b5cfb5` CN 申万分支必然崩溃：字典推导把 key 字符串当列表索引用（src/aionis/features/regime_meso.py:276）
- **P1** `be115ea8` 防泄漏端到端测试以 pytest.skip 占位交付（违反仓库 Definition of Done）（tests/test_macro_headline.py:168-187）
- **P1** `dd0ba707` 合并逻辑在 CI 上是死代码 —— 面板在目标环境并未解冻（scripts/export_terminal_data.py:912-921）
- **P1** `dd0ba707` active_filers 排名窗口被哨兵行挤空 → 破坏 TS 构建（scripts/export_terminal_data.py:968-970）
- **P1** `ee1b14f1` `_build_news_theme` 被 export_themes 的 panel 门挡住，CI 上不生效（scripts/export_terminal_data.py:541-546）
- **P1** `ee1b14f1` 增量游标永不回刷当月 —— 最新月份冻结在月头几天的部分样本（src/aionis/ingest/news_sentiment_gdelt.py:296-306、353-356）

_由 _sync.py 生成；单 commit 报告见 commits/ 目录。_
