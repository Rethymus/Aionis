# 重接手深度审计 — 疏漏 / 失效预演 / 功能提案 / 提效方案（2026-10-07，轮 221）

> 性质：业主 /goal 委托的深度研究审计（docs/研究 lane）。方法 = 本地全库审计 + 三个并行外部研究
> 代理（量化方法论论文 / 同类开源项目功能 / 运维与可复现性实践，结论浓缩于 §F，全部带来源）。
> **不重复声明**：项目自身反思周期 1-5（轮 205-217，含 `2026-10-07-deep-reflection-round4.md`）
> 已覆盖的面（可复现标识符、OpenBB alerts 不适配、Streamlit 五问等）此处只引用不重做。
> 边界：0 ledger / 0 frozen / 0 OOS。

## A. 明显疏漏（按严重度；状态：✅本日已修复 / ◻建议 / ⛔业主门）

1. **🔴 `data/` 5.7GB 不可重取历史零异地备份。** `backup_audit_chain.py`（轮 172）只把
   ledger+git bundle 备份到**同机** `data/backups/`。磁盘损失 = GDELT 新闻情绪史（2017→，
   源只伺服近期窗口，历史**不可重取**）、provider cutoff 探针记录、抓取缓存史全部不可逆。
   对策（⛔业主门，需 B2 账号 ~$6/TB/月）：restic → Backblaze B2，Windows 原生 + VSS +
   `--pack-size 64` 控 class-C 费用（§F-运维-6）。git-annex/DVC 不适（前者自称非备份系统，
   后者是管线版本化非 DR）。
2. **🟡 白名单 ISC / Matplotlib 悬置一个月。** 2026-09-09 审计旗标（lucide-react=ISC、
   matplotlib=PSF 系）至昨日未裁决，而白名单规则"表外即 REJECT"使文档与现实自相矛盾。
   **✅本日已修复**：v0.3 补两行等价认定（ISC≈MIT；Matplotlib≈BSD-3，同 NCSA 先例）。
   业主如不认可等价判定可否决（reversible，一行 revert）。
3. **🟡 无 SECURITY.md、无 pre-commit 防线。** 公共仓无漏洞报告通道；"Forbidden：commit
   .env/data/parquet"仅靠纪律。**✅本日已修复**：`SECURITY.md`（含 PolyForm-NC 滥用举报
   通道——业主防"包装转售"的执行入口）+ `scripts/precommit_guard.py`（data/、*.parquet、
   .env、>5MB 四规则，`.env.example` 模板豁免）+ `.pre-commit-config.yaml`（纯本地钩子，
   Windows/Git-Bash 安全）。**待业主激活**：`uv tool install pre-commit && pre-commit install`。
4. **🟡 证据级联正典顺序无交互入口。** 顺序咬合（dossier 内嵌 atlas sha、shelf/matrix 重钉
   必须最后）先后咬人三次（2026-09-09 许可级联、轮 182、轮 215）；晚间通道已编码顺序但
   与 75 分钟抓取熔合，午间交互改导出器仍靠记忆。**✅本日已修复**：
   `scripts/evidence_refresh.py`（通道导出尾的逐字提取，进程内直调，`--check` 跑同一证据
   门测试子集，`--dry-run` 打印计划）+ 4 个 hermetic 测试钉死顺序不变式。
5. **◻🟡 `docs/RESULTS.md` 停在 v0.1（2026-07-31）。** README 称其"活页快照"，实际滞后
   两个月（Track B 七主题 nulls、E3 影子窗启动、ADR-008 主张族扩充都未入页）。刷新需
   逐数对账（研究事实面），建议专轮。
6. **◻🟡 无全局多重性注册表。** ADR-008"broaden the null family"（RES-01..10 强基线族）
   将增加预注册主张数，但跨主张的 trial 计数无处聚合（现仅策略节单点 `n_trials=20`）。
   DSR 的 n_trials 应随主张族增长而全局登记——建议设计 claims registry（研究面，需任务
   规格 + 业主过目）。
7. **🟢 轮 92 的 Plan B（self-hosted runner）可正式否决。** 2026-03-01 起私有仓自托管
   runner 收平台费 $0.002/分钟；而本仓现为公共仓 = Actions 无限 + Pages 免费（100GB/月
   软带宽，静态研究站远达不到）。CI 成本风险面实际已收缩。
8. **⛔🟢 Zenodo concept DOI + release 归档缺失。** 近零成本换来：永久可引（ACM "Available"
   徽章级）+ Software Heritage 自动互链 + 巴士因子保险。配 CITATION.cff 已就绪，只差业主
   在 Zenodo 开关 GitHub 集成。

## B. 没有把握的部分（Uncertainty Register）

