# TASK-DISP-K — 审计发现项修复批（T3 + T4/T5/T6/T7）

**Lane**: display（纯前端视图）。**优先级**: T3=P2、其余 P3（来源：全站审计
`reports/audit/2026-08-27-terminal-consistency-audit.md`，发现项 JSON 同目录）。
**工作目录**: worktree `F:\ZCodeData\Aionis-wi`（分支 `feat/audit-remediation`，junction 已挂，LF ledger 已预拷）。
**已由主线修复（勿重复）**：AUD-T1（stock 页 /manager 死 chip→/institutions）、AUD-T2（stakes
窗口对象插值→start→end；顺带覆盖 T5 的窗口披露部分）。audit JSON 里这两条已部分/全部处置，
你做剩余项。

## 1. 工作项（逐条对应审计编号）

### T3（P2）53 个死亡股票深链 ×115 实例
- 机制：面板行的 ticker ∉ stock 导出宇宙（/stock/[t] 只为 stock_universe 收录的 1,421 只 SSG），
  confirmation(48)/smart-money(48)/congress(16)/events(1)/executives(1)/reddit(1) 的跨链未过门。
  典型：BRK-B、BRK.B 双拼写、SNDK 更名。
- 修法（照既有守卫先例）：视图层链接处统一用 stockUniverse 成员集判定（代码库已有该内存判定
  模式——grep STOCK_PAGE_TICKERS / stock-universe 导入用法），未收录 ticker 降级为纯文本
  （保留 ticker 字样，只是不发链）。逐视图修复，统计各视图修复前后链数写入报告。
- 注意：stock_universe.ts 是独立模块——确认在这些视图引入它不会把 553KB 拖进页面 bundle
  （先看现有消费方怎么引的；若该模块只被 /stock 页加载，就改用导出期已有的轻量判定或
  复用各面板已在用的门控数据源，报告说明选择）。

### T4（P3）insiders.html 无页级 as_of
- form4 面板 as_of=2026-08-20 有数据未展示。照 site 惯例补页级 as_of 披露
  （参考同页其他面板或 stakes 页头 as_of 锚的既有组件/i18n 键，复用不新造）。

### T5（P3）stakes 页 as_of 披露
- 窗口日期已由主线修入副标题；补 as_of（ stakes_13g.json as_of=2026-08-21）到同一披露行或
  页头惯例位。

### T6（P3）congress 页 tx 卡 as_of 锚位混淆
- 页级锚是 v1 面板（politician_trades 08-18），tx 卡数据源 v2（politician_trades_tx 08-20）
  未显示。在 tx 卡头部补其自身 as_of，消除双版本并存误读。

### T7（P3）overview.tsx:604 附近注释 "40 in the committed panel" 未随 +2 同步
- 改成不写死数字的表述（如 "the curated roster length"）或更新为 42——前者优先。

## 2. 验证

```bash
cd F:\ZCodeData\Aionis-wi\web && npx tsc --noEmit && npx eslint src --max-warnings 33
cd F:\ZCodeData\Aionis-wi && PYTHONPATH="$PWD/src" uv run --project F:/ZCodeData/Aionis pytest -q tests/test_web_terminal_data.py
```
若动到面板 JSON 的契约锚（不应该——本任务零数据改动）才需要更多。build 留主线。

## 3. 铁律与报告

纯 display-lane；0 ledger/frozen/config/prereg/OOS；零 Python/导出改动；不 push；
不碰 docs/code-review/；junction 永不 rm -rf；小步 commit（建议 T3 一笔、P3 批一笔）。
报告：(a) T3 各视图修复前后链数与门控数据源选择；(b) T4/5/6 披露位与 i18n 键（对称新增若有）；
(c) T7 处置；(d) 验证 exit codes；(e) 冲突面声明。
