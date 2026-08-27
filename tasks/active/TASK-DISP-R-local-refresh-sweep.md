# TASK-DISP-R — 本地数据刷新扫荡（镜像 refresh 工作流的 display-lane 数据部分）

> **状态 (2026-08-27 深夜轮)**：轮 1 已执行、部分完成、可幂等续跑。Phase 1 **4/10 成功**
> （ark +2026-08-27 / reddit 08-27 / ape_wisdom 08-27 / news_feed 08-27 双语 / korea 周度在位），
> 其余步骤与 Phase 2-5 被本机病理挡住：**`import pandas` 间歇性被系统层阻塞**（挂点
> pandas._libs 的 .pyd 加载，user-CPU≈0 纯等待，高度疑似杀软实时扫描；好窗口仅数分钟，
> 坏窗口 30min-2h；GNU timeout 的 KILL 在坏窗口内也会失灵）。网络本身全通（curl 预检逐源验证）。
> **轮 1 产出已保全**：wj 全部增量缓存已按"worktree 缓存必须拷回主仓"铁律 robocopy /XO 回主仓
> （6,428 文件 / 4.2GB，含 13D daily_idx 暖启动文件、cik_names、cot_aggregate 部分聚合）。
> 零 tracked 变更故零 commit（不制造空提交）；runs/ledger.jsonl 保持原样；未 push。
> **续跑协议**：(1) 先探针 `timeout 45 uv run python -c "import pandas; print('OK')"`——过=窗口开；
> (2) 开则跑扫荡脚本（主仓版 `data/refresh_sweep_main.sh`，gitignored，含 Phase1 余量→5 +
> 契约测试全量守卫；wj 版 `refresh_sweep.sh` 与 `window_retry.sh` 亦留存未提交）；
> (3) 幂等暖启动：ark/reddit/ape/news_feed/korea 秒过，13D 走 daily_idx 增量，form4 需 20-35min；
> (4) 完成后重出 §3 报告并分阶段 commit。工具脚本（refresh_sweep*.sh / window_retry.sh /
> refresh_log.txt）一律不提交。

**Lane**: display / data-refresh。**优先级**: P1（全项目当前最高价值未阻塞项——24 个日更面板
as_of 停在 08-18~21，Actions 冻结所致；本地跑同样的抓取即可恢复新鲜度，不涉部署）。
**工作目录**: worktree `F:\ZCodeData\Aionis-wj`（分支 `feat/local-refresh-sweep`）。
**环境已就绪**: 主仓已整体复制 `data/`（2.6G 含全部增量缓存/checkpoint）与 `.env`（密钥；
**绝不提交 .env**）。worktree 缺研究面 runs/ 产物——导出时冻结面板会走 retain 守卫保留旧值，
这是设计内行为（与 CI 完全一致），**不要**试图补研究面缓存。

## 0. 权威步骤来源

镜像 `.github/workflows/refresh-terminal-data.yml` 的数据部分（先读它）。工作流之外、后续
新增的 display 抓取器也要跑（见下表）。

## 1. 抓取序列（按此顺序；每步失败如实计数继续下步，除非连续 2 步同源失败则跳过同源余步）

**Phase 1（轻，无厚缓存依赖）**：
```bash
uv run python scripts/ark_holdings_fetch.py          # ARK 日快照（+1 个新日期，±pp 积累）
uv run python scripts/reddit_fetch.py                # Reddit Atom 自采
uv run python scripts/ape_wisdom_fetch.py            # ApeWisdom 榜
uv run python scripts/cot_fetch.py                   # CFTC COT（周更，可能无新）
uv run python scripts/market_prices_fetch.py         # VIXCLS
uv run python scripts/fetch_macro_display.py --force # ALFRED 宏观
uv run python scripts/news_sentiment_gdelt_fetch.py  # GDELT 增量
uv run python scripts/news_feed_fetch.py             # /news 双语道（eng 撞过 429，退避自愈）
uv run python scripts/korea_proxy_fetch.py           # FRED DEXKOUS 周
uv run python scripts/bts_tsi_fetch.py               # BTS 货运月（可能无新）
```
**Phase 2（EDGAR/EFTS 族，全部 ≥2s 礼貌）**：
```bash
uv run python scripts/stakes_13d_daily_fetch.py      # 13D 日索引
uv run python scripts/stakes13g_fetch.py             # 13G 流
uv run python scripts/form8k_fetch.py                # 8-K 50 发行人
uv run python scripts/form_def14a_fetch.py 2>/dev/null || uv run python scripts/def14a_fetch.py
uv run python scripts/form_d_fetch.py                # Form D 滚动 30 天
uv run python scripts/filing_stream_fetch.py         # 统一申报流 v2
uv run python scripts/form_ipo_fetch.py              # IPO 窗口滚新
uv run python scripts/politician_trades_fetch.py     # House PTR 流
uv run python scripts/form4_fetch.py                 # Form 4 30 发行人增量（最重，可能 15-30min）
```
（确切文件名以 `ls scripts/*fetch*.py` 实际为准；上表与实际名不符时以实际为准并报告差异。）
**Phase 3（衍生/重计算，全本地零抓取）**：
```bash
uv run python scripts/stakes_pct_parse.py            # 离线 pct 解析（若其输入更新了）
uv run python scripts/build_regime_macro.py          # 宏观主题合成
uv run python scripts/build_ticker_metadata.py --no-cache   # 需要 --with baostock：
#   uv run --with baostock python scripts/build_ticker_metadata.py --no-cache
```
**Phase 4（价格与物化，预算受控）**：
```bash
uv run python scripts/phase_b_fetch.py --display --budget-minutes 24
uv run python scripts/track_b_materialize_panel.py --display
```
**Phase 5（全量导出 + 闸门）**：
```bash
uv run python scripts/export_terminal_data.py        # 全量 main()——冻结面板 retain 是设计
uv run pytest -q tests/test_web_terminal_data.py --deselect tests/test_web_terminal_data.py::test_ledger_append_only_not_mutated_by_export
```

## 2. 提交与边界

- **只提交** gitignored 之外的变更（web/src/data/aionis/*.json、docs/data-intake 若有更新、
  scripts 无改动则零）。分阶段小步 commit（Phase 1 一笔、Phase 2 一笔、Phase 4/5 一笔）。
- **不 push**；不部署；不碰 runs/ledger.jsonl（CRLF 假红从主仓拷原件——已预拷）；
  不碰 docs/code-review/；junction 永不 rm -rf；0 ledger/frozen/config/prereg/OOS。
- 网络礼貌是硬约束：脚本内置 ≥2s；你不并行跑两个抓取命令；单步超时/失败 → 退避重试一次 →
  诚实跳过记账。
- `.env` 里的密钥绝不外传、绝不写进任何提交/报告（报告只写"某源用 key=有/无"）。

## 3. 报告格式

(a) 逐抓取器结果表（命令/结果/新增 as_of/请求数级估计/失败原因）；(b) data_health before→after
的 daily 面板 as_of 对照表（跑前后各 dump 一次对比）；(c) Phase 4 价格收敛进度（cached/fetched）；
(d) 契约测试结果；(e) commit 清单；(f) 冲突面（预期大量 committed JSON 变更——主线以你的 worktree
版本为准统一取用）。
