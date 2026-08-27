# TASK-DISP-D — DEF14A 人名降噪（"Age" 后缀粘连修复，display 数据 lane）

**Lane**: display / bounded-parse。**优先级**: P1（⑱ 轮目视终验记录的残余项）。
**工作目录**: worktree `F:\ZCodeData\Aionis-wd`（分支 `feat/def14a-name-denoise`，junction 已挂，LF ledger 已预拷）。
**授权**: 业主"设计开发任务区分、分配给不同 agents 直接推进"常设指令。

## 0. 问题陈述（已实测核实）

`web/src/data/aionis/def14a_persons.json` 的 `top_persons` 中出现 3 个人名带 " Age"
后缀粘连：`Charles M. Chiappone Age` / `John B. Blystone Age` / `Mark C. Davis Age`
（50 人中 3 个）。这是解析正则把申报文档里 "NAME Age" 行标结构的 Age 字样吸进名字所致。
下游影响：`/executives` PersonsSection 人名显示怪异；`lineage_graph.json` 的 co_board
person 节点以 `_lg_norm(name)` 为 id —— 同一真人的干净名与脏名会被当成两个人，
可能少并边。上游来源：`src/aionis/ingest/def14a_persons.py`（先读它定位捕获点）。

## 1. 目标

在 ingest 层修名字归一化，使人名不再携带结构性后缀；**分级诚实计数照旧披露**；
重导出 def14a_persons.json 与连带派生（lineage_graph/data_health），全部被契约测试钉住。

## 2. 规则（严格逐条执行）

1. 只允许剥离**可证明的结构性尾部**：候选模式 = 尾部独立 token `Age`
   （大小写变体）与紧随其后的孤立 2-3 位数字年龄（如 `John Smith Age 64` →
   `John Smith`）。逐条列在实现里成为数据常量，不许任何 fuzzy/模糊匹配。
2. **绝不合并不同真人**：归一化后若与既有条目产生新碰撞，如实计数为
   `same_name_merges_possible` 的真实发生数（该字段已在 coverage 里），不删除任何行。
3. 分级桶（section+age / name+role / unparsed / no-doc）的**判定逻辑不动**——
   本次只修 name 字符串内容，各方法计数允许因同批姓名清洗而轻微移动，逐个披露 old→new。
4. 重导出链：`export_def14a_persons` → 重跑内联三函数
   （lineage_graph → data_health → api_catalog；不许全量 main()）。
   断言 lineage 的 co_board 边涉及这 3 人处的节点 label 已清洁，且总边数变化如实报告
   （若有边的两pté端被同一真人合并，w 可能增大——这是**正确结果**，不是回归）。

## 3. 交付物

1. `src/aionis/ingest/def14a_persons.py`（或其实际分离的解析函数处）：降噪规则 +
   注释写明模式依据。
2. 契约测试（tests 内既有文件追加或新建 `test_def14a_person_names.py`）：
   - no exported name matches `/\sAge$/`；
   - 三个已知案例归一化到期望值（钉死这三个具体字符串是允许的——它们是 bug 实证）；
   - roles/companies/n_director_seats 字段在修复前后对同一个人保持不变；
   - 若缓存原始 HTML 在本地（`data/cache/` 下 grep def14a），离线重放零网络验证；
     否则做一次有界重抓（≤40 文档、≥2.1s、预算记账写进报告）。
3. 重导出产物（committed JSON ×3）+ 报告附 before/after 差异摘要（人数、计数移动、边变化）。

## 4. Worktree 环境注意（沿用）

```bash
cd F:\ZCodeData\Aionis-wd
PYTHONPATH="$PWD/src" uv run --project F:/ZCodeData/Aionis pytest -q tests/test_web_terminal_data.py tests/test_def14a_person_names.py
```
CRLF ledger 假红 → 从主仓复制原件覆盖。前端无需改动（label 是数据驱动）；
若 tsc/eslint 全绿即不需要跑（本任务无 .ts 变更时跳过）。

## 5. 铁律

纯 display-lane；0 ledger/frozen/config/prereg/OOS；不 push；不动主仓工作树；
不碰 docs/code-review/；junction 目录永不 rm -rf。

## 6. 报告格式

(a) 捕获点定位结论；(b) 规则实现说明 + 三个已知案例的修复证据；(c) 离线/联网判定与请求账；
(d) 计数移动表（old→new）；(e) lineage 边变化摘要；(f) 验证命令 + exit codes；
(g) 冲突面声明（预期仅 def14a 相关导出/测试/JSON 三件 + 主线会统一重生成汇总面板）。