1. **PolyForm-NC 可执行性未经诉讼检验**（目标司法辖区尤甚）；许可=请求权基础（下架/索赔），
   不是免疫——骗子本就违法。SECURITY.md 通道 + DMCA 模板（建议入 runbook）是完整执行链。
2. **GDELT 间歇伺服缓存批次**（轮 211）：检测已根治，上游行为不受控；"有记账"≠"有数据"。
3. **uv.lock sig 搁浅**（Phase B OOS 面板，blockers 在案）：DROP/重冻/收窄 sig 三选一未裁。
4. **E3 第二影子窗 10-31 未到**；点火 = 业主 GO（ADR-010 门）。
5. **provider cutoff 探针是保守下界**（2023-03-10）：真实训练截止不可观测，E2 门为下界近似。
6. **诚实 null 叙事 vs 被误读**：外部读者可能把"全 NULL"读作"项目失败"。对策见 D.1。

## C. 失效预演（假设 6-12 个月后方案失效，最可能的断点排序）

| # | 失效模式 | 概率×损伤 | 已有防线 | 缺口→对策 |
|---|---|---|---|---|
| 1 | **笔记本磁盘损失**：data/ 历史不可逆 | 中×致命 | 同机 bundle | A.1 restic→B2 |
| 2 | **单人巴士因子**：业主停摆→通道静默腐烂（历史同类："7/38 路由腐烂"） | 中×高 | 月报自动化、staleness 绊网 | README"停摆声明"+Zenodo 归档（A.8） |
| 3 | **数据源断供**：Tiingo/Alpaca key 过期或 API 破坏性变更 | 中×中 | 软败记账、staleness、源节奏文档 | 源冗余映射表（Alpaca↔Tiingo 价格互备）入 runbook |
| 4 | **GitHub 平台事件**（账号误判/锁定） | 低×高 | 每晚 git bundle 本地 | Zenodo+SWH 异平台镜像（A.8） |
| 5 | **叙事失效**：null 被读作失败、流量停滞 | 中×中 | README 教养段 | D.1 Verdict Board 把 null 证据产品化 |
| 6 | **许可滥用事件**：真被包装售卖 | 低×高（声誉） | PolyForm-NC+ADR-013+SECURITY 通道 | DMCA/警告信模板入 runbook |
| 7 | **依赖 CVE 破例困境**：版本钉=H6 纪律 vs 安全通告需升级 | 低×中 | 轮 216 双侧审计流程化 | "CVE 破例决策树"入 WORKFLOW 附录（重锁→ADR→重跑 H6 断言） |

## D. 亮眼功能提案（代理排名 × 现有雏形核查后；成本 S<1天 / M=数天）

**首推两项（S 级、纯展示层、素材全有）：**
1. **Verdict Board（裁决榜）** — qlib 式基准表的能量反转 payload：全部预注册主张
   （B/C/D/E1/Track C/Track B/E3 look）一页榜：差分 rank-IC + 95%CI + 裁决徽标
   （NULL CONFIRMED）+ config sha + ledger 行链接。现有 /evidence、/confirmation 散落
   各主张卡，无集中 leaderboard。这是"把紧 CI 的 null 做成可交付物"的产品化。
2. **可证明预注册页（hash 时间链）** — 每主张一页链式证明：prereg 文档 sha →
   config_committed ledger 行 → git commit hash → 结果工件 sha。2026 年 SSRN 7417918
   才出现"密码学时间戳预注册交易策略"的论文，**尚无开源项目做过**——差异化之最，
   且 Aionis 已持有全部素材（纯展示层，display lane）。
3. `aionis verify-run <sig>` 公开确定性验证器 + H6 故事页（M）— nautilus"回测/实盘同
   代码路径"式信任叙事的 Aionis 版：验证器从 ledger 重算哈希核对工件。
4. Claim Browser：每主张一页可引用卡（IC 序列图+敏感性网格+裁决）（M）— OSAP Signal
   Browser 是其 666+ 引用的第一驱动。
5. pip 客户端 `aionis-data`（M）— 包已公开的只读数据 API（OSAP openassetpricing 先例）。
6. "Cite this null" BibTeX 页（S）+ 中文优先入口定位（S，qlib/FinRL 的中文受众红利）。
7. **已有雏形、不再重复建**：`/discipline`（=代理提案"泄漏自审 walkthrough"，freqtrade
   lookahead-analysis 式）、`/data-health`（=vintage 页）、昨夜变更条（=What's New）、
   README hero GIF（=终端漫游动图，9-09 已入）。
8. **明确不做**（代理结论与宪法一致）：收益排行榜样叙事、实盘/交易控制面、fair-code
   分层销售（vectorbt 模式）。

## E. 全流程提效

- **✅已实施（本日）**：`evidence_refresh.py` 单入口（结构性消灭级联顺序事故类）；
  pre-commit 防线（待激活）；SECURITY.md；白名单 v0.3。
