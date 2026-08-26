# TASK-DISP-H3 — IPO 发行价有界解析（424B4 bounded-parse lane）

**Lane**: display / data-export（照 stakes_pct 有界解析先例）。**优先级**: P1（roadmap H3 深度残余第一项）。
**工作目录**: worktree `F:\ZCodeData\Aionis-wb`（分支 `feat/ipo-offer-price`，已建 junction）。
**授权**: 业主 2026-08-26"多 agent 分工开发"指令。

## 0. 目标

`/ipo` 面板现在是 1,046 份申报 / 484 发行人，但**发行价未解析**（v1 边界，诚实降级披露中）。
本任务给最新一批 priced（424B4）申报补上封面发行价，把"价格未解析"的残余项变成
"有界解析 + 覆盖率如实披露"——**绝不追求全量，绝不编造缺价**。

## 1. 先读懂现状（动工前必做，结论进报告）

- `src/aionis/ingest/form_ipo.py`（或实际同名模块）：EFTS form 级查询、status 推导逻辑、
  现有缓存模式（幂等、≥2s 礼貌）。
- `scripts/form_ipo_fetch.py`（或实际 runner）。
- `src/aionis/reporting/export_terminal_data.py::export_form_ipo`（或 grep 定位）：
  现有字段、retain/守卫模式（`_safe_export`/`_committed_json` 五导出器守卫先例）。
- `web/src/data/aionis/form_ipo.ts`（独立模块）与 `/ipo` 页 view 组件、现有契约测试
  （grep `form_ipo` in `tests/`）、`docs/data-intake-form-ipo*.md`。
- 有界解析的方法论先例：`src/aionis/ingest/stakes_pct.py`（分级置信度 + 诚实计数 + 测试钉死）。

## 2. 交付物

1. **有界解析器**（ingest 层新函数或新模块）：
   - 目标集 = form_ipo 现有数据中 status=priced 的 424B4 行，**按申报日取最新 ≤80 份**
     （预算封顶：index 页 + 主文档 ≈ ≤170 请求，全部 ≥2.1s 间隔 + 指数退避；
     实际请求数逐条记账写进 7-gate 文档）。
   - 每份拉 EDGAR filing index → 定位 424B4 主文档 → 封面价正则解析
     （"Initial public offering price" 类段落；分级：精确解析 / 低置信留空 / no-match，
     计数披露，低置信不猜）。
   - 幂等缓存（accession 键；复跑 0 新请求必须成立并在报告中给出证据）。
2. **导出升级**：`export_form_ipo` 增字段——per-row `offer_price`（可 null）+ 汇总
   `offer_price_parsed` / 覆盖率 / 预算与窗口披露（methodology 段照现有风格）。
   保持既有字段逐字不变（契约兼容）。重导出生成 committed JSON。
3. **前端**：ipo-view 价格列（空值 "—"）+ KPI/方法学披露行 + i18n zh/en 对称键
   （建议 `ipo.price.*`）。
4. **契约测试**：照现有文件风格新增断言——price>0 或 null；覆盖率数学自洽
   （parsed 计数 ≤ priced 计数 ≤ total）；newest-first 不破坏；methodology 含
   bounded/not-extracted 披露与请求预算；幂等字段（如 parsed_at/as_of）形状。
5. **7-gate 文档** v0.x：新增请求账 + 解析方法分级 + 诚实边界段。

## 3. 铁律

- 真实数据优先：跑一次真抓取（预算内）；网络失败→诚实计数降级并照常交付（解析器 + 测试），
  不得为凑覆盖率放宽正则去"多解析"。
- 纯 display-lane 数据：0 ledger/frozen/config/prereg/OOS 接触。
- 礼貌是硬约束（≥2s + backoff）；总请求预算 ≤170，超了就截断到预算内并在披露中写明。
- 不碰 `docs/code-review/`；不 push；不动主仓工作树。

## 4. Worktree 环境注意（前人踩坑，直接照做）

- Python 测试：`PYTHONPATH=F:/ZCodeData/Aionis-wb/src` + 主仓 venv
  （editable 安装指向主仓，不设即测旧码）：
  ```bash
  cd F:\ZCodeData\Aionis-wb
  PYTHONPATH="$PWD/src" uv run --project F:/ZCodeData/Aionis pytest -q tests/test_form_ipo*.py tests/test_web_terminal_data.py
  ```
- 若撞 `runs/ledger.jsonl` sha256 pin 假红（CRLF 重签出）：
  `git checkout -- runs/ledger.jsonl` 后从主仓复制原文件覆盖即可，**绝不"修复"其内容**。
- 前端验证：
  ```bash
  cd F:\ZCodeData\Aionis-wb\web && npx tsc --noEmit && npx eslint src --max-warnings 33
  ```
  build 归主线集成（worktree 内 next build 必败——Turbopack symlink 限制，别试）。

## 5. 报告格式

(a) 现状核查结论（模块/runner/export/测试/文档真实路径）；(b) 解析分级设计一句话 +
实测解析成功/低置信/no-match 计数；(c) 请求账（实际总数/预算）；(d) 幂等复跑证据；(e)
文件清单；(f) 验证命令 + exit codes；(g) 冲突面声明（预期：export_terminal_data.py、
dict.ts、tests、data_health/api_catalog 由主线统一重生成）。
