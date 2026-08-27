# TASK-DISP-VERIFY — 终端全站静态一致性审计（只查证，零修复）

**Lane**: 验证 / 审计。**优先级**: P1（⑰-⑲ 三轮 ~25 commits 合入后的首次全站扫查）。
**工作目录**: 主仓 `F:\ZCodeData\Aionis`。**基线**: `web/out/` 当前构建（1,501 页，本轮集成后产物）。

## 0. 目标与边界

对构建产物做全站静态一致性扫查，产出审计报告。**你零代码修复**——发现项如实列报，
处置留给下一轮任务。只允许新建两个文件：
`reports/audit/2026-08-27-terminal-consistency-audit.md`（主报告）+
`reports/audit/2026-08-27-terminal-consistency-findings.json`（机器可读发现项）。

## 1. 审计项（逐项给证据：方法 + 样本量 + 结果数字）

1. **渲染垃圾全站扫**：全部 1,501 个 HTML 里 grep `undefined`、`NaN`、`[object Object]`、
   `0月NaN日`、`Infinity`（排除合法词如 "undefined behaviour" 类文案——逐条人工裁定，报告
   附原文片段与文件路径）。
2. **内链完整性**：抽取全部 HTML 的 `href="/Aionis/..."` 内链 → 逐一验证目标 .html 在 out/
   存在（含 /stock/[t]、/manager/[cik] 深链）。死链全列。外链只查格式不访问。
3. **i18n 对称性**：dict.ts zh/en 键集差集（应空）；若非空列出。
4. **数据调和**：首页 StatBand 五数字（上市公司/机构申报人/明星投资人/政客交易/Reddit 标的）
   逐一对回 data_health.json / 各面板 rows——明星投资人应=42（本轮 +2 后）。
5. **新鲜度披露**：data_health 中 category=daily 的面板 as_of 与各页面展示一致性抽查
   （10 页样本）；theme_signals 06-30 之类陈旧值是否有诚实 as_of 显示（有=PASS，它属 H1 门）。
6. ** basePath 完整性**：产物内资源引用是否全部 `/Aionis/` 前缀（有无漏前缀的绝对路径）。

## 2. 方法建议

python 脚本（uv run python -c 或写临时脚本在 data/cache 下）批量扫 HTML；正则抽取 href；
禁止修改任何被审计文件；临时脚本不提交（或放 reports/audit/ 附带并声明）。
样本引用格式：`路径:行号: 片段`。

## 3. 报告格式

主报告：执行摘要（PASS/发现数）→ 逐审计项表格 → 每个发现一条（严重度/证据/建议归属 lane）。
JSON：`[{id, severity(P0-P3), area, evidence_path, snippet, suggestion}]`。
最后 commit 一个原子 docs(audit) 提交到当前分支（main——只含上述两文件）。

## 4. 铁律

只读审计 + 两份新文件；零生产代码/数据/配置改动；0 ledger/frozen/config/prereg/OOS；
不 push。
