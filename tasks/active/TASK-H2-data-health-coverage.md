# TASK-H2 — data_health 注册全覆盖契约(P0-3③ 制度化:web barrel 面板 ↔ data_health manifest 一等性)

- Lane:display 测试(纯新增测试文件;零生产代码改动——若测试抓出真实漏注册,如实报告并停在报告层,不擅自改生产)
- 背景:R1A 轮 score_diagnostics 差点漏 data_health/api_catalog 注册(agent 自裁补救)。既有契约已钉 api_catalog↔data_health key 一等性;本任务把最后一环钉死:**web barrel 消费的每个面板 JSON 都必须在 data_health manifest 有行**(漏注册=新面板在数据健康地图/API 目录隐身)。
- 你是本轮唯一 dev agent(H2),分支 agent/h2 已检出。**不 push、不删 worktree。**

## 交付物(唯一新文件)

`tests/test_data_health_coverage_contract.py` — hermetic,零 skip:

1. **barrel ↔ data_health 覆盖**:import `web/src/data/aionis/index.ts` 的注册面(在测试里维护一张显式清单:barrel 注册的每个面板 key → 期望 data_health category;从 index.ts 的 `aionis = {...}` 逐 key 提取,硬编码清单并注释"新增面板必须同步此表")——断言每个 key 都在 `data_health.panels` 有行且 category 匹配。注意 barrel 含非面板成员(如 stock_universe/lineage_graph/companies_dir 等独立模块与派生面板)——以 data_health manifest 实际行集为准构建期望集,**先跑一次盘点再写死**,清单即文档。
2. **反身断言**:data_health.panels 的每个 key 都能在 `web/src/data/aionis/` 找到对应 JSON 文件(防幽灵行)。
3. **atlas 消费面专项**:metrics/ic_monthly/calibration_reliability/score_diagnostics/data_health/api_catalog 六个 atlas 直接消费面板各自 present=true 且 as_of 非空(score_diagnostics 的 as_of=末行 month 语义)。
4. 若发现真实漏注册/幽灵行:**不改生产**,把发现写进报告与测试的 xfail?——不,仓规禁 xfail/skip。处理:若发现漏注册,直接把该发现作为报告顶项交回主线,测试先写成"当前实况断言"(把实况作为期望值写死并注释 `# KNOWN-GAP` 标记行,待主线修复后翻转为严格断言);若零缺口,直接写严格断言。

## 验证与提交(worktree 内)

```bash
uv sync --all-extras
uv run pytest -q tests/test_data_health_coverage_contract.py tests/test_web_terminal_data.py -x
uv run ruff check tests/test_data_health_coverage_contract.py
```

全净后单原子 commit(分支 agent/h2)。报告:barrel 面板盘点清单(逐 key+category)、发现的缺口(若有)、测试清单、输出摘要。
