# TASK-DISP-Z — 全站静态可访问性/文档结构扫查（只查证，零修复）

**Lane**: 验证 / 审计（VERIFY）。**工作目录**: 主仓 `F:\ZCodeData\Aionis`。
**基线**: `web/out/` 当前构建（1,502 个 .html，轮 24 产物）。

## 0. 目标与边界

全站静态可访问性（a11y）与文档结构首轮系统性扫查。**你零修复**——发现项如实列报。
只允许新建两个文件：
`reports/audit/2026-08-28-a11y-structure-audit.md`（主报告）+
`reports/audit/2026-08-28-a11y-structure-audit-findings.json`（机器可读）。

**陷阱**：目录遍历前先判 `out/Aionis` junction（本轮应不存在，但代码必须先判后扫）。
剥 `<script>/<style>` 后再分析；只看服务端渲染出的 HTML（客户端水合后的 DOM 变化不在
静态审计范围，如实声明这一边界）。

## 1. 审计项（逐项给样本量 + 结果计数 + 证据样例）

1. **图片替代文本**：`<img>` 无 `alt` 属性（区分 alt="" 装饰性=合法）；内联 svg 的
   aria-hidden/role 抽查。
2. **空交互元素**：`<a>`/`<button>` 可见文本+aria-label 双空（图标按钮重点查）。
3. **标题层级**：每页 h1 缺失/多 h1/hN 跳级统计（Top 违规页列举）。
4. **地标结构**：每页 `<main>`/`<nav>`/`<footer>` 存在性；`<html lang>` 属性值。
5. **重复 id**：同页 id 重复（水合冲突高危）。
6. **tabindex**：正 tabindex（扰乱自然 Tab 序）。
7. **表单标签**：`<input>`（非 hidden）无关联 label/aria-label（本站表单少，全量）。
8. **对比度线索（静态可查部分）**：内联/工具类中的低对比组合抽查不做全量（色值计算
   需渲染，声明边界），只查 `text-muted-foreground/40` 以下透明度修饰的**正文性**文本
   使用处（装饰性分隔符除外），人工定性列举即可。

## 2. 方法建议

python 批量扫（uv run python，临时脚本放 data/cache/ 下不提交）；html.parser 或正则；
逐项输出计数与 `路径: 片段` 样例（每类至多 10 条）。

## 3. 报告格式

主报告：执行摘要（PASS/发现数/最严重的 3 条）→ 逐审计项表格 → 发现项
（严重度 P0-P3/计数/样例/建议归属 lane）。JSON：
`[{id, severity, area, count, samples:[...], suggestion}]`。
最后 commit 一个原子 `docs(audit)` 提交到 main（只含两份报告文件；不 push）。

## 4. 铁律

只读审计 + 两份新文件；零生产代码/数据/配置改动；零网络；0 ledger/frozen/config/
prereg/OOS；不碰 `docs/code-review/`、`state/`、`tasks/`。
