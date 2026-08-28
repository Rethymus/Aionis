# TASK-DISP-R1A — 分数面诊断透视图(export 派生面板 + /atlas 第四区块,垂直切片)

- Lane:display/export 派生(只读冻结产物 `runs/track_c_confirmatory_oos_scores.parquet`;**0 抓取 / 0 frozen 写 / 0 config / 0 prereg / 0 ledger / 0 OOS 计算**——本任务只对已冻结的分数做描述性统计,不产生任何新研究主张)
- 设计规格:`reports/design/2026-08-28-editorial-diagram-language.md` §6 R1-lite(本轮落地)
- 你是本轮唯一 dev agent,可在自己的 worktree 内改共享文件(dict.ts / page.tsx / index.ts);主线集成时无并发冲突。

## 背景(主线已核实的事实)

- `runs/track_c_confirmatory_oos_scores.parquet`(1.1MB,94,438 行):列 `date(datetime64, 月末) / ticker(str) / region(str: "us"|"cn") / score(float64)`。这是 confirmatory run 的冻结横截面 OOS 分数。
- decile 收益单调性(金标准诊断)需要全样本前向收益——**本轮明确不做**(口径漂移风险,业主门,见规格 §6);改做纯分数面诊断。

## 交付物(全部在 worktree 内完成并原子提交)

### 1. 导出函数 `scripts/export_quarto_data.py`(与 export_ic_monthly 同区、同风格)

`export_score_diagnostics()` → `score_diagnostics.json`(根级 list,行结构):

```json
{"month": "2021-01", "region": "cn", "n": 812, "score_mean": -0.12, "score_std": 1.02, "score_iqr": 1.31, "rank_autocorr": null}
```

- 月键 `YYYY-MM`(ic_monthly 同款);按 month 升序、region 字典序排序。
- `n`:当月该区域横截面股票数;`score_mean/score_std` 一阶矩;`score_iqr` = P75−P25(线性插值分位)。
- `rank_autocorr`:当月与**上一个有数据月**在重叠 ticker(内连接)上的 score Spearman 秩相关(pandas `.corr(method="spearman")`);重叠 <30 只 → 如实 `null`(首月必 null)。区域独立计算(us 与 cn 各自链)。
- 数值 `round(float(x), 6)` 保证字节稳定;json 写法与 export_ic_monthly 完全同款(含是否 _stamp 由它现有模式决定,跟随即可)。

### 2. 注册三件(`scripts/export_terminal_data.py`,grep 定位)

- `main()`:`_safe_export("score_diagnostics", eq.export_score_diagnostics)`(ic_monthly 行后)。
- data_health 注册表:`("score_diagnostics", "score_diagnostics.json", _DH_FROZEN)`(ic_monthly 行后)。
- as_of 分支:`if key == "score_diagnostics":` 取最后一行的 month(照 ic_monthly 分支写法)。
- api_catalog source 映射:`"score_diagnostics": ("Aionis research artifacts (repo MIT)", "confirmatory OOS cross-sectional score diagnostics (display-only derivation)")`(ic_monthly 行后)。

### 3. 契约测试 `tests/test_score_diagnostics_panel_contract.py`(新文件,hermetic)

- 用**标注为测试夹具的合成 parquet**(tmp_path 构造,允许——mock 仅限测试夹具是仓规)断言:精确 n/mean/std/iqr;构造已知秩关系的两月断言 rank_autocorr 精确值(用 scipy-free 的独立算法或 pandas 双算交叉验证);重叠<30 → null;首月 null。
- 已提交面板调和测试:读 `web/src/data/aionis/score_diagnostics.json`(你会在 worktree 生成并提交它)——形状断言(字段全在/region ∈ {us,cn}/month 升序不重)+ 与 ic_monthly.json 的月覆盖调和(score_diagnostics 的 (region,month) 覆盖 ⊇ 对应区域 IC 月,宽松不等于——两源都从同一分数 parquet 派生但聚合窗口可差一月,如实断言你实测的关系并写明)。
- 全部断言基于你实测生成的真实 JSON 写死期望,不许 `pytest.skip`/`pytest.mark.xfail`。

