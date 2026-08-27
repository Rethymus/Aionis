# TASK-DISP-H — i18n 孤儿键审计与保守清理（zh/en 对称）

**Lane**: display（纯前端 + 一个静态扫描脚本）。**优先级**: P2（续㉗ 记录 58/476 孤儿键"低优先
清理候选"，此后字典已增至 ~1,197 键/语言，本轮审计其现状）。
**工作目录**: worktree `F:\ZCodeData\Aionis-wh`（分支 `feat/i18n-cleanup`，junction 已挂，LF ledger 已预拷）。

## 0. 目标

产出可复用的孤儿键扫描器 + 按其结果**保守清理**确证无引用的键。诚实结果合法：
若扫描证明孤儿键比历史记录少得多（此前 58 的口径可能含动态组合引用），如实报告、少删或不删。

## 1. 扫描器（`web/scripts/i18n-audit.mjs`，新增，node 直跑）

1. 解析 `src/i18n/dict.ts`：键格式为 4 空格缩进 + 双引号（如 `"brand.name": "…"`），
   zh 块与 en 块各约 1,197 键。用稳健解析（括号深度法或成熟正则均可），**不要**
   依赖单引号假设（前人踩坑：t() 实参多为双引号）。
2. 全 src 扫描引用：`t("…")` / `t('…')` 及任何 `dict.xxx` 直引、模板拼接
   `` t(`prefix.${x}`) `` ——模板拼接视为**前缀引用**：`prefix.` 开头的全部键视为被引用。
3. 输出三清单：确证孤儿（零静态零前缀引用）/ 存疑（仅前缀匹配）/ 双语不对称键。
4. 报告 stdout 摘要 + 写 `web/i18n-audit-report.json`（gitignored 或临时文件均可，不提交）。

## 2. 清理规则（保守优先）

- 只删"确证孤儿"，且 zh/en 同步删（保对称）；存疑键一律保留并在报告列出。
- 每删一批跑：`npx tsc --noEmit`（DictKey 类型由 zh 对象推导，被引用键误删会立刻编译红）
  + `npx eslint src --max-warnings 33` + 相关 pytest（web 契约测试有引用 i18n 的用例就跑它）：
  `cd F:\ZCodeData\Aionis-wh && PYTHONPATH="$PWD/src" uv run --project F:/ZCodeData/Aionis pytest -q tests/test_web_terminal_data.py`
- 若 tsc 红 → 回滚该键（扫描器误判），计入误判统计。
- **零功能改动**：不改任何组件/视图；只动 dict.ts 与新增扫描器脚本。

## 3. 验证

tsc 0 / eslint 0 error / pytest exit 0（上述文件）；build 留主线。
若全仓 ruff 需跑：本任务零 Python 改动则跳过。

## 4. 铁律与报告

纯 display-lane；0 ledger/frozen/config/prereg/OOS；不 push；不动主仓；junction 永不 rm -rf；
小步 commit（扫描器 → 清理）。
报告：(a) 扫描器实现要点；(b) 三清单数字（确证/存疑/不对称）与历史 58 的对照结论；
(c) 实删键清单（zh=en 同步证据：清理后两侧键数相等）；(d) 误判回滚记录；(e) 验证 exit codes；
(f) 冲突面（预期仅 dict.ts + web/scripts/ 新脚本；与其他 lane 的 dict.ts 追加无冲突——不同区域）。
