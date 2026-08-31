# TASK-P2-N — /quarterly + /annual 财务申报流双子模块（移交新 session 接手）

- 编号: P2-N
- 标题: 10-Q 与 10-K 近窗申报流两页（`/quarterly`、`/annual`），对标参照站同名页（其自身为空壳，本项目用真实 EDGAR 数据填上）。
- 状态: **READY — 前一子代理被取消，worktree 有半成品未提交改动，待新 session 审查后续作**
- 优先级背景: 见 `reports/design/2026-08-21-参照站-full-parity-roadmap.md` P2 行。
- 边界: display + 数据导出 lane。**0 ledger / 0 frozen / 0 prereg / 0 OOS**。真实管线禁 mock。

## 现场状态（2026-08-22 02:45 交接）

- worktree：`F:\ZCodeData\Aionis-n`（分支 `agent-n`，基 b1f991a；**main 已前进到 d15bd9b**，续作前先 `git rebase main` 或以 main 重建 worktree——推荐后者：新建分支基于最新 main，再把半成品文件拷过去审用）。
- node_modules junction 已建；`runs/ledger.jsonl` 已用主仓原文件覆盖（M = 行尾幻影，勿提交勿 checkout）。
- **半成品未提交改动**（先审查再续作，查重复定义/半成品）：
  - `scripts/export_terminal_data.py`（M，部分接线）
  - `.github/workflows/refresh-terminal-data.yml`（M）
  - `web/src/components/app-sidebar.tsx`（M）
  - `web/src/data/aionis/index.ts`（M）
  - `runs/ledger.jsonl`（M，幻影）

## 任务规格（自包含）

**数据模式**：EFTS form 级全市场查询（无 ciks=）——读 `src/aionis/ingest/form_ipo.py`（main 上已集成，正是这个模式）与 `form8k.py`（客户端+缓存范式）。

1. **ingest** `src/aionis/ingest/form_filing_stream.py`：EFTS 查 `forms=10-Q`（含 /A）与 `forms=10-K`（含 /A），近 ~90 天窗口，分页；每行 company（display_names 解析学 form_ipo）、ticker、filed_date、form、accession、doc_url（filing-index 直链零额外请求）。10-Q 量大，**每类 cap 最近 300 份进面板**，计数诚实记 total vs shown（methodology 披露）。
2. **fetch** `scripts/form_filing_stream_fetch.py` → `data/cache/form_filing_stream.parquet`（form_type 列区分），accession 去重，幂等缓存。
3. **7-gate** `docs/data-intake-edgar-financial-stream.md`（10-Q/10-K 合一，学 form8k 文档格式）。
4. **导出** `export_filing_stream()` → `web/src/data/aionis/filing_stream.json`（as_of/window/{quarterly,annual,counts{total,shown}}/methodology）+ `_API_LICENSE` SEC 条目 + data-health 日更 manifest + `_dh_as_of` 分支 + main() 调用（**data_health/api_catalog 仍排最后**）。
5. **CI** refresh-terminal-data.yml 加 fetch 步（timeout 10 + continue-on-error）。
6. **web**：`/quarterly` + `/annual` 两路由（各自 page.tsx，SegmentHeader segment="context"）+ 共享 `web/src/components/filings/filing-stream-view.tsx`（props 区分 10q/10k；日期降序表：申报日/公司+ticker（链 /stock/[ticker] 仅冻结宇宙内——学 institutions-view 的 STOCK_PAGE_TICKERS 守卫）/form 徽章/原文链；total+shown 汇总卡；methodology 卡）+ 侧栏语境组 /regime 之后两项（FileTextIcon 类）+ i18n `filings.*` zh/en（dict.ts 只加不删）+ index.ts 类型 barrel。
7. **测试**：hermetic（EFTS fixture + display 解析，显式标注）+ 契约（形状/两段都有/日期降序/counts.total ≥ counts.shown）。改共享函数后跑 `tests/test_web_terminal_data.py` 全文件。
8. **真实数据**拉取并 committed JSON。

## 验证命令（实测可用）
- pytest：`cd <worktree> && PYTHONPATH=<worktree>/src F:/ZCodeData/Aionis/.venv/Scripts/python.exe -m pytest tests/<目标> -q`
- ruff：`F:/ZCodeData/Aionis/.venv/Scripts/python.exe -m ruff check src scripts tests`
- tsc：`cd <worktree>/web && node node_modules/typescript/bin/tsc --noEmit`
- eslint：`cd <worktree>/web && node node_modules/eslint/bin/eslint.js src --quiet`

## 完成定义与集成协议
全部验证绿 + 增量 Conventional Commits 在自己分支 → 主线 cherry-pick（生成物 JSON 冲突取 ours 后统一重生成）→ 全套验证（pytest exit 0 + ruff + tsc + eslint + `npx next build` 含两新路由）→ state 沉淀 → push。清 worktree 铁律：**先 `cmd //c "rmdir <wt>\web\node_modules"` 摘 junction 再删目录**。完成后把本文件移至 `tasks/completed/`。