### 4. Web barrel `web/src/data/aionis/index.ts`

显式契约类型(仓规:绝不 `as typeof json`):

```ts
export type ScoreDiagnosticsRow = {
  month: string; region: string; n: number;
  score_mean: number; score_std: number; score_iqr: number;
  rank_autocorr: number | null;
};
```

import + `aionis` 对象注册(照 icMonthly 的内联写法或具名类型,风格就近)。

### 5. i18n `web/src/i18n/dict.ts`(zh/en 各一段,atlas 块末尾追加)

`atlas.diag.title`(分数面诊断透视图 / Score-surface diagnostics)、`atlas.diag.desc`(说明:派生自冻结 confirmatory OOS 分数,纯描述性统计;秩自相关=相邻月重叠 ticker 的横截面 Spearman;重叠<30 诚实留空)、`atlas.diag.disp.title/desc`(月度分数离散度/标准差带)、`atlas.diag.breadth.title/desc`(宇宙宽度/每月每区域股票数)、`atlas.diag.ac.title/desc`(分数惯性·月度秩自相关;0.5/0 参考线)、`atlas.diag.table`(数据表(无障碍与降级回退))、`atlas.diag.n`({n} 个月 · {start} → {end})。措辞遵守红线:呈现测量,不给投资建议。

### 6. 区块组件 `web/src/components/atlas/atlas-divergence.tsx` 同目录新文件 `atlas-diagnostics.tsx`

- "use client"、默认导出 `AtlasDiagnostics`;`aionis.scoreDiagnostics`;`diagram` tokens + `primitives`(scaleLinear/niceTicks/DiagramFigure);零 Date/random;蓝橙/主色系,禁红绿方向语义。
- 面板 A 离散度:US/CN 双面板,每月 score_std 竖带或面积(附 IQR 细线可选),y 轴 niceTicks。
- 面板 B 宽度:每月 n 竖条,US/CN 双面板。
- 面板 C 惯性:rank_autocorr 折线(两区域一线,null 断开),0 与 0.5 虚线参考。
- 每面板完整 `<table>` 回退(表头永远渲染;字段名列头可用语言中立字面量,force-camp 先例)。
- 卡片风格与三区块一致(Card + 区块标题 h2)。

### 7. 页面 `web/src/app/(dashboard)/atlas/page.tsx`

- 已是 client 壳(sr-only h1 + SegmentHeader + 三区块);在 AtlasDivergence 之后、AtlasDataflow 之前插入 `<AtlasDiagnostics />`。

### 8. 生成并提交真实 JSON

worktree 内已拷贝真实 parquet(主线复制,`runs/track_c_confirmatory_oos_scores.parquet`)。运行(仓库根):

```
uv run python -c "import sys; sys.path.insert(0,'scripts'); import export_terminal_data as m; m._safe_export('score_diagnostics', m.eq.export_score_diagnostics)"
```

生成 `web/src/data/aionis/score_diagnostics.json`(真实数据,非 mock);提交它。

## 验证(worktree 内,全部贴实际输出)

1. `uv run pytest -q tests/test_score_diagnostics_panel_contract.py tests/test_web_terminal_data.py`(worktree 有 .venv 由 uv 自动建;若个别存量测试因 worktree 缺 gitignored data/ 而失败,如实记录——只要求你新增的测试与 web 契约测试全绿)。
2. `cd web && node node_modules/typescript/bin/tsc --noEmit` → 0 error。
3. `cd web && node node_modules/eslint/bin/eslint.js src/components/atlas/atlas-diagnostics.tsx src/i18n/dict.ts src/data/aionis/index.ts "src/app/(dashboard)/atlas/page.tsx"` → 0 error。

## 提交

单原子 commit(Conventional Commits,如 `feat(web): score-surface diagnostics panel — export derivation + contract tests + atlas section (display lane)`)。分支 `agent/r1`(已检出)。**不 push、不删 worktree、不跑 next build。**

## 报告要求

实测统计摘要(月数/区域覆盖/rank_autocorr 范围/最宽离散度月)、pytest/tsc/eslint 实际输出、任何偏离与理由。
