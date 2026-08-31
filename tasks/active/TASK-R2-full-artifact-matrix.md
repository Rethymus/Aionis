# TASK-R2-full — 证据工件矩阵（多 claim 档案 · 版本化 · CI 挂钩）

- 编号: R2-full（roadmap §5 P2-10，2026-08-31 Planner 拆分前置完成）
- 标题: 把"单 Track C 主张"的自包含证据工件（atlas-claim-v1 / research-dossier-v1）扩展为
  **五主张证据矩阵**（B / C / D / E1 / Track C），加版本化与 CI 自动重导钩子。
- 状态: **READY — Planner 拆分完毕，切片可独立派发（单 agent 串行纪律）**
- 优先级背景: `reports/design/2026-08-28-future-roadmap-research.md` §5 P2-10。
- 边界: **export/display lane；runs/ 只读；0 ledger 写 / 0 frozen / 0 prereg / 0 OOS 计算**。
  真实管线禁 mock。全部切片不做任何 fetch（输入均为已 committed 面板与 runs/ 冻结产物）。

## 现场地基（均已存在，逐条核实过）

- 渲染器: `scripts/export_evidence_html.py`（atlas-claim，`render_html(load_panel(PANEL_DIR))`）与
  `scripts/export_research_dossier.py`（dossier，main()）。两者均为字节稳定契约
  （`tests/test_evidence_html_artifact.py`、`tests/test_research_dossier_pipeline.py`
  的 committed == fresh-render 断言）。
- 注册点: `scripts/ks_sources.py`（stdlib-only 书签字面量单一来源）+ knowledge_shelf
  Layer-3"证据工件"（导出时现算 sha）。
- 输入: 五相各自 `runs/results/<sig>/differential.json`（B=17245a75…, C=a7fdb48f…,
  D=d3158063…, E1=ef321e9e…）+ Track C `web/src/data/aionis/metrics.json`；账本
  confirmatory 行（#28/#30/#34/#37/#49）。

## 切片（S/M/L，每片独立验证、独立 commit）

### S1 — 矩阵清单 manifest（S，半天）
`export_evidence_matrix_manifest()`：枚举五主张（phase、ledger 行号、results 目录 sig、
differential.json 关键值 mean/ci_lo/ci_hi/dm_p、当前工件 sha 与字节量），写
`reports/evidence/evidence-matrix-v1.json` + 注册进 `export_terminal_data.py` main()。
hermetic 契约测试：五相齐、账本行号对账、sha 与磁盘重算一致、字节稳定双跑。
**验收**: pytest 文件级绿 + ruff 净。

### S2 — 每相 dossier 参数化（M，1-2 天）
把 dossier 渲染器按 phase 参数化（目前 Track C 中心），为 B/D/E1 各渲染一份
`research-dossier-<phase>-v1.html`（C 复用现有文件名不动——**不改名不移位既有工件**）。
输入即各相 differential.json + save_run 产物（IC 序列存在性守卫：缺失则该相降级为
"meta-only" 卡并如实披露，不造数）。shelf Layer-3 逐相注册。
**验收**: 每份工件字节稳定双跑 + 契约测试 + 全套 pytest exit 0。
**注意**: 证据链重导正典次序 = 面板 → atlas → dossier → shelf（轮 51/52 实战定律）。

### M3 — 版本化与保留（M，1 天）
manifest 增 `version` 字段（v1 起步）；重导后旧版本移动至
`reports/evidence/archive/<version>/`（move-don't-delete，AGENTS 铁律）；shelf 条目
指向当前版本并在 methodology 披露历史版本路径。契约测试钉"当前版本指针一致 + 归档
目录只增不删"。
**验收**: 同 S1 + 归档行为有一个真实重导的实测记录。

### M4 — CI 挂钩（M，半天 + 门）
`.github/workflows/refresh-terminal-data.yml` 数据刷新步之后追加
`python scripts/export_evidence_html.py && python scripts/export_research_dossier.py`
（continue-on-error + 显式 timeout，学 13D 步先例）。**硬门: Actions 计费封锁未解前
仅提交 workflow 改动不启用**——workflow 已处 disabled 态，本片完成即"接线完毕待解冻"，
如实记录，不得宣称 CI 已在跑。
**验收**: workflow YAML 语法校验（actionlint 或 python yaml parse）+ 本地等效命令序列
实测一遍（正是轮 52 已跑通的 面板→atlas→dossier→shelf 正典次序）。

### L5 — 终端矩阵页（L，1-2 天）
`/shelf` 或 `/track#evidence` 扩展矩阵卡：五相工件卡（phase/裁决/sha/字节量/GitHub
链接），数据源 = S1 manifest 面板。i18n zh/en 对称（dict 只加不删）；hermetic 契约测试。
**验收**: tsc 0 + eslint 0 + build 页数 +1~0 + 目视终验（明暗双主题）。

## 完成定义
每片: 验收绿 → 增量 Conventional Commit（`feat(evidence): R2-full S1 …`）→ 全套 pytest
exit 0。全片完成: roadmap §5 P2-10 销项 + 本文件移 `tasks/completed/`。
**红线**: 任何一步发现需要写 ledger / 动 prereg → 立即停，进 backlog 待预注册级业主 GO。
