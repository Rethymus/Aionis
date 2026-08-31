# TASK-W: 统一申报流 v2 —— 直查 EFTS 多表单族（全市场近期申报流）

> **状态：已完成并集成上 main（2026-08-23，handoff (s)）。**

> 优先级：P2 尾巴（统一流的表单覆盖扩展）。worktree：`F:\ZCodeData\Aionis-ww`（分支 feat/filing-stream-v2）。
> 派发：2026-08-23 主线（业主指令"多 agents 同步推进"）。基于 main f759c3f+。

## 铁律 #0（业主明令）
**绝不请求/爬取 参照站 或任何竞品站**。数据一律一手公共源（SEC EDGAR）。

## 背景
/events 页已有"全市场申报流"（`filing_stream.json`，2026-08-23 上线）= **六面板派生合并**（800/2,259/11 表单）——覆盖受源面板可见上限约束，且缺 10-K/10-Q 等表单。v2 = **直查 EFTS 多表单族**，覆盖参照站统一流的全家桶：8-K / 10-K / 10-Q / S-1 族 / 4 / D / SC 13D / SC 13G。

## 任务
1. **ingest**：`src/aionis/ingest/filing_stream.py` —— 对每个 root form 逐一 EFTS 表单级查询（**一次一个 form 参数，绝不逗号列表**——efts 对 root+amendment 列表解析有 bug，见 stakes_13d_efts 已验证教训）。窗口 trailing ~14 天（RECENT 流）。表单族与预期体量（14 天窗）：
   - `8-K` ~5-6k（安全）
   - `10-K`/`10-Q`：财报季波动大，若 ≥9,500 复用 `form13f_dir.py` 的自适应切分（阈值/地板同款）
   - `S-1` ~400、`D` ~3k、`SC 13D` ~200、`SC 13G` ~600（安全）
   - `4`（内部人）**~10-15k 必超上限** → 直接切两个 7 天半窗（照 form13f_dir.split 逻辑）
   - `DEF 14A` **不要碰**（TASK-V 的 lane）
   每表单独立缓存文件 `efts_fstream_{form}_{start}_{end}.json`（幂等）。页间 sleep 2.1s。
   归一化行：`{form, who, ticker, filed_date, doc_url}`——who = 公司名（display_names 去括号，`form_ipo._parse_company`）；ticker = `parse_ticker`；4 的 who 用 filer 名；13D/13G 的 who = "FILER → TARGET"（target 字段若无则 filer）。doc_url = `_filing_index_url`。**None→""、占位符过滤**（照 export_filing_stream 现有 add() 的卫生规则）。
2. **fetcher**：`scripts/filing_stream_fetch.py` → `data/cache/filing_stream_aggregate.parquet`（accession 去重，newest-first）。
3. **导出**：重写 `export_filing_stream()`（scripts/export_terminal_data.py）——改读新 parquet（**保留 SKIP/retain 守卫**：cache 缺失 → SKIP 保留已提交 JSON，旧派生逻辑整段删除并在 methodology 记 v1→v2 迁移事实）。payload 形状不变（form/who/ticker/filed_date/doc_url + by_form + total_merged→改名 total 或保留字段名 **不破坏现有测试**——先读 `tests/test_web_terminal_data.py::test_filing_stream_panel_contract` 并适配）。可见 cap 800 照旧。methodology：直查事实、每表单请求账、4 的切分披露、13F 排除、DEF 14A 由独立面板载。
4. **前端**：`/events` StreamSection **无需大改**（形状不变）——仅确认 by_form pills 自动扩到新表单；若 LabelKey 有硬编码需微调则微调。i18n note 文案更新（提及 10-K/10-Q）。
5. **测试**：更新 `test_filing_stream_panel_contract`（allowed forms 集合按 v2 实际、newest-first、by_form 求和、卫生断言保留）。

## 冲突边界（重要）
- TASK-V 同时在改 `scripts/export_terminal_data.py`（加 export_form_def14a）、`tests/test_web_terminal_data.py`、`web/src/i18n/dict.ts` —— **你只改自己函数/区块附近**，集成时主线解 merge。绝不 rebase main；只在自己的分支上工作。

## 验证（worktree 内，禁 next build）
pytest（test_web_terminal_data.py）+ ruff + `npx tsc --noEmit`（web/ 下）+ eslint 改动文件。全绿后原子 commit。

## 通用铁律
- worktree = 兄弟目录；主仓只读；禁 rm -rf；禁 junction 未摘先删；禁 next build。
- python 用主仓 venv + PYTHONPATH=F:\ZCodeData\Aionis-ww\src。
- 礼貌 ≥2s；0 ledger/frozen/prereg 改动；死于配额 [1308] 直接结束写报告。
- 交付报告：commit hash / 每表单请求账与体量 / 4 切分实录 / 测试结果 / v2 覆盖对比 v1。
