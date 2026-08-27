# TASK-DISP-F — 明星投资人准入 +2（Corvex / GAMCO，按策展门槛规格执行）

**Lane**: display / data-curation（已获授权路径：设计规格全 PASS 由主线代裁采纳）。
**工作目录**: worktree `F:\ZCodeData\Aionis-wf`（分支 `feat/stars-admission`，junction 已挂，LF ledger 已预拷）。

## 0. 裁决依据（主线已完成裁决，你负责落地）

- 门槛规格：主仓 `reports/design/2026-08-26-stars-curation-bar.md`（六闸门制）。
- 证据报告：主仓 `reports/design/2026-08-26-stars-candidates-evidence.md/.json`
  （Corvex/Keith Meister CIK 0001535472 与 GAMCO/Mario Gabelli CIK 0000807249 六闸门全 PASS；
  前者 ≥13 季连续、Q2 HR filed 2026-08-14；后者同 Q2 filed 2026-08-12）。
- **采纳决定**：两人准入。中文名按证据置信执行——GAMCO zh_name = `"GAMCO（加贝利）"`（high 置信）；
  Corvex zh_name = **null**（medium 置信按 S7/G4 惯例宁缺毋滥）。类别：Corvex=activist，
  GAMCO=value。
- **禁止事项**：不动 Pershing Square 等在册任何条目（其 watch 态是数据事实如实展示，非本轮范围）；
  不采纳 BORDERLINE/UNVERIFIED/FAIL 任何人（Southpoint/Icahn/Baron/Gundlach/Bessent 等）；
  不新增第八类别；绝不凑数。

## 1. 工作项

1. 读 `scripts/form13f_fetch.py::MANAGERS`（策展唯一事实源），按该字典既有精确格式追加两行
   （CIK → verbatim 实体名以证据报告的 data.sec.gov 权威名为准 / zh_name / category）。
2. 有界抓取两位新人的持仓书：复用 form13f fetch 管线的既有 per-manager 能力
   （先读懂它怎么跑：manifest/checkpoint/幂等缓存）。请求预算 ≤40、≥2.1s、逐条记账。
   目标 = 证据报告中他们最新已申报季（2026-Q2）的数据进 parquet 聚合与导出链。
3. 重导出链（内联调用，绝不全量 main()）：form13f 相关 export → export_form13f_stars →
   export_lineage_graph → export_data_health → export_api_catalog（顺序满足派生依赖；
   具体函数名 grep 确认）。
4. 预期连锁变化全部如实记录：明星计数 40→42；/manager/[cik] SSG 页 +2；
   home 统计条"明星投资人"数字自动跟随（验证即可，不改代码）；form13f.json ticker 覆盖数变化；
   lineage co_hold 可能新增边（两位新人可见书与他人交集）——如实给前后对比。
5. 验证：
   ```bash
   cd F:\ZCodeData\Aionis-wf
   PYTHONPATH="$PWD/src" uv run --project F:/ZCodeData/Aionis pytest -q tests/test_web_terminal_data.py tests/test_form13f*.py
   PYTHONPATH="$PWD/src" uv run --project F:/ZCodeData/Aionis pytest -q   # 全套 exit code 为准
   ```
   契约测试均为派生锚（roster 变化无须编辑测试）；若有测试红，查你的数据链同步问题而非改测试语义。
   ruff 三件套（改动文件）净。
6. 小步 commit（Conventional Commits）：curated roster 行 → 抓取+重导出产物。

## 2. Worktree 注意

PYTHONPATH + 主仓 venv（editable 指向主仓）；CRLF ledger 假红从主仓拷原件覆盖（已预拷）；
不 push；不动主仓工作树；junction 目录永不 rm -rf；0 ledger/frozen/config/prereg/OOS。

## 3. 报告格式

(a) MANAGERS 追加行原文（verbatim 对齐证据）；(b) 抓取请求账；(c) 导出链输出摘要行；
(d) 连锁变化前后对比表（stars 计数/ticker 覆盖/lineage 规模/页数预期）；(e) 验证 exit codes；
(f) 冲突面声明（预期 form13f.json/form13f-stars/lineage_graph/data_health/api_catalog +
manager-[cik] 新页由 build 产出，dict.ts 应零改动）。
