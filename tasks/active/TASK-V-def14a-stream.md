# TASK-V: DEF 14A 代理委托书申报流（高管/董事会治理维度，filing-stream v1）

> 优先级：P3（差距地图最后一项）。worktree：`F:\ZCodeData\Aionis-wv`（分支 feat/def14a）。
> 派发：2026-08-23 主线（业主指令"多 agents 同步推进"）。基于 main f759c3f+。

## 铁律 #0（业主明令）
**绝不请求/爬取 data.xiaoyinsi.com 或任何竞品站**。数据一律一手公共源（SEC EDGAR）。

## 背景
差距地图（reports/design/2026-08-23-replication-gap-map.md）P3 最后一项：小隐寺有"高管人级档案 + 董事会分析"维度，其一手源 = DEF 14A 代理委托书（股东大会文件，含董事/高管/薪酬/持股）。Aionis 已有 /executives 页（8-K Item 5.02 流，20+ 条）。本任务给 /executives 增加 **DEF 14A 申报流**（v1 = filing-stream 级，人级解析诚实 DEFERRED）。

## 任务
1. **ingest**：`src/aionis/ingest/form_def14a.py` —— 照 `form_d.py` 模式（EFTS 表单级查询，无 CIK）。表单 `DEF 14A`（含空格 → URL 里 `%20`，照 form_ipo 的 `root_form.replace(' ', '%20')`）。窗口 trailing ~120 天（照 ipo 固定锚 2026-04-25+，只增不减）。**体量先探测一次**：`forms=DEF%2014A` 的 count——若单窗逼近 10,000 则复用 `form13f_dir.py` 的自适应切分模式。注意 DEF 14A 有修正件 DEF 14A/A（root-form 扩展应自动覆盖，探测验证）。`_get_json`/`_cache_dir` 从 `aionis.ingest.form4_efts` 导入；`_parse_company`/`parse_ticker`/`_filing_index_url`/`_issuer_cik` 从 `aionis.ingest.form_ipo` 导入（照抄 form_d.py 的导入行）。**页间 sleep 2.1s 显式**。
2. **fetcher**：`scripts/def14a_fetch.py` —— 照 `form_d_fetch.py`（种子合并 + accession 去重 → `data/cache/form_def14a_aggregate.parquet`）。
3. **导出**：`export_form_def14a()` 加进 `scripts/export_terminal_data.py`（照 `export_form_d` 结构）：status/as_of/window/issuers/total/by_form/filings（可见 600 最新，cap 披露）/methodology。**v1 诚实边界（方法学必须写明）**：董事/高管姓名、薪酬、持股在委托书正文内，v1 不解析（每份文件数千行 HTML，逐份解析的请求/解析成本 deferred）；每行链 EDGAR 文件页。**SKIP/retain 守卫**（cache 缺失 → 打印 SKIP 返回，不动已提交 JSON）。注册三处：`_DATA_HEALTH_MANIFEST`（`("form_def14a", "def14a.json", _DH_DAILY)` 放 form_d 后）、`_dh_as_of` 分支、`_API_LICENSE`（"U.S. SEC EDGAR — public domain"）、main() 调用列表（form_d 后）。
4. **前端**：`web/src/components/executives/executives-view.tsx` 新增 Def14aSection（**先读该文件**照其现有组件风格）：表（发行人/ticker 链接-STOCK_PAGE_TICKERS 守卫照 ipo-view 模式/表单徽章/申报日 fmtDateShort/EDGAR 外链）+ LoadMoreFooter（stream-kit）+ 头部 mono 计数。i18n zh/en 各 ~8 键（executives.def14a.*）。
5. **barrel**：`def14a.json` + 类型（照 FormD 类型模式）进 `web/src/data/aionis/index.ts`（**普通 barrel 即可，600 行可见 <100KB**，不需要专用模块）。
6. **测试**：`tests/test_web_terminal_data.py` 加 `test_form_def14a_panel_contract`（照 form_d 契约：status-form 一致 DEF 14A→new / DEF 14A/A→amendment——**按实际探测的 form 字段值定枚举**、newest-first、by_form 求和、EDGAR 链接前缀、methodology 含 "not extracted"/"not parsed" 与 display-only）。
7. **7-gate**：`docs/data-intake-edgar-ipo.md` 同级新建或增补 `docs/data-intake-edgar-def14a.md`（照现有 intake 文档结构，含请求账）。

## 验证（worktree 内，禁 next build）
`uv run pytest tests/test_web_terminal_data.py -q`（PYTHONPATH 见下）+ `uv run ruff check`（改动的 .py）+ web 侧 `npx tsc --noEmit`（在 web/ 下，需要 node_modules junction）+ eslint 改动文件。全绿后 commit（原子，Conventional Commits）到分支。

## 通用铁律
- worktree = 兄弟目录；主仓只读；**禁 rm -rf；禁 junction 删除前不摘；禁 next build（耗资源且集成时统一跑）**。
- 运行 python 用主仓 venv：`cd F:\ZCodeData\Aionis-wv && F:\ZCodeData\Aionis\.venv\Scripts\python.exe -m pytest ...`（或 PYTHONPATH=F:\ZCodeData\Aionis-wv\src）。
- 礼貌 ≥2s；失败诚实计数不猜测；0 ledger/0 frozen/0 prereg 改动；绝不碰 runs/ledger.jsonl。
- 若死于配额 [1308]：直接结束并写一行报告，不要重试。
- 交付报告：commit hash / 探测体量（count、修正件占比）/ 请求账（页数×请求）/ 测试结果 / v1 边界确认。
