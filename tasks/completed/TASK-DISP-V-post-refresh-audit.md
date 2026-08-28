# TASK-DISP-V — 轮 23 刷新后全站静态一致性审计（只查证，零修复）

**Lane**: 验证 / 审计（VERIFY）。**工作目录**: 主仓 `F:\ZCodeData\Aionis`。
**基线**: 轮 23 数据补跑 + `web/out/` 重建后的构建产物（页数以实测为准，轮 22 为 1,502）。
**前置**: 主线已完成 fetch→materialize→export→契约测试→`pnpm build`，你看到的 `web/out/`
即为被审计对象。

## 0. 目标与边界

对构建产物做全站静态一致性扫查，产出审计报告。**你零代码修复**——发现项如实列报，
处置留给下一轮。只允许新建两个文件：
`reports/audit/2026-08-29-post-refresh-audit-r23.md`（主报告）+
`reports/audit/2026-08-29-post-refresh-audit-r23-findings.json`（机器可读发现项）。

**陷阱警示（轮 22 P2-2 实证）**：`web/out/Aionis` 可能是指向 `web/out` 自身的 NTFS
junction——目录遍历**绝不**用裸 `rglob("**/*")` 扫 out/，先判 junction 跳过，否则无限递归。

## 1. 审计项（逐项给证据：方法 + 样本量 + 结果数字）

1. **回归复验（轮 22 修复项，应保持修复态）**：
   a. 全站 `/stock/` 内链逐一对照 `out/stock/` 实际页——上轮修复后应为 0 死链；本轮新数据
      （08-28 刷新带入的新 13G/filing ticker）是否再次带入宇宙外死链 = 本审计最高价值项。
   b. 哨兵 ticker（`NONE.` / `N-A` / `NULL` / `NIL` / `UNKNOWN` / `NAN` 等解析失败值）不得
      以链接或可点文本形式出现在任何页面；导出端应已清洗为 null 并计入 source_health。
   c. dashboard Reddit 统计条 "已载前 N" 就近披露在位（ee6ea16）。
2. **渲染垃圾全站扫**：全部 HTML 剥 script/style 后扫 `undefined`、`NaN`、`[object Object]`、
   `0月NaN日`、`Infinity`（逐条人工定性，附路径+片段）。
3. **内链完整性**：全部 `href="/Aionis/..."` 内链 → 逐一验证目标 .html 在 out/ 存在
   （/stock/[t]、/manager/[cik] 深链全覆盖）。死链全列。
4. **i18n 对称性**：dict.ts zh/en 键集差集（应空；轮 22 为 1,095=1,095）。
5. **统计条调和**：dashboard StatBand 五数（上市公司/机构申报人/明星投资人/政客交易/Reddit
   标的）逐一复算对回面板 JSON；明星投资人应=**43**。
6. **新鲜度披露**：八 hub 页 as_of 披露 vs 面板 JSON 一致（本轮刷新后水位应为 08-28 或
   源节奏诚实值）；form4 类 snapshot_ts 与申报日滞后属正常，按轮 22 口径判定。
7. **/manager 页完整性**：`out/manager/` 页数 = `form13f-stars.json n_managers`（应 43），
   抽查含 Southpoint（新准入页）非壳。
8. **诚实性抽查**：空态/降级/披露文案抽查 5 页（data-health、api-docs、ipo、congress、market）。

## 2. 方法建议

python 脚本批量扫 HTML（uv run python -c 或临时脚本）；正则抽 href；禁止修改任何被审计
文件。样本引用格式：`路径:行号: 片段`。

## 3. 报告格式

主报告：执行摘要（PASS/发现数）→ 逐审计项表格 → 每个发现一条（严重度 P0-P3/证据/建议）。
JSON：`[{id, severity, area, evidence_path, snippet, suggestion}]`。
最后 commit 一个原子 `docs(audit)` 提交到 main（只含上述两文件）。

## 4. 铁律

只读审计 + 两份新文件；零生产代码/数据/配置改动；0 ledger/frozen/config/prereg/OOS；
不 push；不碰 `docs/code-review/`（并发 session 领地）。
