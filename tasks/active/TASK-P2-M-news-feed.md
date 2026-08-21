# TASK-P2-M — /news 新闻流模块（移交新 session 接手）

- 编号: P2-M
- 标题: 美股/市场新闻流页面（`/news` 路由），对标小隐寺 /news。
- 状态: **READY — 前一子代理被取消，worktree 有半成品未提交改动，待新 session 审查后续作**
- 优先级背景: 见 `reports/design/2026-08-21-xiaoyinsi-full-parity-roadmap.md` P2 行。
- 边界: display + 数据导出 lane。**0 ledger / 0 frozen / 0 prereg / 0 OOS**。真实管线禁 mock。

## 现场状态（2026-08-22 02:45 交接）

- worktree：`F:\ZCodeData\Aionis-m`（分支 `agent-m`，基 b1f991a；**main 已前进到 d15bd9b**，续作前先 `git rebase main` 或以 main 重建 worktree——推荐后者：新建分支基于最新 main，再把半成品文件拷过去审用）。
- node_modules junction 已建（`web/node_modules` → 主仓）；`runs/ledger.jsonl` 已用主仓原文件覆盖（CRLF 修复）。
- **半成品未提交改动**（先逐一审查再决定去留——历轮教训：验收他人遗留必须查重复定义/半成品）：
  - `scripts/news_feed_fetch.py`（??，新文件）
  - `docs/data-intake-gdelt-news-feed.md`（??，新文件）
  - `scripts/export_terminal_data.py`（M，部分接线）
  - `.github/workflows/refresh-terminal-data.yml`（M，可能加了 fetch 步）
  - `runs/ledger.jsonl`（M = 行尾幻影差异，内容 0 diff，勿提交勿 checkout）

## 任务规格（自包含）

**目标**：`/news` 新闻流（v1）。两路按数据可得性选一，报告说明取舍：
- **路 A（推荐若可行）**：GDELT DOC 2.0 API（`https://api.gdeltproject.org/api/v2/doc/doc?query=...&mode=artlist&format=json`，公开无 key，已在项目允许源内）拉近期市场要闻（英文 query 如 `(stock market OR "S&P 500" OR federal reserve)`，timespan 近 7-30 天，artlist）→ 每条 title/source/seendate/url；聚合为新闻流面板。礼貌 ≥2s，条目 ≤200。
- **路 B（降级）**：只用既有 `themes.json` 的 GDELT 月度情绪聚合做"新闻情绪"页（诚实披露"聚合情绪非文章流"）。
- 无论哪路：禁编造文章；字段缺失诚实空。

**实施清单**：
1. ingest `src/aionis/ingest/news_feed.py`（走路 A 时；纯解析函数 + 幂等缓存）。
2. fetch `scripts/news_feed_fetch.py` → `data/cache/news_feed.parquet`（或 json），去重键=url。
3. 7-gate：`docs/data-intake-gdelt-news-feed.md`（学 `docs/data-intake-edgar-form8k.md` 格式；GDELT 开放数据许可评估）。
4. 导出 `export_news_feed()` → `web/src/data/aionis/news_feed.json`（as_of=最新条目时间/by_day 计数/条目 capped 150/methodology）+ `_API_LICENSE` GDELT 条目（学 themes 写法）+ data-health manifest（源节奏判断 _DH_CADENCE/_DH_DAILY）+ `_dh_as_of` 分支 + main() 调用。**注意 main() 里调用顺序：export_data_health/api_catalog 必须仍排最后**。
5. CI：`refresh-terminal-data.yml` 加 fetch 步（学 form8k_fetch 步：timeout-minutes 10 + continue-on-error）。
6. web：`/news` 路由 + `web/src/components/news/news-view.tsx`（日期降序条目表：时间/标题外链原文/来源；by_day 汇总卡；methodology 卡；空态卡学 events-view）+ 侧栏（reference 组 api-docs 附近或 context 组，按信息架构判断并报告理由）+ i18n `news.*` zh/en（dict.ts 只加不删）+ `index.ts` 类型 barrel（学 Form8k）。
7. 测试：hermetic（artlist JSON fixture 显式 hand-written 标注）+ `tests/test_web_terminal_data.py` 契约（形状/日期降序/条目计数一致）。改共享函数后跑该文件全量。
8. 真实数据拉取并 committed JSON。

## 验证命令（实测可用）
- pytest：`cd <worktree> && PYTHONPATH=<worktree>/src F:/ZCodeData/Aionis/.venv/Scripts/python.exe -m pytest tests/<目标> -q`
- ruff：`F:/ZCodeData/Aionis/.venv/Scripts/python.exe -m ruff check src scripts tests`
- tsc：`cd <worktree>/web && node node_modules/typescript/bin/tsc --noEmit`
- eslint：`cd <worktree>/web && node node_modules/eslint/bin/eslint.js src --quiet`

## 完成定义与集成协议
全部验证绿 + 增量 Conventional Commits 在自己分支 → 主线 cherry-pick（生成物 JSON 冲突取 ours 后统一重生成 data_health/api_catalog）→ 全套验证（pytest exit 0 + ruff + tsc + eslint + `npx next build` 含 /news）→ state 沉淀 → push。清 worktree 铁律：**先 `cmd //c "rmdir <wt>\web\node_modules"` 摘 junction 再删目录**。完成后把本文件移至 `tasks/completed/`。
