# Commit ecd68a1b6ceebdb57f5f1c5cd0d745ea7048dc2e 审查报告

**提交信息**: docs(dashboard): v2 design — near-final quant-eval interface (5 dimensions)（2026-07-29，Rethymus）
**改动范围**: 1 个文件，+403/-0；新增 `docs/dashboard-v2-design.md`——dashboard v2 的设计文档（5 评估维度、3 个数据缺口、8 标签布局、许可证核验表、分片构建顺序），纯设计、不含代码。

## 四维度结论
| 维度 | 结论 | 一句话说明 |
|---|---|---|
| 稳定性 | ✅ | 纯文档；设计含"诚实无数据守卫"（缺产物→提示不崩溃） |
| 可扩展性 | ✅ | 数据层扩展全部 additive + 向后兼容（旧 run 缺产物只禁用相关图表）；分片构建顺序每步可演示 |
| 生产可用 | ✅ | "dashboard 是 reader+plotter、绝不重算引擎"的边界声明直接守护 H6 与防泄漏纪律 |
| 高内聚低耦合 | ✅ | 推理全部回流 eval/* 既有模块；事件研究显式标注 exploratory until registered |

## 对照参考
文档本身就是对照研究（alphalens/pyfolio/quantstats/empyrical/zipline-reloaded/mlfinlab 六项许可证核验）。独立复核：alphalens-reloaded、pyfolio-reloaded、empyrical(-reloaded) 确为 Apache-2.0（github.com/stefan-jansen/*、pypi.org），文档判定无误；mlfinlab 非许可（NOASSERTION）拒绝引入，与 AGENTS.md 许可白名单一致。"add ZERO new runtime deps by default" 的结论与项目 KISS/YAGNI 哲学一致。方法论引用（Grinold-Kahn IC/IR、Brown-Warner 事件研究、MacKinlay 1997、Künsch MBB、Politis-White）均为标准出处。

## 问题清单
### P3-1 「purgedcv (Apache-2.0-equivalent NCSA)」措辞松散
- 描述：§4 表格下方写 "purgedcv (Apache-2.0-equivalent NCSA)"——NCSA 与 Apache-2.0 并非等价许可证（条款义务不同），而项目白名单明文只列 MIT/Apache/BSD；purgedcv/arch 实为 AGENTS.md 技术栈既定依赖（豁免既成事实），但用 "equivalent" 措辞弱化了白名单的严格性，为后续引入 NCSA 系依赖开了模糊先例。
- 位置：`docs/dashboard-v2-design.md:296`（§4 Bottom line 段）
- 影响范围：仅文档措辞；不新增依赖。
- 修复建议：改为如实陈述（"purgedcv/arch 为 NCSA，已在技术栈既定白名单内、先于本设计引入"）。
- 修复成本：低
- 状态：未修复

## 领域红线核查
- 防泄漏 ✅：事件研究锚定不可变披露日期（13D filing_date / ALFRED vintage / FRED release，G3-safe）；"OOS 面板 PIT-safe by construction"；dashboard 永不进研究管线的重算路径。
- 账本纪律 ✅：h≠21 视图明确 EXPLORATORY 徽章；事件研究"exploratory, not confirmatory, until registered"；对既有 confirmatory 结果与 sha256 零触碰（additive only）。
- 许可白名单 ✅：拒绝 mlfinlab；quantstats 虽核验为 Apache-2.0 但因"残余模糊"保守地不作为运行时依赖。

## 总体评分
9/10 — 高质量设计文档：数据缺口诊断准确（后续 257336c/ec35d97d/d2acf325 恰按 Gap 1-3 落地）、许可证核验经独立复核无误、诚实呈现纪律贯穿（preliminary-data 徽章、EXPLORATORY 标注、无数据守卫）；仅一处许可证措辞松散（P3）。
