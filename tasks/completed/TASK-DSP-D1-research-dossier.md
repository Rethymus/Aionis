# TASK-DSP-D1 — 溯源研究档案管线(来源研究 → 报告生成 → 建模分析,全程 [S#] 可溯源)

- Lane:display/export 派生(只读 tracked 工件:web/src/data/aionis/*.json、runs/ledger.jsonl、docs/、decisions/、reports/evidence/;**零网络、零 runs/ 写、零冻结触碰、零 now()**)
- 设计依据:`reports/design/2026-08-28-evidence-corroboration.md`(Trust-Tiered Librarian=LLM 研究报告需可信分级+溯源;OpenPM=可审计评估)、G2 先例(atlas-claim-v1.html 字节稳定工件)
- 业主命题:"覆盖基于来源的金融研究、报告生成到金融建模与分析的完整流程,全程可追溯可溯源"。本任务=该流程的 v1 落地:**溯源研究档案(Research Dossier)生成器**。
- 你是本轮唯一 dev agent(D),分支 agent/dsp 已检出。**不 push、不删 worktree。**

## 管线架构(三阶段,一个生成器)

- **Stage 1 基于来源的金融研究** → **S-registry(来源登记表)**:从 tracked 工件装配 S1..Sn,每条 = `{id, type, locator, integrity, license, role}`:
  - `type:"panel"` — web/src/data/aionis/*.json(metrics/ic_monthly/calibration_reliability/score_diagnostics/data_health/api_catalog/evidence/headline_provenance);integrity=**文件内容 sha256**(生成时现算)。
  - `type:"ledger"` — runs/ledger.jsonl 的特定行(最新 `phase:"sensitivity_horizon"` exploratory 行;config_committed 行若可定位);integrity=行 JSON 文本 sha256+行号。
  - `type:"doc"` — docs/phase-d-preregistration.md 等预注册与 docs/data-intake-rubric.md;integrity=文件内容 sha256。
  - `type:"artifact"` — reports/evidence/atlas-claim-v1.html(G2 工件);integrity=sha256。
  - `type:"external"` — knowledge_shelf.json 的编辑精选外链书签;integrity=`"external: self-declared"`(诚实标注不可机器核验)+ URL。
- **Stage 2 报告生成** → `reports/evidence/research-dossier-v1.html`:**单文件自包含**(内联 CSS+SVG+表格,零 JS 零外部资源零字体,浏览器直开),字节稳定(零时钟、排序写死、双跑 sha 一致),浅色卡面/单蓝强调 WCAG AA,方向编码不用红绿。
- **Stage 3 金融建模与分析** → 档案的模型与分析章节:全部数字读 committed 面板实值(metrics/IC 序列/校准/score_diagnostics/horizon sweep ledger 行),并显式呈现分析链:config_sig → ledger freeze 行 → result 行 → 面板 snapshot。

## 档案章节(每节所有数字与论断旁标 [S#];无 S# 支撑的句子不得陈述数字)

1. **执行摘要**:预注册两尾差分主张一句话 + 头条读数(IC/CI/p/n/verdict/SESOI/config_sig/ledger_row)[S:metrics, S:headline_provenance]
2. **研究设计与门禁**:预注册设计摘要、7-gate 摄入、purged CV+embargo、H6 确定性 [S:doc(预注册,sha), S:doc(data-intake-rubric,sha)]
3. **数据来源与可溯源性**:api_catalog 汇总(49 端点 × source/license/as_of 分组计数)+ data_health 三类新鲜度 [S:api_catalog, S:data_health]
4. **建模与分析**:冻结链(config_sig_short → ledger_row freeze→result)→ 合并 IC 森林图(SVG)→ 66 月 IC 条形 → 校准汇总(ECE/pooled)→ score_diagnostics 摘要(秩自相关范围)→ horizon 稳健性(读 ledger 行:h=10/42 四相 null_holds)[S:各面板, S:ledger]
5. **证据与文献语境**:evidence.json 15 行表 [S:evidence] + Harvey-Liu-Zhu t>3.0 语境(引用为外部文献,S 条目 type:"external",integrity 如实标 self-declared)+ 编辑精选外部研究书签选录 [S:knowledge_shelf external 条目]
6. **局限与边界**:NULL 判定的诚实呈现(纪律的胜利)、探索 vs 确认分离、E3 forward-live 状态如实("已实现待业主契约冻结")、面板新鲜度边界
7. **引用完整性自检**:S-registry 全表 + 机检结论(每个 S# 被引用 ≥1 次;每个渲染数字可回溯)——生成器内置 closure 检查,违反即 raise(不静默)

## 交付物

1. `scripts/export_research_dossier.py`(唯一生成器;G2 的 `scripts/export_evidence_html.py` 是结构与字节稳定先例,先读它)
2. `reports/evidence/research-dossier-v1.html`(生成并提交;重跑双算 sha256 一致)
3. `tests/test_research_dossier_pipeline.py`(hermetic 零 skip):
   - 合成夹具:生成器在合成面板上跑通;S-registry sha 正确;closure 检查(删一个引用→raise);
   - 真实工件:与 metrics.json 逐字对账;零外部资源(http/https/src=/script/link/@import/url( 全查);字节稳定(双渲染相等);S# 引用闭包;ledger 行 sha 与实际文件行一致;
4. 引擎常量 `DOSSIER_VERSION = "v1"`(文件头与溯源脚注使用)。

## 纪律(违反=失败)

- 不改任何既有文件;不加依赖;不碰 ledger 写/frozen/config/prereg;不碰 runs/(只读)
- 数字仅来自 committed 工件;语态=呈现测量与设计,不给投资建议;NULL 按仓库立场如实呈现
- **[S#] 闭包是硬门**:生成器对"数字无引用"或"引用无来源"必须 raise

## 验证与提交(worktree 内;0xC0000142/fork 失败=本机病理,sleep 30-60 重试)

```bash
uv sync --all-extras
uv run pytest -q tests/test_research_dossier_pipeline.py tests/test_evidence_html_artifact.py -x
uv run ruff check scripts/export_research_dossier.py tests/test_research_dossier_pipeline.py
```

全净后单原子 commit(分支 agent/dsp)。报告:S-registry 全表(type/locator/integrity 摘要)、双算 sha、章节实嵌数字清单、测试输出、文件大小。