- **◻建议（S）**：`justfile` 四命令包装（`just fetch` / `just lane` / `just evidence` /
  `just check`——2026 共识 runner，Windows+Git-Bash 一等公民，make 的陈旧性语义对"必须
  总是按序跑"的证据管线是错的）；新机器 bootstrap 文档（uv sync → pre-commit install →
  .env.example → fetch 顺序）。
- **◻建议（M）**：RESULTS.md 专轮刷新并把"confirmatory 结果变更即刷快照"写进 DoD；
  restic→B2 runbook（docs/ops-offsite-backup.md）。
- **已有强项**（不需要动）：晚间通道全自动+月报五步验证、契约门先于 push、staleness
  绊网、bundle diet 战役（793KB 首页）。

## F. 外部情报浓缩（全部带来源；全文见本轮会话研究记录）

**方法论（12 项，择要）**
- **purgedcv（MIT，已安装！）内含 CPCV/PBO/CSCV/DeflatedSharpe/min-TRL**——现只用
  PurgedGroupKFold；加 PBO 诊断 = 零新依赖。github.com/eslazarev/purged-cross-validation
- **CRSP 磁带重写事件**（Schwarz-Walter-Weiss, JFQA 2026-03）：供应商静默改史使已发表
  回测不可复现 → **建议账本行增设数据快照哈希**（抓取 parquet 内容哈希+日期），把
  "不修订契约"升级为"可验证契约"。cambridge.org（DOI 10.1017/s0022109026102774）
- **近零 IC 外部验证**（SSRN 6742700, 2025）：大盘股截面可达成 IC 实证上界≈0——四相
  NULL 是学科预期的外部佐证，支持 SESOI 等价框架。
- Jensen-Kelly-Pedersen（JoF 2023）复制率 ~82% 收敛于 ~13 主题——"紧 CI null 有信息量"
  立场的当前共识区间。
- **LLM 记忆泄漏可量化**：Glasserman-Lin（arXiv 2309.17322）两形态定义；Didisheim 等
  （Econ. Letters 2025）记忆探针法；Chen 等（AER 2025）ChatGPT 历史收益重构偏差 →
  建议 E3 加"记忆探针"泄漏诊断（让模型回忆训练期 S&P 月度赢家并记账）。
- Registered Reports 已进金融期刊（SFS: APS/RCFS）+ Arpinon（2025）警示：预注册 null
  仍可能输给未注册阳性——支持"null 自发布于 RESULTS.md"路线。
- 其余：Arian 等（2024）PBO 估计器自身的噪声（引用以预防审稿人"为何不只 PBO"）；
  Witzany（2021）CSCV 贝叶斯批评；OpenSourceAP/CrossSection 作 SESOI 经验先验校准集；
  Guimaraes（2025）分层贝叶斯（monitor）。

**运维（6 项）**：ACM 徽章四级映射（Available≈Zenodo DOI 近零成本）；pre-commit 栈
（ruff→守卫→gitleaks 可后补）；just 优于 make/poe/taskipy；Zenodo+SWH+2FA 恢复码+
"if-I-disappear"注记；公共仓 Actions 无限/Pages 免费/自托管 2026 起收费；restic→B2
（~$6/TB/月）为 gitignored 多 GB 缓存的 2026 务实答案。

**功能（15 选 3 不做）**：浓缩入 §D。

## G. 行动清单

| 状态 | 项 | 落点 |
|---|---|---|
| ✅ 本日 | evidence_refresh.py + 4 测试 | scripts/ · tests/ |
| ✅ 本日 | precommit_guard.py + pre-commit 配置 + 3 测试 | scripts/ · .pre-commit-config.yaml |
| ✅ 本日 | SECURITY.md（含许可滥用举报通道） | SECURITY.md |
| ✅ 本日 | 白名单 v0.3（ISC/Matplotlib 补正） | docs/data-license-allowlist.md |
| ◻ 下轮 S | Verdict Board 裁决榜 | web 终端新路由（display lane） |
| ◻ 下轮 S | 可证明预注册 hash 链页 | web 终端新路由（display lane） |
| ◻ 下轮 S | justfile + bootstrap 文档 | justfile · docs/ |
| ◻ 下轮 M | RESULTS.md 刷新 + DoD 钩子 | docs/RESULTS.md |
| ⛔ 业主门 | restic→B2 异地备份（A.1，最高优先） | 账号+密钥+runbook |
| ⛔ 业主门 | Zenodo DOI + 停摆声明 | 平台开关 |
| ⛔ 业主门 | CPCV/PBO 诊断任务化（零新依赖） | 研究面任务规格 |
| ⛔ 业主门 | 账本行数据快照哈希设计 | 研究面（动账本 schema，需 ADR） |
| ⛔ 业主门 | E3 点火 GO（10-31 第二窗后） | TASK-E3-launch |
