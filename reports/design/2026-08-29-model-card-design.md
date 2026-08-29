# 可追溯金融建模:模型卡(model card)设计规格 — 文献印证版

- 日期:2026-08-29(轮㊟)
- 状态:APPROVED(本轮 H4 实施;单进程)
- 证据分级:**A = 本次 API 实检**(arXiv 摘要逐条核对,2026-08-29);**B = 领域知识**(未在线核验,标注);不采信任何凭空条目。

## 1. 命题:什么才是"可追溯的金融建模"

建模环节的追溯性 = 模型的**身份、数据输入、特征、超参、随机性、CV 方案、库版本、账本链**全部机器可读、哈希钉定、人类可读、可在终端呈现。Aionis 已有:ledger(config_committed 先于 result,sha256)、H6 确定性(bit-identical)、冻结 config.json(实测含 feature_cols×9/horizon=21/n_splits=5/embargo=21/cv_scheme/frozen_params 全超参含 seeds=0/versions(lightgbm 4.7.0, purgedcv 0.1.2, arch 8.0.0)/输入 sha×4+uv_lock)。**缺口**:这些字段散在 gitignored 冻结产物里,无人类可读、无可发现、无文献对齐的**模型卡**。

## 2. 文献印证(逐条 A 级,arXiv API 2026-08-29 实检)

| 文献 | 日期 | 对本设计的印证 |
| --- | --- | --- |
| **Model Cards for Model Reporting**(Mitchell et al.) | 2018-10 | 模型卡=透明度工件的奠基规范:身份/预期用途/评价数据/指标分节——本卡骨架直接对齐 |
| What's documented in AI? 32K AI Model Cards 系统分析 | 2024-02 | 大样本证据:实践中的模型卡普遍**缺完整性**——佐证"卡片必须机器生成+哈希钉定,不靠手写" |
| Position: Current Model Cards Are Insufficient for Downstream Governance of Open-Weight Foundation Models | 2026-06 | 当前卡对**下游治理不足**——治理需要可机器校验的钉定(我们用 sha256+ledger 行号,正是该方向) |
| **Datasheets for Datasets**(Gebru et al.) | 2018-03 | 数据集文档规范 → 本卡"数据输入"节:4 个输入 sha+PIT 语义+end_lag 逐项可溯 |
| NeurIPS 2019 Reproducibility Program(Pineau et al.) | 2020-03 | 复现清单制度 → 本卡"复现"节:H6/种子全 0/n_jobs=1/uv_lock sha |
| A Large-Scale Measurement of **AI Bill of Materials** Completeness in Hugging Face Models | 2026-07 | AI-BOM 完整性可测量 → 本卡=投资研究域的 BOM:库版本/数据哈希/代码版本全列 |
| Who Built This Model? LLM Lineage via Spectral Fingerprints | 2026-08 | 血统追踪前沿(权重指纹);Aionis 用 config_sig+ledger 行号做经典域的血统链 |
| FAIR Principles(HEP 应用) | 2022-11 | Findable/Accessible/Interoperable/Reusable → 面板化(JSON)= FAIR 的 A 与 R |
| **[B 级]** SR 11-7(美联储模型风险管理指引) | 2011 | 银行业模型治理三件套:**模型清单/文档/独立验证**——模型卡即清单+文档,契约测试即验证 |
| **[B 级]** López de Prado, *Tactical Investment Algorithms* | 2019 | 主张"算法应以伪代码+数据规格+配置发布供验证" → 本卡把冻结 config 全文结构化公开 |

## 3. 卡片规格(全部机器读自已提交/冻结工件,零手写数字)

- `identity`:phase="track_c_confirmatory"、config_sig(全)+short、results_dir、aionis_version、schema、h6_deterministic、run_ts(取 meta.ts,非时钟)
- `intended_use`:预注册两尾 null-expected 主张一句话 + display-only + 非投资建议 [S: docs/track-c-preregistration.md sha]
- `data`:fund/prices/membership 三输入 sha、end_lag(10-K:6/10-Q:4)、feature_cols(9 列全列)、universe/membership 语义
- `model`:learner=lightgbm(versions.lightgbm)、frozen_params 全 dict、seeds(bagging/feature_fraction/drop=0,n_jobs=1)、purgedcv/arch 版本
- `evaluation_protocol`:cv_scheme 原文、horizon=21、n_splits=5、embargo_sessions=21
- `results`:metrics.json 实值(IC/CI/p/n/verdict/SESOI/config_sig_short/ledger_row)
- `governance`:ledger freeze 行(ts/sha/行号)→ result 行、uv_lock_sha256、**本卡的 S 式溯源脚注**(G2/D 体例)
- 呈现:/model-health 新"Model card"节(双语 i18n、字段表格、sha mono)

## 4. 确认性 run 目录解析(实现要点)

4 个 runs/results/<sha> 目录中,以 **ledger result 行的 config_sig** 对应 `meta.json.config_sig` 匹配确认 run;本地缺失 → `_safe_export` 诚实 SKIP(既有守卫)。
