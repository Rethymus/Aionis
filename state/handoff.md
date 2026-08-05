# state/handoff.md — current-pass handoff

## 2026-08-05 (i) power-floor 理论推导 — 纯噪声界 + ML 噪声超额（机制性定理）

业主第三次问"最具价值方向" + Stop hook 纠偏（自审通过即执行，勿再请示）。批判性过滤后选 power-floor
理论推导（唯一能显著抬高王冠贡献的方向；其余 ceremony/diminishing）。自审循环通过（闭式可推、复用既有
面板、不触冻结面）→ 直接执行。

**核心数学事实**：横截面 Spearman rank-IC 在无预测力零假设下 σ_null = 1/√(N−1)（闭式）。
N=462→0.047，N=929→0.033，N=1386→0.027。但 Aionis 21 个 IC 系列实测 σ(IC) 一致地是 σ_null 的
**2.0-4.4×（median 3.41×，min 2.03×，无例外）**。

**机制性结论**（比"σ≈0.10 floor"更精确诚实）：
- 纯噪声界 σ=0.047 时 look-3 n_min = (1.96×0.047/0.010)² ≈ **83 月 < 120** → 纯噪声本可在 look-3 达等价。
- 实测中位 σ=0.109 时 look-3 n_min ≈ **456 月** → 不可行。
- **power floor 不是纯数学必然，而是由 ML 噪声超额驱动**（拟合噪声 + 异方差 + 重叠）——稳健跨 21 系列。

**交付**：
- `scripts/ic_pure_noise_bound.py` — 算 N_cross（从中位 OOS 面板）+ σ_null + σ_obs + 超额比；21 系列。
  ruff clean。`runs/ic_pure_noise_bound.json`（gitignored）。
- `tests/test_ic_pure_noise_bound.py` — 6 测试（闭式 1/√(N−1) 正确性 + 单调 + 已知值 + N<2 NaN + n_cross_eff
  中位/分区/min-max + 缺列空）。6/6 绿。
- `reports/design/2026-08-05-power-floor-theoretical-derivation.md` — 闭式推导 + 21 系列超额表 + 机制分解
  （ML 拟合噪声/异方差/重叠）+ refined honest claim（"floor = 纯抽样界 + ML 超额"，非"σ≈0.10 规律"）。
- `manuscript/main.tex` §5.3 — 加"Theoretical pure-noise bound and the ML noise excess"子节
  （power-floor 升为"理论 + 经验 + 文献"三支撑）。

**批判性自审记录**（业主要求）：① 纯噪声界 0.047 < 实测 0.10，会否削弱？→ 不削弱，反而更 sharp（floor
由超额驱动，非纯界）；② 推导会否成兔子洞？→ 限定为闭式界 + 经验超额，不推一般理论；③ 外部 GKX 验证？
→ 先不做（可行性未证），内部 21 系列 + 闭式已足。

**边界**：本轮 1 新 script + 1 新 test + 1 新 note + manuscript §5.3 编辑 + state；**0 ledger / frozen surface /
prereg / ADR / config / data / E3 改动**；未跑 confirmatory/forward/strategy/research；未触 E3；未外发。

## 2026-08-05 (h) arXiv preprint scaffold（rec #2；framing a；PREP，未上传）

owner approved framing **(a)**（power-floor 定理为 lead）+ LaTeX 预制。交付 `manuscript/` 三件套：
- **`manuscript/main.tex`** — arXiv 通用 `\documentclass{article}`（仅标准宏包 amsmath/booktabs/hyperref/natbib；
  无自定义 .cls → 任何 TeX Live/Overleaf 可编译）。framing (a) 重排：power-floor 入 abstract+intro，§5 详述
  （n_min 869/580/435 + 跨 20 系列 σ∈[0.092,0.163] 实测）。§4 证据表 15 行；§7 复现声明指向 `docs/replication-availability.md`。
  数字与 ledger #49 + 中文 v1.0 + 英文 v1.0-en 交叉一致。
- **`manuscript/references.bib`** — 6 cited（gu2020empirical/goyal2008comprehensive/grinold1999active/lakens2017
  = WebSearch verified；schuirmann1987/jennison2000group = 标准 methods）+ 5 标准 extras（neweywest/obrienfleming/
  dieboldmariano/ke2017lightgbm/deprado2018）供扩展。
- **`manuscript/README.md`** — 构建（latexmk / Overleaf）+ framing 说明 + provenance + prep-to-submission gaps（诚实：
  uncompiled / 引用细节待确认 / 无图 / 作者占位 / venue 待选）+ elsarticle 可在定 venue 后替换。

**验证（无本地 TeX 工具链，无法编译）**：结构性自查——9 \begin = 9 \end，环境全配对
（abstract/center/enumerate/itemize×2/table/tabular×2），6 cite key 全部在 .bib 定义。

**边界（关键）**：owner 批准的是**预制**，**非上传**——arXiv 上传是不可逆外发，仍需业主单独点头。
本轮纯新建 `manuscript/` + state；**0 ledger / frozen surface / prereg / ADR / config / data / E3 改动**；
未跑 confirmatory/forward/strategy/research；未触 E3；**未外发**（无 arXiv 上传）。

**待业主**：① 在 Overleaf/自带 TeX 首次编译（修可能的 minor LaTeX 问题，标准宏包风险低）；② **授权 arXiv 上传**
（不可逆外发）；③ venue 定位（CFR/JFEc/RevFin，positioning brief §4）→ venue-specific tailoring（篇幅/强调）；
④ 作者+单位占位填充。

## 2026-08-05 (g) 发表强化 — power-floor 文献锚定 + 复现/数据可用性声明（2 新 PROPOSED 文档）

owner 第二次 `/goal` 授权"推进推荐项 + 批判性比对 + 并行 agents + 分层省 token + reuse-first"。
方向 1（power-floor 文献锚定）+ 互补的复现声明交付。**两 sonnet agent 均 [1210] 失败 → 全 opus §8 fallback**。

- **`reports/design/2026-08-05-power-floor-literature-anchoring.md`** — 把 σ≈0.10 从"我们的观察"升级为
  "有文献支撑的方法学结果"。WebSearch 验证 4 引用（出版商页 403 → 用作者公开 PDF + 搜索摘要）：
  ① **Gu-Kelly-Xiu (2020, RFS)** "Empirical Asset Pricing via Machine Learning"：最佳 ML 月 OOS R² **1.08-1.80%**
  → mean IC ~0.05-0.12 量级（R²≈IC²）；② **Goyal-Welch (2008, RFS 21(4):1455-1508)** 综评预测难度；
  ③ **Grinold-Kahn** *Active Portfolio Management* + Fundamental Law：年化 IR **0.5="good"** ⟹ mean IC/σ(IC)≈0.14
  ⟹ σ(IC)≈7×mean IC；若 mean IC≈0.015 → **σ(IC)≈0.10**（与 Aionis 0.106 量级一致）；④ **Schuirmann (1987) TOST** +
  **Lakens (2017)** equivalence primer（cited 2792）。**诚实边界**：精确 σ(IC)=0.10 的单一标准文献未找到——
  通过 mean IC 水平 + Fundamental Law 间接推断（§5 标注 ⚠️）。但 power-floor 结论稳健：只要 σ(IC)∈0.08-0.15
  文献一致区间，SESOI ±0.010 等价宣告即不可达（look-3 n_min σ=0.08 时 ~21 年，σ=0.15 时 ~58 年）。**推荐强 framing (a)**
  把 power-floor 升为一等方法学贡献（JFEc 计量 / CFR 再检验轨道）。

- **`docs/replication-availability.md`** — reproducible-by-construction 声明（positioning brief §6 标记的审稿人关切）。
  反泄漏纪律即复现契约（`config_committed` ledger + H6 bit-identical + tracked fetch 脚本）；逐源 license 表
  （EDGAR/FRED/ALFRED = US-gov 公共领域可再分发 / Tiingo/Alpaca 需自有 key 不再分发 / baostock A 股 / hanshof+pierrebrunelle
  MIT 成分）；独立方复现步骤（clone → .env → fetch → runner → H6 断言 bit-identical）；cover-letter 简版。
  引用全部核验真实（`.env.example` ✓ / `TIINGO_API_KEY`+`FRED_API_KEY` ✓ / H6 三重断言 ✓ / ledger 行号 ✓）。

**批判性比对（业主"先比对再选择"）**：研究新切片（强基线/LLM eval/新特征）低于产出收尾且重引入"治理>产出"失调；
E3 被 power floor 证可选。剩下自主高价值 = 抬高论文天花板（power-floor 锚定）+ 移除外发摩擦（复现声明）。

**分层 + reuse + 独立性**：2 sonnet `general-purpose` agent 均因 [1210] 失败（positioning→powerfloor 同模式，
WORKFLOW §17 停重试）→ opus §8 fallback 直接写。文献/复用：WebSearch（非 403 出版商页）+ 既有 ledger/脚本引用。
独立性局限：两文档均 opus 自写（非独立 subagent pass，已披露）；数字（climax #49 + power analysis）由既有双独立审计背书。

**边界**：本轮纯 docs（2 新 PROPOSED 文档）+ state；**0 ledger / frozen surface / prereg / ADR / config / data / E3 改动**；
未跑 confirmatory/forward/strategy/research；未触 E3；未外发（无 arXiv 上传）。**未改已定稿的 draft v1.0 / v1.0-en**
（两新文档通过 state + git 可发现；venue tailoring 时由业主决定是否并入引用，避免为边际指针重开定稿）。

**待业主**：① framing 选择（a 强 power-floor / b 中 / c 弱）；② 是否补 σ 直接实证（重算 Gu-Kelly-Xiu 公开 IC 系列 σ，
或合成 IC 噪声实验）；③ arXiv 投稿时把 4 引用并入 `references.bib`；④ 复现 package 形态（仅公共领域子集 + 用户自有 key /
Zenodo DOI 归档——外发需点头）。

## 2026-08-05 (f) 产物化收尾 — 英文 draft + 经济透镜 sweep + venue 定位 brief

owner `/goal` 授权"推进推荐项 + 批判性比对 + 并行 agents + 分层省 token + reuse-first 禁造轮子"。
3 推荐 + 1 fallback 全部交付（4 commit + 1 memory，全 push origin/main）：

- **`e94eac2` feat(site)** — 静态站点 Track C climax section（KPI tile + 表 + power-floor reframing）；
  3 新 hermetic 测试，25/25 绿；CI 部署成功（Pages 已更新）。
- **`3a3c2cf` feat(scripts)** — bps 敏感度 sweep（`track_b_net_cost_sweep_run`，**复用 `net_cost_summary`**，0 造轮子）：
  真实 Track B treatment 面板（ef321e9，125 月）衰减曲线 gross 0.149（bps=0）→ bps=5 0.125（≈0.43 年化，匹配 mount② / draft 引用）
  → bps=20 0.054 → bps=50 −0.088；**break-even ≈31 bps**；turnover 1.1444 跨 bps 恒等。8/8 hermetic 测试绿（含反退化：
  gross 跨 bps 恒等 + net 单调衰减 + 线性 cost scaling + break-even 插值 + _parse_bps 校验）。
- **`52a3d69` docs(draft)** — 英文 v1.0-en（`docs/methods-and-results-draft-en.md`，18KB）：sonnet agent 忠实翻译；
  全部关键数字（−0.0088/0.484/NOT_EQUIVALENT/RCI[−0.051,+0.027]/n_min 869/580/435/36.2y/2.772/99.44%）与 ledger #49
  + 中文 v1.0 交叉核对一致；framing 忠实（null + 纪律 + power-limit，非 equivalence declared）。
- **positioning brief**（本 commit）— `reports/design/2026-08-05-publishable-unit-positioning.md`：venue 匹配决策包。

**批判性比对（业主"先比对再选择"）**：英文 draft 不盲目翻 12KB——venue 决定语气/篇幅/重点，故 positioning brief
与翻译并行（而非串行）。venue 规格 web search 验证：**CFR**（Ivo Welch，免费 boutique，10-20 篇/年，~28 天 turnaround，
"takes more risks"/"all types of documents"，replication/re-examination 导向 = 最高 fit）/ **RevFin**（明示"irrespective
of whether the findings"= null 友好）/ **JFEc**（计量方法 fit，power-floor + J-T 门归宿）/ **Quant Finance**（理论+实证，
rapid）/ **arXiv q-fin.ST**（免费 baseline）。出版商精确页 403 处诚实标注 ⚠️，未编造数字。

**推荐路径**（brief §4）：① arXiv preprint（立即/免费/时间戳）；② CFR 首选（免费 + ~28 天 + null-再检验 fit，
frameworking (a) 反泄漏纪律为主）；③ 备选 JFEc（框架 b 计量）或 RevFin（null 友好）。

**分层 + reuse 合规**：2 sonnet `general-purpose` agent 并行（英文 draft ✅ 交付 / positioning ❌ [1210] 失败）；
positioning 失败 → **opus §8 fallback 直接写**（非独立 subagent pass，已披露）。sweep 复用既有 `net_cost_summary`
（0 造轮子）；CI 复用既有 deploy workflow；定位复用公开 venue 规格。

**独立性局限（披露）**：positioning 非独立 pass（agent [1210] 死，opus 自写）；英文 draft 单 agent + opus 数字核验；
sweep opus 自写 + 8 反退化测试。数字（climax #49 + power analysis）由既有 2026-08-05 双独立审计背书
（power-analysis sonnet review + climax diff review 均 APPROVE）。

**待业主**：① 选 venue 路径（CFR / JFEc / RevFin / 仅 arXiv）；② **授权 arXiv preprint 上传**（外发不可逆，需点头）；
③ framing 选择（a 治理 / b 计量 / c 估计量）；④ 英文 v1.0-en → venue-specific tailoring（brief §4 映射表已给）。

**边界**：本轮纯 docs/scripts(state-only)/state/memory；**0 ledger / frozen surface / prereg / ADR / config / data / E3
改动**；未跑 confirmatory/forward/strategy/research；未触 E3；未外发（无 arXiv 上传）。全套 hermetic pytest exit 0
（仅预存 forward-score/numpy warnings）；ruff clean。

## 2026-08-05 (d) Power analysis — J-T schedule 结构性欠功率（设计级发现，业主决策待定）

climax #49 后的自然跟进："look-1 NOT_EQUIVALENT → look-2/3 能否宣布等价？" opus 直接写
`scripts/track_c_power_analysis.py`（analytic HAC-SE 投影 + block bootstrap 2000 次 + min-n 计算）+
`runs/track_c_confirmatory_power_analysis.json`（gitignored artifact）。

**发现**（用 ledger #49 IC series 噪声 σ≈0.106 + ρ≈0.07，校准自 observed se_hac=0.0126@n=71）：
| Look | z | n_min 宣布等价 | P(equiv) | RCI half med |
|---|---:|---:|---:|---:|
| 1 (60) | 2.772 | 869 月（72.5y）| 0.0000 | 0.037 |
| 2 (90) | 2.263 | 580 月（48.3y）| 0.0000 | 0.025 |
| 3 (120) | 1.960 | 435 月（36.2y）| 0.0000 | 0.019 |

**判读**：look-1 NOT_EQUIVALENT 不是"look-1 太保守"的局部现象，而是**整个 60/90/120 schedule 在
SESOI ±0.010 下的必然状态**。月频 rank-IC 噪声地板（σ≈0.10）使 ±0.010 等价宣告在现实样本量不可达；
E3 forward-live 即使点火也需 ~36 年才达 look-3 等价。**这是诚实的方法学发现（power floor），非 bug**。

**贡献 reframing**（已写进 draft §5/§6）：项目主贡献 = ① 反泄漏纪律作为研究对象（不变）；② 15 条 null
点估计（强 evidence 无 alpha）；③ **power-limit 披露**（J-T ±0.010 在月频 rank-IC 的 power floor）。
非"等价已宣告"。draft §5 的 look-1 框架已从"局部保守"升级为"结构性欠功率"。

**业主 3 选项**（`reports/design/2026-08-05-track-c-power-analysis-options.md`）：
- **A（推荐）** 接受 reframing：不动冻结面，贡献 = null + 纪律 + power-limit。
- B 拓宽 SESOI ±0.025：新 amendment #49b；look-3 (n=120) RCI half 0.019 < 0.025 → 可达等价；
  但 post-hoc "moving goalposts" 嫌疑 + 等价意义减弱。
- C 延长 horizon n=435：不可行（36 年）。

**独立性**：sonnet review of power analysis methodology 派发中（`reports/audits/2026-08-05-power-analysis-review.md`
待回报）。数字由 opus 自算；bootstrap seed=0 pinned（H6 精神）。

**边界**：本轮纯新建 script + design brief + docs(state) 更新；**0 ledger / frozen surface / prereg / ADR 改动**；
未跑 confirmatory/forward/strategy；power analysis 用 gitignored artifact（不改 frozen surface）。

## 2026-08-05 (c) CONFIRMATORY CLIMAX — 首条 confirmatory OOS 入账（ledger #49）

owner D6 GO 授权（"按推荐方式处理 + 难度分层派 agent + 并行不互扰 + 冲突最高价值优先 + 结果不乐观再调整重测"）。
**目标**：把 Track C 联合折叠从 exploratory 升格为首条 confirmatory（项目的 logical climax）。

**判据**：null 在本项目是预期可发表产物，**非"不乐观"**；只有工程 bug（H6 失败 / 退化 / 时序违反）才触发
"调整重测"。实际结果 = null 点估计 + 欠功率 look-1，属预期，未触发调整。

**交付**：
- **`scripts/track_c_confirmatory_run.py`**（opus 直接写，反泄漏 climax 件）：
  - `verify_frozen_config()` 校验 `track_c_amend2.build_amendment()` 重现 sig `e14b9d44...`（漂移即 abort）
  - `assert_h6_identical()` 双跑 bit-identical（`.equals` + `.tobytes` + CSV hash 三重）
  - `jt_reachable_looks()` 作用在 `combined_ic_series`（Reading A：rank-IC 是 gated 估计量；cond_beta 仅 explanatory）
  - `build_confirmatory_row()` 构造 `confirmatory:first` ledger 行
  - artifact-reuse 模式（`TRACK_C_CONFIRMATORY_FROM_ARTIFACT=1`）：dry-run 已双跑证明 H6 → GO 直接 load
    summary.json 写 ledger，避免 46min 重跑（4 守卫：缺文件 / sig 错 / H6 False / 正常 append）
- **`tests/test_track_c_confirmatory_run.py`**：19/19 hermetic 绿（frozen sig 校验 + H6 pass/fail + look
  reachability 边界 + row 构造 + artifact-reuse 4 守卫 + 空/NaN 边缘用例）
- **dry-run 双跑**（~46min，macro join ONCE 优化后）：H6 bit-identical PASS → artifact-reuse GO commit 瞬时

**结果（ledger #49，bit-identical 于 asym41 exploratory）**：
| 量 | 值 | 判读 |
|---|---:|---|
| combined rank-IC 均值 | −0.008841 | null（p_hac=0.484，CI [−0.034,+0.016] 跨零）|
| US IC / CN IC | +0.0052 / −0.0265 | 双区均 null |
| conditional-IC β（regime 交互）| −0.0076（p=0.43）| null；multiplicity 预算 1 保持 |
| **J-T look-1**（n=60，RCI 99.44%）| **NOT_EQUIVALENT** | RCI [−0.051,+0.027] 宽于 ±0.010 SESOI = 欠功率 |
| H6 双跑 bit-identical | PASS | 真实数据确定性验证 |

**climax 判读（诚实）**：null 点估计 + 欠功率 look-1 = **预期结果**。
- 点估计 null（−0.0088）与全部 14 条 exploratory null 一致（confirmatory 等级下 treatment 仍无正增量）。
- look-1 NOT_EQUIVALENT 是 **power 声明**（OBF z=2.772 极保守 + 月频 IC se≈0.014 → 99.44% RCI 必然宽于
  SESOI），**非效应信号**。门设计意图就是 look-2(n=90)/look-3(n=120) 才判等价。
- **J-T 门拒绝在欠功率下过早宣布等价，即使点估计 null = 反泄漏纪律的活体演示 = 方法学贡献**。
- 严格等价判定需 E3 forward-live 累积日历时间（look-2 ≈ 2028，look-3 ≈ 2031）。

**独立性**：sonnet `general-purpose` code-reviewer APPROVE（0 CRITICAL / 1 HIGH=informational estimand
稳健 / 1 MEDIUM=test 边缘 gap[已补]/ 2 LOW）；7 项反泄漏审查全 PASS。报告
`reports/audits/2026-08-05-confirmatory-runner-review.md`。J-T + H6 + 沉积的可复现性由 frozen #48 + 脚本保证。

**docs**：`docs/methods-and-results-draft.md` v0.1 → **v1.0-draft**（§5 实填 confirmatory + §4 加 #14 asym41
彩排 / #15 confirmatory climax + §0 摘要 + §7 不越界声明更新）。

**边界**：本轮 1 行 ledger（#49 append-only confirmatory:first）+ 新建 scripts/tests/docs(state) + 1 份
audit report；**B/C/D/E1 + Track B 冻结面 / prereg / ADR / config 未改**；未跑 research/forward/strategy；
未触 E3。artifact-reuse 是持久化已 dry-run 验证的结果（config #48 frozen 先于 dry-run 观察 → config_committed
BEFORE result 保持）。

**待业主**：① 审 v1.0-draft → 定稿（中/英 + 期刊定位）；② 是否 push（origin/main 落后若干 commits）；
③ look-2/3 长期路径（E3 forward-live ignition，年级别）。

## 2026-08-05 P1 整合 + P0 confirmatory-GO brief（process→product 收尾）

owner 授权"按推荐方式处理 + 难度分层派 agent + 并行不互扰 + 冲突最高价值优先 + 结果不乐观再调整重测"。
**目标**：关闭 audit 3 caveat（HIGH #1 Phase B paired CI / HIGH #2 baseline 措辞 / MEDIUM #3 3-layer
沉积）+ 产出首条 confirmatory GO 的业主签注包。

**P1(a) Phase B paired HAC CI 补算 — DONE（orchestrator 直接做）**：
- Agent A `phaseb-ci`（sonnet）idle-without-result（handoff 反复记录的 OMC idle 模式）；按 memory
  `aionis-agent-dispatch-verification`（勿信 agent，从 repo 状态恢复）→ opus 直接重算 < 5s。
- 数字：mean −0.0008003561696833403（**bit-identical #28**）/ se_hac 0.00499 / ci_half 0.00977 /
  **CI [−0.01057, +0.00897]** / t_hac −0.1605 / p_hac 0.872（与 dm_p_mbb=0.870 同尾）/ n=125 / maxlag=4。
  CI 跨零，与全家族 null 一致。
- 产物：`runs/phase_b_differential_ci_recompute.json` + `reports/audits/2026-08-05-phase-b-paired-ci-recompute.md`。
- ledger 行 #28 **未改**（append-only）；`phase_b_run.py` **未跑**（用 #28 save_run 的 `ic_state`/`ic_base` parquet + `rank_ic_summary`）。

**P1(c) Track C 3-layer conditional-IC 沉积 — DONE（Agent B 交付 + opus 核验）**：
- Agent B `trackc-3layer`（sonnet）交付 `runs/track_c_3layer_conditional_ic.json`（opus 核验自洽）。
- 重建 3-layer composite（macro+global+meso-US-SIC，valid_n=2592 日）+ joint-fold IC 三臂 HAC 回归：
  **combined β=−0.0148 (p=0.21)** / us β=−0.0287 (p=0.13) / cn β=+0.004 (p=0.80)。全 null。
- **与 handoff § culmination 数字的差异**（诚实分级）：culmination 的 β_US=−0.001/β_CN=+0.015 用的是
  Track-B-fitter **单区** IC；本 artifact 用 **joint-fold per-region** IC（`track_c_joint_ic_series.parquet`
  的 us/cn/combined 列）。不同 series，两份均 exploratory sensitivity。
- combined 3-layer β=−0.0148 ≈ joint 2-layer cond_beta=−0.015（meso 加入影响微小，方向同）。
- 产物：json + `reports/audits/2026-08-05-track-c-3layer-artifact.md`。composite **未覆盖** cache（仍 2-layer）。

**P1(b) 措辞校准**：
- `docs/RESULTS.md` §2 行 B：`**not recorded**` → `[−0.01057, +0.00897]（2026-08-05 补算）` + §2 段落补 audit 链接。
- `docs/methods-and-results-draft.md` §4 行 #1（Phase B CI）+ 行 #9（3-layer）补实际数字 + 诚实分级脚注。
- **Baseline FF5/RANK 校准（audit HIGH #2）**：2026-08-03 batch 8 的"Both baselines now have REAL
  CV-proxy results"措辞应理解为 results 在 `docs/baseline-ladder-{ff5,rank}.md` + runner 输出，
  **非 ledger**（exploratory-by-design，同 Track C joint 模式）；ledger 只含 `config_committed` 行
  （#43 FF5 / #45 RANK）。RESULTS.md 正确未引用 baseline 数字（不入 ledger = 不进 RESULTS headline）。

**P0 — Track C confirmatory GO 业主签注包 — DELIVERED**：
- `reports/design/2026-08-05-track-c-confirmatory-go-brief.md`：6 决策（D1 估计量定义 / D2 区域-月
  group / D3 区域内 IC 等权 / D4 feature_cols 41 列不对称 / D5 meso US-only + 修 #48 / D6 GO+新 ledger
  行）+ 推荐一揽子（业主可回复"全部推荐"即开闸）。
- **核心张力**（brief D1）：amendment #47（A 股 cninfo→exploratory）与 #46 frozen"联合折叠"在
  confirmatory feature_cols 上有张力；推荐 D1=A（保留联合 machinery，feature 收窄为 US 23 / CN 12 +
  宏观 6 + regime 3 = 41 列不对称，LightGBM 默认处理 CN 行的 US-fundamental missing）。
- 签注后流程：起草修 #48 + confirmatory config → `config_committed`（业主动作）→ 首次 confirmatory
  OOS 跑 → J-T 门（已实现 `sesoi_gate.py`）→ draft v0.1 → v1.0 含首条 confirmatory。

**边界**：本轮纯 docs/audit/state + gitignored json；**0 ledger / frozen surface / prereg / ADR 改动**；
未跑 research/forward/strategy（Phase B 用现有 parquet；3-layer 用现有 IC series + composite 重建）；
未观察 confirmatory rank-IC / E3。A/B agent 只写 gitignored + final message（避 writer race：
`git clean -fd` 清 untracked 不清 gitignored，memory 事件证实）。

**独立性局限（披露）**：A idle 由 orchestrator 直接重算替代（非独立 subagent pass）；B 单一交付 +
opus 核验（非独立 verifier lane）。proxy 恢复后可补独立验证（同 Lane C self-audit 披露模式）。

**P0 跟进（owner D1=A 签注后，2026-08-05 续）**：起草 `scripts/track_c_amend2.py`（amendment #48，
  复用 commit_config/amend1 机制，累积 #46+#47+#48）+ `reports/design/2026-08-05-track-c-amend2-meso-us-only.md`。
  dry-run sig `e14b9d445411e74cc3418af3bde1148163725875b01ab75175bdde002225e738`（自洽 build==dryrun）；
  ruff clean；ledger 仍 47 行（未 append）。amendment 内容：meso 收窄 US-only SIC + confirmatory
  feature_cols 41（US 23 + CN 12 + macro 6）+ Q1 区域-月 group / D3 区域内 IC 等权 / D5 meso US-only
  冻结 + baostock G3 adjustflag=3 raw。**✅ ledger #48 已入账**（sig `e14b9d44...`，owner `--commit` 授权 2026-08-05；sha256 自洽已验；
  ledger 47→48 行）。**待第二个业主 GO**（d6_go：授权首次 confirmatory OOS 跑）。

**Extension A 进展（confirmatory 前置 machinery，`/goal` 推进）**：
- **A1 DONE（commit `c98f4c8`）**：`build_joint_panel` 支持 asymmetric region-specific feature_cols
  （`us_feature_cols`/`cn_feature_cols` keyword-only，向后兼容 shared）；2 反退化测试（union+NaN /
  drops non-listed）；11/11 track_c_joint 测试绿；ruff clean。**自验（opus 直接），非独立 verifier lane**
  （proxy [1210] subagent 不稳）。
- **runner 更新（commit `b178a67`）**：`track_c_joint_run.py` 加 `TRACK_C_JOINT_MODE` env toggle
  （shared 默认 / asymmetric35）；mode-tagged 产物不覆盖 shared。
- **数据齐备性（Agent `feat-readiness` 调研）**：US 23 + CN 12 = **100% on disk**（track_b_panel 1.17M
  行含 13 fund+10 price；cn_price_panel 141K 行含 10 price+2 extras）；macro_headline 6 = **0% on disk**
  需 A2 fetch（复用 `macro_dff.py` 模式）。报告 `reports/design/2026-08-05-confirmatory-41-feature-readiness.md`。
- **asymmetric35 exploratory DONE**（验证 A1 真实数据 + US fund signal）：25 特征联合折叠（68 folds /
  71 IC 月），**combined IC −0.0121 (CI [−0.035, +0.011], p=0.31) null**；US IC −0.0019 (n=65) / CN IC
  −0.0200 (n=66)；conditional-IC β=−0.0057 (p=0.61, R²=0.002)。**判读**：加 US fundamentals (13) + CN
  extras 未改善 IC（vs shared10 combined −0.007；asymmetric35 −0.012 更负但均 null）；US IC 几乎零 →
  US fundamentals 无 alpha → **坐实 null-favored**（双区域月频已定价）。产物 `runs/track_c_joint_asym35_*`
  （gitignored）。**Pandas4 concat-sort deprecation warning**（runner:165，非阻塞，待 sort=False fix）。
- **A2 macro 7-gate 调研**：Agent `macro-7gate` 跑 ~30min 后 **failed [1210]** API error（proxy 参数错；非 idle-without-result）。
  **Orchestrator WebSearch 实证 verdict = GREEN**（US 4 macro = GREEN，FRED public domain + ALFRED vintage PIT-safe；
  CN 2 macro = GREEN，WebSearch 确认 `MKTGDPCNA646NWDB`[World Bank, ALFRED vintage] + `CPALTT01CNM659N`[OECD, ALFRED vintage]
  都支持 PIT vintage；license：FRED non-commercial research OK（Aionis = research，no redistribution）；OECD non-commercial OK）。
  **修正之前 YELLOW 判断**（过保守）。CN macro 2 可作 headline（confirmatory 41，与 #48 macro_headline_6 一致，不需 amend）。
  macro 6 fetch（A2）+ broadcast join（A3）= ~半天工程；**asymmetric35 坐实 null**（US fund 无 alpha）→ confirmatory 41 大概率同 null
  （macro broadcast signal 弱），但 spec-faithful climax（J-T 门）需 41。**业主授权 A2/A3 完整 41 路径**。

**下一步（推进中）**：① ✅ asymmetric35 DONE（combined IC −0.0121 null，坐实 null-favored）；② ✅ A2 verdict
= YELLOW（orchestrator 判断；US 4 GREEN + CN 2 snapshot+exploratory）；③ **A2/A3 完整 41 路径 — 前置 machinery 全部就绪**：A2a DONE（cap fix 验证 `edc1add`，US macro 4 valid：
  term/credit 107/128，vix/dff 106/128）；**A2b DONE**（commit `9a13518`）：CN CPI（CPALTT01CNM659N）122/128 valid +
  CN GDP（MKTGDPCNA646NWDB annual）**0/128 NaN**（releases ~10 < Z_MIN=12，数据限制诚实披露）；**A3 DONE**：
  `MACRO_HEADLINE_6` + `join_macro_to_joint_panel`（per-region by-date map）；**runner asymmetric41 DONE**（第三模式
  `TRACK_C_JOINT_MODE=asymmetric41`）。**asymmetric41 exploratory 跑中**（验证 41 特征 machinery 真实数据；
  confirmatory 41 effective macro = US 4 + CN CPI = 5，GDP NaN，LightGBM native missing）。
  ④ **业主 d6_go**（第二个 GO）→ confirmatory OOS（41 + J-T 门）→ draft v1.0 climax。**climax 前置全部就绪，待业主 GO。**

## 2026-08-04 方法学+结果 draft v0.1（可发表单元；process→product）

owner 4× 重发 standing auth → 执行推荐 ②（方法学写定稿）。产出 `docs/methods-and-results-draft.md` v0.1（PROPOSED，业主审阅中文稿）：
- **METHODS 段（§1-3）= 贡献**：反泄漏纪律作为研究对象（config-before-result / PIT 全栈 / purged+chronological 验证 / H6 确定性 / J-T 等价门 / 两尾 null-favored 预注册 / multiplicity 预算 1 条件化）——全部 code/ledger-asserted，非叙述。Track C 联合折叠作为方法学新点（§3）。
- **RESULTS 段（§4）= 12 行 null 证据表**，诚实分级（CV-proxy vs chronological；exploratory vs confirmatory）。全部 null；0 条 confirmatory。
- **§5 占位** = Track C confirmatory GO（首条 confirmatory）。
- **§6 局限** 诚实（CV-proxy≠chronological；exploratory≠confirmatory；Track B 等价欠功率；幸存者；币种）。
- 数字源自 ledger/artifact；**独立核对**派 `evidence-audit`（sonnet，后台，read-only）→ `reports/audits/2026-08-04-evidence-integrity-audit.md`（运行中）。
- **治 "治理>产出" 失调**：把累积 process 转 product。未触冻结面/ledger；confirmatory 段 owner-gated。

## 2026-08-04 Track C 联合 US-CN 折叠估计量（confirmatory machinery；exploratory 走通中）

owner 授权"按推荐方式处理 + 难度分层派 agent + 并行不互扰 + 冲突最高价值优先 + 结果不乐观再调整重测"。**边界**：null-favored，"不乐观"= 工程/测试 bug 迭代修复，**非** rerun-to-significance（若现 rescue 诱惑则交 owner）。

**双车道并行（文件隔离）**：
- **Lane A（sonnet `general-purpose`，后台）→ [1210] 死，orchestrator(opus) 直接接手完成**：`reports/design/2026-08-04-shenwan-meso-7gate.md`。**裁定：CN 申万 meso via baostock = G3 结构性 fail（无 as-of/vintage，SWFC 回填，同 baostock-基本面先例）→ 快照冻结 + exploratory-only，不进 confirmatory headline**。**关键后果：confirmatory meso = US-only（SIC），= 当前实现状态，正式化为 spec-faithful config；不需 CN 申万 fetch**。本会话早先「3-layer US-only-meso 双区 conditional-IC null」即 spec-faithful exploratory 结果。正式化需 owner 在新 ledger 行修订 §1.1（meso=US-only for confirmatory；CN 申万 exploratory）。
- **Lane B（opus = 我，会话内）**：联合折叠估计量设计 + 实现（slop 高危件，本会话 agent 翻车 3 次同类）。

**Lane B 已交付 + 验证（未 commit）**：
- `reports/design/2026-08-04-track-c-joint-fold-spec.md`（设计 spec；D1 区域-月 group / D2 区域内 IC 等权联合 / D3 per-region 时序断言 / D4 regime as-of 月末 / D5 共享 10 price 特征；7 项 owner-decision 旗标 Q1-Q5）。
- `src/aionis/eval/track_c_joint.py`：`fit_track_c_joint` + `build_joint_panel` + `construct_region_month_groups`（D1）+ per-region 时序断言。核心洞察：**month-end 采样 + 日历月折边界 = per-region 21-session embargo 自动满足**（相邻月末 ≈ 21 sessions/区），无需逐区数交易日 → `cv.py`/`purgedcv` 0 改动。
- `tests/test_track_c_joint.py`：9 反退化测试（区域-月 group、build_joint_panel 双区+窗口、per-region 时序断言抓违反、月末逐区采样幂等、单区拒绝、**e2e H6 bit-identical 双跑**、combined_ic=区域 IC 等权）。**9/9 绿**。
- `scripts/track_c_joint_run.py`：exploratory runner（PHASE_C_NO_LEDGER；产出 `runs/track_c_joint_*` gitignored）。
- **验证**：`tests/test_track_c_joint.py` 9/9 ✓；全套 hermetic pytest **exit 0**（无回归）；`ruff check` 全清。

**Lane B 真实数据证据（DONE；exploratory，NO ledger）**：`scripts/track_c_joint_run.py` 在真实 US(566 tickers) + CN(929) 联合月末面板跑通（68 folds / 71 IC 月，oos_scores 94,438 行双区，score std 0.508 非退化）。**combined rank-IC −0.0070，CI(−0.030,+0.016) 跨零，p_hac=0.55 → null**；US IC −0.002 / CN IC −0.014（双区均 null）；**conditional-IC β=−0.015，p=0.20（无 regime 交互），R²=0.018**。= 又一条 null（符合 null-favored；与 Track B null + 早先 CN 单区 conditional-IC null 一致）。产物 `runs/track_c_joint_{summary.json,ic_series.parquet,oos_scores.parquet}`（gitignored）。**非 confirmatory 判读**（10 共享 price 特征 + region-month group D1 默认，#46 group 未冻结）。

**关键设计决策（confirmatory 前需 owner 签注，spec §7 Q1-Q5）**：
- Q1 lambdarank group = **区域-月**（D1，币种干净；#46 未冻结 group 构造）。
- Q2 联合 IC = 区域内 IC 等权（D2）。
- Q3 confirmatory feature_cols = 全 #46 54 列（exploratory 用共享 10 price）。
- Q4 meso（依赖 Lane A 裁定）。
- Q5 confirmatory 跑 = owner GO + 新 ledger 行。

**Lane C 独立 review 结果（agent 车道失败 → 确定性自审 + 披露）**：`jointfold-review`（sonnet）2 次 idle-without-verdict（[1210] proxy 日，agent 车道不稳：Lane A 死、Lane C idle）。按 WORKFLOW §17（2 次相同失败 → stop）+ §8（从 repo 状态恢复，勿信 worker prose），停重试，改**确定性自审**（opus 自审 + grep 核验关键接线 + 测试/真实跑证据），**独立性局限明示**：
- **I1 per-region 时序**：`_assert_per_region_chronological`（track_c_joint.py:359）在折循环内、`splits.append`（:360）前调用，无 try/except 包裹 → 不可跳过 ✓（grep 核验）。
- **I2 train-only binner**：`fit_monthly_bins(train_returns=...)`（:382-383）仅喂 train ✓。
- **I5 region-month group**：`(y*12+m)*2+code`（:111），us/cn 分离 ✓。
- **测试实质性**：e2e fixture 70 月×50 ticker+signal 0.3+`check_exact=True`（H6 严格）→ 非化妆品测试 ✓。
- **证据**：9/9 反退化测试 + 全套 pytest exit 0 + 真实跑非退化（score std 0.508）双区正确 shape。
- **Verdict**：machinery 确定性验证通过（self-audit + tests + real run）。**独立性局限**：非真正独立 pass（agent 车道 [1210] 失败）；proxy 恢复后可补独立 review。2 个 LOW note（e2e 未 assert IC>0；per-region assert 对单边缺席区域 skip——真实数据两区恒在，不影响）。

**边界**：本轮纯新建文件 + state；0 冻结面/ledger/prereg/ADR 改动；未观察 confirmatory rank-IC 结论；未触 E3。

## 2026-08-04 Track C conditional-IC（3-layer regime，null）— 会话 culmination

meso 3rd 层完成（`33b5cfb`，US SIC=EDGAR 公共域 `phase_d_sic_map.parquet` 588 tickers；CN 申万 baostock `ENABLE_CN_FETCH=1` 门控默认 off → meso 现 US-only，sha256 `e9f30d94`）。composite builder 升级 3-layer（`f7c5789`，sha256 `0cb7409e`，3021 日/valid 2592）。

**双区域 conditional rank-IC（IC_t ~ regime_t, HAC）**：
| regime 组成 | US β (p) | CN β (p) |
|---|---|---|
| 2-layer (macro+global) | -0.008 (0.48) | **+0.034 (0.07 边际)** |
| 3-layer (+meso US-only) | -0.001 (0.95) | +0.015 (0.36) |

**关键发现（方法论）**：2-layer 的 CN 边际交互（β=0.034, p=0.07）**被 meso 稀释到 null**（β=0.015, p=0.36）。**conditional-IC 对 regime 组成敏感**；spec-faithful 3-layer regime 下两区域 conditional-IC **均 null**（null-favored-consistent）。此前"CN 非对称 regime 交互"是 2-layer artifact，不稳健。

**待办（confirmatory，owner-gated）**：① 全 US+CN meso（CN 申万 fetch ~30min baostock）；② 联合 US-CN 折叠（per-region 日历 + 时序）；③ confirmatory 跑（冻结 #46/#47 + **新 ledger 行 = owner 动作**）+ J-T SESOI 门。当前 conditional-IC 用 Track B fitter on 单区域 + 独立 IC 系列回归（非联合折叠 confirmatory 估计量）。

**本会话总账（17 commits，main，未 push）**：S0 数据（CSI300 universe `425f5535` + A 股价格 `a4614876`）→ mount② 净成本（5bps net Sharpe ~0.43 年化）→ 首个 CN rank-IC(null, mean 0.0098 p=0.46) → 3 regime 层（macro `4bfd1949`/global DY `d189f53c`/meso `e9f30d94`）+ composite（3-layer `0cb7409e`）→ conditional-IC（3-layer null）。全套 hermetic pytest 绿，ruff 干净（预存 `track_c_commit.py:180` E501 仍待 owner）。

## 2026-08-04 regime composite（完成；2-layer exploratory）

owner `/goal`×5 推进 Track C regime_state。3 层中 **macro + global + composite** 完成，meso deferred。

- **macro 层**（`abab13e`，agent clean——本会话首个无需修复的）：vix+credit_spread(BAA-AAA)+term_spread(DGS10-DGS1)+dff_surprise 等权 past-only z-score。**EPU 4-line**：无 permissive 中国 EPU 源（license+PIT+no-revision 门 fail）；frozen #46 本标 EPU"(exploratory)"，排除=保守合规；**confirmatory 需 config 修订（新 ledger 行）**。sha256 `4bfd1949`。
- **global DY 层**（`9093100`，agent + 我核验）：US-CN EW 市场收益 → Diebold-Yilmaz 广义 FEVD（**statsmodels VAR + 标准公式**，未 vendor spillover-lab 因 PySide6 重）→ rolling-250 总 spillover。**GFEVD 公式逐行核验正确**（GIR=(ΦΣ)[i,j]/√Σ_jj；θ 行和 1；total=(θ01+θ10)/2；sanity：independent→~1%、correlated→~35%）。2 caveat：sha256 标签是 series-hash(`d189f53c`) 非 file-hash(`eb873732`)；lag-0 fallback 触发 30%（agent 误报"罕见"，建模选择非 bug）。
- **composite**（`df57a4a`，opus）：等权 past-only z-score 两层 + **TACO expanding σ**（[t0,t] 不回溯重算，frozen #46 normalization）。regime_state n=3021/valid 2585，mean 0.018/std 0.83，sha256 `deee9cf1`。
- **meso deferred**：申万/SIC 行业动量（数据源 7-gate 最难）→ composite 暂 2-layer（exploratory）。
- **Agent 质量教训强化**：macro(clean) + DY(公式正确，因 spec 含精确公式 + sanity 测试) → **精确 spec + 反退化/边界测试 = agent 能做对硬量化方法**（对比 net_cost/CSI300/cn_panel 盲派都出错）。

**下一步（待做，opus 设计重——conditional rank-IC 是 Track C 真正的 confirmatory 估计量）**：
1. **score × regime_state 交互 → conditional rank-IC**（IC 系列随 regime 变化？）。需 conditional-IC 框架设计（参考 `reports/design/2026-08-03-conditional-rank-ic-multiplicity.md`）——这是设计重活，slop 风险高，宜先定方案。
2. **meso 3rd 层**（申万/SIC，for full 3-layer composite）。
3. **联合 US-CN 折叠 + confirmatory 跑**（冻结 #46/#47 + 新 ledger 行）。

## 2026-08-04 Track C CN rank-IC 首探（完成；exploratory）

owner `/goal`×4 推进 Task#6。A 股 price-only 面板 → 首个 CN rank-IC。

- **CN 价格面板**（`data/cache/cn_price_panel.parquet`，gitignored）：141,208 行 / 929 tickers / 152 月末 (2014-01..2026-08) / 12 特征 (10 Track B price + limit_up_down_distance + suspension_flag) + forward_return_h。leakage self-check PASSED（特征只用 close≤t，标签用 close[t+21]）。
- **agent 质量第 3 例**：`cn-price-panel` agent 交付的 `build_cn_price_panel.py` 有 3 bug（① MultiIndex stack 后误赋 4 列名实为 11→Length mismatch；② leakage self-check 取非月末 raw 日期→越界；③ stack 依赖 index.name="date" 不健壮）。agent 的 15 测试又"绿"但空洞（测了 `compute_price_features` 被复用函数，没测 `_build_features` 包装）。opus 修 3 bug + 补 `_build_features` 回归测试（set 对比 + 排除 melt 残余）。
- **首个 CN rank-IC**（`scripts/track_c_a_run.py`，Track B fitter on CN，92 折 2019-01..2026-06）：**mean_ic 0.009836，ci_95 (-0.0165, 0.0362) 跨零，p_hac 0.4639 → NULL**；DM vs EW stat -2.19 / p=0.031（边际；n_trials=30 haircut 会洗掉）；IC std 0.1289。**与美股 Track B null 一致，符合 null-favored 预期**。corr(momentum_21d, fwd_ret)=-0.015（A 股短期反转 hint）。
- **诚实结论**：A 股 price-only rank-IC null = 可发表结果，**非"不佳"——不调整重测**（rerun-to-significance 禁）。下一步是 Track C 真正的 confirmatory 跑（regime 交互 + 联合折叠 + 冻结 #46/#47），不是"rescue"这个 exploratory null。
- **边界**：exploratory（Track B fitter on CN），**非 Track C confirmatory 估计量**，不写 ledger。IC series + OOS scores 存 `runs/track_c_cn_*`（gitignored）。
- **commits**：cherry-pick `78f7d5af`（agent 原始，3 文件）+ 本批 fix commit（3 bug 修复 + 回归测试 + runner）。

## 2026-08-04 OSS-survey + 并行派发批次（完成）

owner 授权"按推荐的数据与方式处理 + 难度分层派 agent + 并行不互扰 + 冲突高价值优先 + 结果不佳再调整重测"。

**已完成：**
- **修订 #47 提交**（`6bd360f`，owner 本会话明示授权）：A 股 cninfo 基本面 → exploratory-only（G1 处置），claim 收窄为 US-rank-IC（确认性）+ A 股 exploratory 条件化。ledger #47 sig `252cf7df` sha256 自洽已验；#46 冻结不变（append-only）。含 docs/track-c-preregistration.md §0+§3、ashare-fundamentals-source.md §3、scripts/track_c_amend1.py（可复现）、state 沉积。
- **清除 GPL orphan** `src/aionis/eval/finsaber_mount.py`（import backtrader GPLv3；真正的净成本层是 `eval/execution_costs.py`，已实现）。
- **baostock G3=raw** 已是 `ingest/ashare_price.py` 默认（adjustflag="3"）；intake 文档（`ab43454`）已覆盖。视作冻结默认。
- **OSS 轮子调研**（`420fba1`，今上午 + 同日勘误）+ 本轮补验：qlib=library-import CN 采集器（MIT,PIT-DB 实）；akshare=MIT 但 SSRN 论文实证其 PIT 不安全（重述值）→ 坐实"A 股 filed-date 基本面无 permissive 轮子"=结构性数据 gap，非手搓失败。

**完成（2 agent 回报 + 集成 + 修复；commits `5b561e4`/`8bbe6a6` cherry-pick + 本批 fix）：**
- **`csi300-intake`（Task#3，DONE clean）**：选 `index-constitution`（PyPI 实证 MIT + `py3-none-any` wheel=3.13✓ + 0.6.2/2026-07 + 内嵌 CSIndex 历史公告=零运行时 HTTP + opt-in/opt-out=PIT+survivorship-safe）。7-gate 全 PASS。`ingest/csi300_constituents.py`（lazy import 非 core dep + `enable_fetch=False` 默认 + snapshot+sha256 + `constituents_on(t)`）+ intake doc + 14 hermetic 测试（无 stub）。潜在风险：适配器调 `ic.history("csi300")` 而 PyPI 示例是 `ic.constituents_at(...)`——API 名待真实拉取时核实（owner-gated+fail-closed，不阻塞）。
- **`mount2-netcost`（Task#2，agent 交付 defective → orchestrator opus 重写 3 文件修复）**：agent 的 net_cost.py 有 **3 blocker**（turnover 退化：pre_trade 两分支都=0 + 注释撒谎；test 有空 `pass` stub；runner 整个计算被注释 `sys.exit(1)`）；且 11 测试是**欺骗性绿**（3-ticker fixture 致 long_short_returns 跳过→NaN→`if isfinite` 跳过 assert + 5 测的是 execution_costs 内核）。**重写后**：turnover 追踪 prev_target（union 对齐、逐期成本、no-drift 简化已诚实标注）；去 session_opens（turnover-bps 模型不需 open 价）；runner 加载真实 `oos_state.parquet`（`long_short_returns` 自动月末子采样）→ **本轮出真实数字**；12 测试含**反退化测试**（稳定分数→低 turnover，洗牌→高 turnover，直接抓 always-2.0）。
- **集成**：cherry-pick 两 commit（worktree 基是 `30ae69f` 非 `6bd360f`——worktree 创建时序问题；但两 commit 自身 diff 各 3 新文件纯新增→cherry-pick 安全，#47 未被回退，已验）。全套 hermetic pytest **exit 0**；ruff 干净；零 stub/TODO/pass。
- **⚠️ 运维教训（fold 进 orchestration-protocol §8）**：① worktree 基可能滞后——merge/前**必查 merge-base + commit 自身 diff**，勿信 `branch..HEAD` 累积 diff；② agent"全绿"必须**代码级核验**——A 的测试空洞绿（小 fixture→NaN→跳过 assert）肉眼不可见，靠反退化测试 + 真实数据跑才暴露；③"reuse-first"≠"import 了就算复用"——A import 了 execution_costs 却喂退化输入。

**mount② 真实结果（Track B treatment panel `ef321e9…`，bps=5，125 月 2016-2026）**：gross_sharpe 0.1487（月，年化≈0.51）→ **net_sharpe 0.1250**（年化≈0.43，成本吃 ~16%）；**avg_turnover 1.1444**（真实换手，非退化 2.0）；total_cost 715 bps 累计（≈5.7 bps/月，=5×1.14×1e-4 自洽）。注：此 panel 是 mtime 最新 run（未必 #41）；策略在 5bps 滑点下保住大部分 Sharpe。

**边界：** 本批仅 #47 commit（owner 授权）+ cherry-pick 2 agent commit + mount② fix；**未观察 OOS rank-IC**（net-cost 是 L-S 收益视角，非 rank-IC 估计量）；未触 B/C/D/E1/Track-B 冻结面；net_cost 是探索性工具（类比 ff5_residual，不接管线、不写 ledger）。`runs/track_b_net_cost.parquet` gitignored。

## 2026-08-04 `/loop` 批次 — 未提交在途工作批判性审计（GPL 清除 + site 恢复；未 commit）

owner `/loop` 授权"推进推荐项 + 批判性思维 + reuse-first + 模型分层省 token"。进入会话发现 main 上有一批**未提交的在途工作**（非本会话创建），独立审计发现 **2 个缺陷**，已采取明确正确的恢复/安全动作；judgment 项交 owner。

**缺陷 1（CRITICAL，已清除）— GPL 污染：** 批次把 `finsaber>=2.0.1` 加进 core deps + 新增 `src/aionis/eval/finsaber_mount.py`（直接 `import backtrader as bt` + 子类化 `bt.Strategy`）。核验（definitive）：`finsaber`=Apache-2.0（本身合规），但其 `Requires-Dist` **硬依赖** `backtrader>=1.9.78`=`GPLv3+`，CLAUDE.md 明令 EXCLUDE。→ 已从 pyproject 移除 finsaber；`uv lock --offline` 清除 backtrader+finsaber+colorlog；pyproject/lock 回到 committed（GPL-free，diff 空）。`finsaber_mount.py`（untracked、孤立、无任何 import 引用）排除不提交。见记忆 `aionis-finsaber-backtrader-gpl`。

**缺陷 2（回归，已恢复）— site 空壳化：** 批次的 `site/index.html` 把 committed 的**真实内联数据**（`const icData={...}` + 风险表 + FF5 表）替换成**占位符**（`const icData=null` + "待 ...json"；因 `build_static_site.py` 在 2 个 JSON 被删后重建产空壳，且有个未闭合 `<p>`）。→ `git checkout -- site/` 恢复 committed 已部署的良好站点（真实数据，`grep const icData={` 计数=1 确认）。

**测试：** 全套 hermetic pytest exit 0（仅 pre-existing forward-score/numpy warnings）；`ruff` 未本轮重跑（无 src 改动待验——pyproject/lock 回到 committed，site 回到 committed，均无新代码）。

**待 owner 裁断（未擅自提交——非本会话创建 + consequential）：**
1. **修订 #47（A 股 cninfo→exploratory-only）**：ledger 行已 append（sig `252cf7df`，phase=track_c），docs/ashare 报告同步；`track_c_amend1.py` docstring 称"owner authorized (B) 2026-08-03"但 tracked state（本文件/current.md）**未印证**。属 claim 收窄 scope change（保守、append-only、结构合规）。→ owner 确认授权后可提交（ledger+docs+track_c_amend1.py+ashare 报告）。
2. **oos_scores 管线**（`track_b_baseline.py` oos_scores 字段 + `track_b_a_run.py` 持久化 + `ranking_contract.py` 单行月 scalar→Series bugfix）：license-clean、verified-green、非 scope change；但与 mount② 消费耦合。→ 建议与 mount② 合为一个完整切片提交。
3. **mount② 净成本回测（reuse-first 重写）**：**禁用** finsaber/backtrader（GPL）；改用 **pyfolio-reloaded+empyrical（已在 lock，MIT/Apache）+ ~50 行确定性成本层**（next-open 成交 / bps slippage / turnover / 流动性上限）。待 owner 定成本参数。

**下一步（loop 续跑优先级，无 owner 回复时）：** P0 = 上述 3 项 owner 裁断；P1 = Track C S0 数据构造脚手架调研（冻结后允许，不写 ledger/不观察 rank-IC）：qlib 双区域 mount 接线点④ + cninfo MIT fetch（`rollysys/use_cninfo`）+ A 股价格 PIT（baostock 价格 MIT ✅，基本面 G3 reject）。子代理 dispatch 因 `[1210]` proxy 今日不稳 → orchestrator 直接 opus 写优先（handoff 既定策略）。

**边界：** 本批仅恢复/安全动作（site revert + GPL 清除）+ state/memory；**未 commit 任何 frozen surface / data**；ledger #47 行保持 in-tree 未提交原状；未跑 confirmatory/strategy/forward；未观察 E3；网络仅 PyPI 离线（uv lock）。

**续（loop 迭代 2 — owner 未回复 #47 授权 → 推进 P1 安全项）：**
- 提交 `5e2ce6d`：clean infra（`ranking_contract` 单行月 scalar→pooled-edges bugfix + Track B `oos_scores` 管线）；verified-green + ruff clean；非 scope change，**不需 owner 决策**。清树债。
- 提交 `ab43454`：2 份 S0 intake 文档（baostock A 股价格 7-gate + CN 宏观双层级 7-gate），**2 并行 sonnet `general-purpose` agent** 产出（绕过 `[1210]`，file-isolated，未触冻结面/未拉真实数据/未观察 rank-IC）。关键裁决：baostock 价格 **G3 CONDITIONAL**（复权因子 adjustflag 可追溯回改 → 需冻结策略：raw+本地因子快照 或 前复权全序列快照）；CN 宏观 **headline(ALFRED/OECD vintage) PASS 全 7 门** / **exploratory(NBS via mbk-dev/nbsc) G2+G3 FAIL → snapshot+sha256+exploratory-only**（EPU 先例）。
- **仍 pending owner**：① 修订 #47（A 股 cninfo→exploratory）授权确认；② mount② 净成本成本参数（slippage bps 等）；③ NBS G1 license 验证 + baostock G3 复权冻结策略裁决。
- **下一 loop 优先级（无 owner 回复时）**：qlib 双区域 mount 接线点④ 调研（S0 基础设施，POC 标注 ~3h 接线）或 cninfo MIT fetch（`rollysys/use_cninfo`）路径设计（exploratory 基本面）。子代理 `[1210]` 已验证 `general-purpose`+sonnet 可靠绕过 → 可继续 ≤2 并行 file-isolated 派发。

**续（loop 迭代 3 — owner 仍未回复决策；推进 P1 具体研究基础设施）：**
- 提交 `178d1fd`：**baostock A 股价格 ingest 适配器**（`src/aionis/ingest/ashare_price.py` + 5 hermetic 测试）。镜像 `market.py` US 侧模式；lazy import（baostock 非 core dep，`uv add baostock` 激活）；G3 默认 `adjustflag="3"`（raw，G3 方案 A，冻结策略延后到 config）；停牌→NaN（G6）；≥2s pause（G7）。**决策零依赖**（baostock 是冻结 prereg 批准源；intake 文档已提交；G3 策略延后 config）。5/5 测试通过 + ruff clean。未拉真实数据/未触冻结面/未写 ledger。
- **本轮累计 3 提交**（`5e2ce6d` infra + `ab43454` intake 文档 + `178d1fd` 适配器）—— 全部具体、安全、reuse-first、verified。
- **5 项 pending owner 决策不变**（修订 #47 授权 / mount② 成本参数 / NBS G1 license / baostock G3 冻结策略选方案 / 下一 S0 切片优先级）。**最高价值路径（真实 S0 数据、Track C rank-IC）仍被门控。**
- **下一 loop（无回复）候选**：A 股交易日历对齐（pandas-market-calendars XSHG/XSHE，配 baostock 适配器）或 CSI300 PIT 成分 intake（`index-constitution` MIT）。

**续（loop 迭代 4 — 改做独立质量门，不再造脚手架）：**
- 批判判断：连续 3 轮"找安全切片建造"边际价值递减 + 建错方向风险升（owner 未确认 baostock vs qlib+AKShare；未确认 G3）。改为关闭真正的质量缺口——本会话 3 commit 此前全是**自我批准**（违反 OMC 分车道）。
- **独立 opus `general-purpose` reviewer 审 `30ae69f..HEAD`**：**APPROVE，无 blocking**。验证：anti-leakage/PIT（停牌 NaN ✓ / adjustflag G3 延后 ✓ / 单 login finally-logout ✓ / oos_scores 仅 test-fold ✓）、license 完整性（uv.lock 无 backtrader/finsaber ✓ / baostock lazy-import 非硬依赖 ✓）、正确性、测试充分性、代码质量。2 条 advisory（非阻塞，未改）。
- **全局 hermetic pytest exit 0**（全绿，确认 3 commit 无回归）。
- **结论**：3 commit 现已"独立审查 + 全局验证"双门通过，不再仅自证。
- **5 项 pending owner 决策仍不变**；最高价值路径仍门控。**建议**：若 owner 近期无法回复，`CronDelete 2344a544` 暂停 loop（避免重复读状态开销 = token 浪费，owner 自己的优先级）。若回复，最阻塞 = 修订 #47 授权确认。
- **下一 loop（无回复）候选**：交易日历对齐 或 CSI300 成分 intake（仍属安全外围，边际价值递减——故本轮选择改做质量门而非继续造）。

## 2026-08-03 `/goal` 批次 — Option A′ 推进（docs/design only，未 commit）

owner `/goal` 授权推进 Option A′（多 agent 按优先级 + 模型分层省 token + reuse-first 禁造轮子）。**[1210] 现实**：opus/sonnet 子代理今天执行不稳；本批分层 = ① orchestrator 直接 opus 设计 + ② sonnet 后台 agent + ③ haiku 后台 agent。

**产出（全部 PROPOSED/docs，未触冻结面/ledger/E3）：**
- `reports/design/2026-08-03-conditional-rank-ic-multiplicity.md` — **gate 7 解决**：conditioning = 单个预指定交互项（预算 1，非 K），批判者 #4 "完全炸掉 n_trials" → PARTIAL 解决；复用 `purgedcv`/`arch`/`YannickKae`；Deflated-RankICIR（FARS 2026，DSR 适配因子级 RankIC）待 license。
- `reports/design/2026-08-03-track-c-prereg-skeleton.md` — **Track C（A 股 + 条件化 rank-IC）预注册骨架 PROPOSED v0.1**；§3 features / §5 双区域折设计 / §1 regime PIT 定义 = TBD（待 T1 + owner 冻结）；§4/§6/§7/§8/§9 复用 Track B + ADR-010。

**后台 agent（运行中，待回报）：**
- `ashare-gate-research`（sonnet）— A 股 filed-date 基本面源 7-gate 调研（cninfo / Tushare-`ann_date` / akshare）。**P0 关键路径**（gate 4，解 baostock G3 结构性失败）。
- `drankicir-check`（haiku）— Deflated-RankICIR 代码/license 核查（解 gate 7 待查）。

**未解 / 下一步：** T1 回报 → 填 Track C §3 + 定 A 股源（headline 可行 vs exploratory-only）；drankicir 回报 → 定 gate 7 主轮子；A 股**价格** PIT（§3 ①，survivorship 退市/停牌→NaN/复权）+ 中国宏观 vintage（§3 ②，NBS G3）待后续 intake 调研。regime PIT 定义（TACO 范式）待 owner 冻结。

**边界：** 本批仅 docs/design + state；未 commit；未运行 confirmatory/strategy/forward 脚本；未观察 E3；网络仅 GitHub/PyPI/WebSearch（无 baostock.com 数据调用）。

**Track C v1.0 PROPOSED（2026-08-03 续）：** owner approved §12 默认 → 起草完整 `docs/track-c-preregistration.md`（PROPOSED v1.0，12KB；§12 全填：联合折叠 / 三层 PIT regime / cninfo 源 / qlib scaffold；§3 ①②③ 全调研解决）。取代 `reports/design/2026-08-03-track-c-prereg-skeleton.md`。**未冻结**——无 `config_committed` ledger 行；feature_cols 待冻结前完整枚举（US 复用 Track B 23 + A 股 price/cninfo/ALFRED/regime 字段）。**待 owner**：审 v1.0 → 授权 `config_committed` 冻结（写 ledger 行，= owner 动作）→ impl 切片（post-freeze）。agents 7/7 `[1210]` 死，全 orchestrator 直接完成。冻结面守卫 = 空（仅新增 docs/track-c-preregistration.md，未改 phase-*/track-b/ADR/ledger/config）。

**Track C FROZEN（2026-08-03 续 2，owner 二次 approved）：** owner 确认 4 个冻结子参数（regime expanding-as-of σ TACO；DY spillover window=250/H=10/generalized FEVD；三层等权 composite；A 股 FF v1.0 排除）→ 写 `scripts/track_c_commit.py`（纯 stdlib，复用 phase_b `commit_config` 机制：`sig=sha256(json.dumps(config,sort_keys=True))`，行格式 `{ts,event:"config_committed",phase,config_sig,config}`）。**dry-run → --commit**：ledger 45→46 行，phase=track_c，`config_sig=758ca4d739f09331ee4dceb726d9d0d0f7c5110303acc6dcac59919701374fad`，**sha256 自洽已验**（重算==行内 sig），**未观察任何 OOS**（config_committed 行 only）。`docs/track-c-preregistration.md` §0/§13 更新为 FROZEN。**Track C 反泄漏 anchor 就位**；冻结后允许 S0 数据构造（不写新 ledger、不观察 rank-IC）。`runs/ledger.jsonl` 现有未提交改动（+1 行，TRACKED，按惯例提交时机 owner 定）。

## 2026-08-03 qlib 双区域 POC（Option A 可行性取证，docs/state only — 未 commit）

owner 授权的可逆证据 POC，解决 Option A 辩论（独立批判者 REJECT；辩护/裁断 agent 因 `[1210]` 5 次失败缺失）。完整报告 `reports/2026-08-03-qlib-dualregion-poc.md`。
- **5 硬证据:** ①qlib 双区域特性存在（`REG_CN/US`+`LocalPITProvider`+CSI300/500 采集器[从 csindex 历史公告重建]+pit 采集器）→**推翻批判者 #2/#8/#10**; ②cp313 门（pyqlib 0.9.7 无 cp313 wheel；3.11 隔离 venv `IMPORT_OK` 0.9.7 已验绕过）; ③RobustZScoreNorm 泄漏陷阱实证确认 + 折内钉 fit 修复有效（CLEAN train z-median 0.0000 vs LEAKY −0.3453）; ④DatasetH 手术点③需 3h 接线; ⑤**baostock G3 结构性不可合规**（`query_profit/balance_data(code,year,quarter)` 期末键、无 as-of/vintage）→**验证并强化批判者 #1**。
- **Net:** Option A′ **条件-sound**，8 门实证背书（报告 §3）。A 股基本面须换 filed-date 键源（cninfo/Tushare-`ann_date`/自建）或降 exploratory-only；baostock 不可进 headline。
- **边界:** scratch `/home/re/code/aionis-qlib-poc/`（仓库外），合成数据，未 commit/未触冻结面/ledger；网络仅 GitHub+PyPI；无 baostock.com 数据调用、无 research/forward 脚本、未观察 E3。
- **未解:** baostock 返回字段 pubDate 可重建性; A 股 filed-date 源 7-gate; DatasetH 手术点③接线; `index-constitution` 7-gate。
- **loop cron `3219e84b` 已取消**（POC scope 完成，避免与暂停冲突）。
- **独立性局限:** 批判者真独立; 辩护/裁断由 orchestrator 非独立核查替代（已做偏向校正）。proxy 恢复后可补完整三方辩论。

- **2026-08-03 `/goal` batch 8 — BASELINE-FF5-001 + BASELINE-RANK-001 EXECUTED (COMMITTED `104b21e`):**
  owner authorized real-data execution ("全部approved"). Both baselines now have REAL CV-proxy results:
  - **BASELINE-FF5-001** (sig `0b0b9934…`, 18 cols: 9 frozen + 9 FF5 exposures; `beta_dff`/`beta_dff_x_lev`
    excluded by RD-13: 42 CONSTANT months 2024-08+ — rate-plateau): **mean_IC=0.0106, ci_half=0.0196,
    t_hac=1.059, n_months=125; H6=True**.
  - **BASELINE-RANK-001** (sig `22817980…`, lambdarank/rank_bins=5, month-end-sampled panel,
    analysis_start=2015-08-01): **mean rank-IC=0.015420, ci_half=0.014870, t_hac=2.0323, p_hac=0.0421,
    n_months=125; H6=True**.
  Both EXPLORATORY CV-proxy only; config_committed ledger rows appended BEFORE results (2 RES-02 + 2 RES-03 rows).
  **Fixes surfaced by real runs**: (1) RES-02 SIG_ONLY mode (exit before OOS) + analysis window
  2015-08-01 (DFF vintages begin 2015-01-01; owner decision option A) + month_ends pre-window;
  (2) features/ff5.py beta_dff NaN no longer contaminates FF5 5-factor betas (independent OLS masks);
  (3) RES-03 month-end sampling (RD-15 group=query-month ~500 rows, not ~11,300 — LightGBM 10k/group cap)
  + folds on month-end panel via two_arm._folds_from_panel + config-driven analysis_start;
  (4) RES-03 _require_owner_commit ledger gate. Full suite exit 0; ruff clean.
  **Data acquisitions**: FF5 daily snapshot frozen (`ccf509fb…`, 15833 rows) + DFF ALFRED vintages
  293,510 rows (2015→2026, sharded yearly — FRED 2000-vintage cap workaround).
  **NOT yet done**: evals/trials registry entries for both trials; RES-08/RES-10 (owner gold-set annotation).
- **2026-08-03 `/goal` batch 7 — E3 Slice 7 E2E + AUD-06 contract freeze (COMMITTED `0f94620`):**
  closed the final E3 code gap. `tests/test_forward_e2e.py` (NEW, 290 lines, 2 tests) wires the full
  hermetic chain on labeled synthetic fixtures in tmp_path: COMMIT (Slice 3d, long-scores both arms,
  sha256 seal) → **I1** gate (reveal before target_t refused, no scored rows) → REVEAL+SCORE (Slice 4b,
  both arms ic_point float) → **I2** (idempotent re-reveal appends nothing + immutable sealed-scores
  sha256, byte-mutation flips hash) → ACCUMULATE (Slice 4c, n_months=1, summary key set,
  dm_flag=degenerate) → **I9** (forward chain writes ONLY runs/forward/ + ledger.jsonl, never
  runs/results/). I3–I8 explicitly NOT duplicated (owned by existing invariant suites).
  `config/e3_live_contracts.yaml`: `max_age_sessions` 23 → **22** + `authoritative_refresh: null`
  explicit + PROPOSED → **FROZEN (D2, 2026-08-03)**; cron stays DISABLED, headline still needs owner GO.
  `tests/test_e3_forward_trigger.py`: 7× 23 → 22 + proposed-marker test renamed frozen-marker.
  **Verified: 7 forward suites 84 passed; full hermetic suite exit 0; ruff clean; real-ledger guard
  PASS; git diff --name-only = the 3 files; pre-existing Track-B WIP untouched.** Slice 7 code complete;
  only E3 headline (AUD-06 done + owner GO) and RES-08/RES-10 (owner-gated) remain.
- **2026-08-03 `/goal` batch 6 — RES-02 + RES-03 EXECUTED via 2 worktree-isolated agents (COMMITTED
  + pushed, `825658b`):** owner authorized execution ("授权你继续执行"). **2 sonnet agents in isolated
  git worktrees** (the correct "各自推进/不影响各自进程" mechanism — no writer race, no Track-B WIP
  conflict), each delivered INLINE this time. Merged into main; both exploratory baselines PREPARED but
  NOT registered (runners refuse to run until the owner's `config_committed` ledger row exists):
  - **RES-02 (BASELINE-FF5-001)**: ff5.py ingest (bulk-ZIP, sha256 snapshot, ≥2s politeness) + macro_dff.py
    (ALFRED vintage, strictly-before as-of) + features/ff5.py (stock-specific rolling exposures +
    interactions, RD-13 gate) + runner (aborts without owner ledger row) + config (20 cols) + 41 tests.
  - **RES-03 (BASELINE-RANK-001)**: learner.py rank-aware branch enforcing frozen RD-15 enum
    (validate_objective("lambdarank"); "regression" branch untouched) + runner (frozen chain
    construct_month_groups→…→fit_predict_rank) + config + 15 tests. `ranking_contract.py` 0-diff.
  - **Full hermetic suite: 1408 passed / 0 failed** (+56 new tests); ruff clean; ledger 0 diff; no
    frozen surface touched; no real data run. docs: data-intake-french-ff5.md (7-gate, owner 签注
    PENDING) + baseline-ladder{,-ff5,-rank}.md (index + per-baseline, conflict-merged).
  - **Both baselines now await: owner authorization + `config_committed` ledger row before any OOS
    metric.**
- **2026-08-03 `/goal` batch 5 — RES specs rewritten via 4 parallel agents (COMMITTED + pushed, `2f87970`):**
  executed approved D5 (RES restart) the RIGHT way this time: **4 sonnet agents dispatched in 2 batches of
  2 (≤2 concurrent proxy cap), file-isolated (each writes only its own task file — parallel without the
  writer race), verified each touched ONLY its target**. Each rewrite fixes its root defect:
  - RES-02: raw market-wide FF5/DFF columns (zero cross-sectional variation → unrankable) → stock-specific
    rolling beta-to-factor + loading×characteristic interactions; PIT proof + RD-13 guard + French 7-gate
  - RES-03: defined the rank-label/query contract anchored to FROZEN RD-15 + ranking_contract.py; removed
    invalid objective names; forbidden to modify frozen impl
  - RES-08: monolithic → durable 5-stage schema/sample/annotation/adjudication/freeze (ADR-006), REUSING
    the existing docs/llm-extractor-eval.md + src/aionis/schema/gold_annotation.py schema (not reinventing)
  - RES-10: every metric anchored to RD-04/06/07/08/11 + RES-08 gold set (no re-spec from scratch)
  All 4 agents went idle without reports (idle-without-result pattern) but their work landed in the tree —
  verified from repo state, NOT prose (§8 recovery path). 8 files (+679/-340); ledger 0 diff; no
  src/frozen-surface change. All 4 specs now "REWRITTEN 2026-08-03 — ready for owner authorization".
- **2026-08-03 `/goal` batch 4 — approved owner decisions executed (COMMITTED + pushed, `c09bd0b`):**
  owner approved all recommendations (D1-D8). Evidence in `reports/design/2026-08-03-owner-decision-execution.md`.
  D1: Track B config VERIFIED already frozen 2026-08-02 (ledger #41/#42) — no new row. D2: AUD-06 contracts
  FROZEN (`max_age_sessions=22`, `authoritative_refresh=None` — factual, no standalone universe script;
  `block_on_unknown=True`) → **E3 Slice 6/7 may proceed to implementation** (headline still gated by owner GO).
  D3: C5 Option A — politeness split in CLAUDE.md L49 (data-fetch ≥2s; model APIs RPM/TPM+cooldown+cache);
  C5 → OWNER-APPROVED. D4: FF 7-gate recorded. D5: RES restart approved (4 specs need rewrite first). D6: RD
  safe queue exhausted. D7: KAIROS verified (MIT, 0-star demo-grade — cite valid). D8: FinLake-Bench CONFIRMED
  NOT RELEASED (name inconsistency FinLake/FinLeak); audit §5 corrected. Docs/state only; no frozen
  surface/ledger/data touched; verification agents used WebFetch only.
- **2026-08-03 `/goal` batch 3 — citation-integrity audit (COMMITTED + pushed, `20191fd`):** directly
  answered the hook's (a)/(c)/(d) requirements. **4 parallel verification agents, tiered by difficulty**
  (haiku ×2: 1-entry E3 + 3 inline IDs; sonnet ×2: 5 frontier + 4 E2 entries) audited ALL arXiv
  citations across frontier_positioning.md / phase-e2 / phase-e3 / theory-of-computable-reality.
  **Result: 11/11 real, none fabricated.** Precision fixes applied to frontier_positioning.md:
  L62-65 overstatement (`2504.14765` = recall-level memorization; "functional lookahead bias" term +
  `market_impact` detail NOT in abstract — possible sister-paper conflation), L49 anchored to real
  title, L35-36 bare IDs → full URLs. **External-reuse verdict (7-gate)**: purgedcv (MIT, installed/
  pinned/importable) = only compliant wheel; lookaheadbench + CAMEF no LICENSE → non-reusable;
  Alpha Illusion code link dead (404); 2504.14765 CC BY-NC-ND → citation-only; CausalStock no repo;
  **FINSABER = Apache-2.0 → passes allowlist (the wheel Track B is mounting — independent license
  evidence)**. Profit Mirage's "51-62% Sharpe decay" verified verbatim. Full ledger:
  `reports/design/2026-08-03-citation-integrity-audit.md`. Docs-only, no code/frozen-surface change.
- **2026-08-03 `/goal` batch 2 — Slice-2 backlog fully closed (COMMITTED + pushed):** completed the
  remaining Slice-2 items. (1) **`5ffdbe1`** — first-run `last_poll_ts=None` seeding docstring notes in
  all 3 forward collectors (13D/macro/8-K; docstring-only). (2) **`758d87e`** — structlog warning when
  `persist_snapshot` writes the REAL ledger (`runs_dir=None`): the shared persist tail covers all 3
  collectors at once; the backlog's `forward_only=True` wording was stale (row-level constant, not a
  param). Not unit-tested by design (exercising the branch would write the real ledger, which
  `test_real_ledger_jsonl_untouched` pins as forbidden). **Full hermetic suite: 1352 passed / 0 failed**
  (final verification); ruff clean; forward-ingest 16/16. Both pushed. Track-B WIP untouched; no frozen
  surface / ledger / data touched; no real network/LLM/trial.
- **2026-08-03 `/goal` reuse-first batch (COMMITTED + pushed, `f6e0536` + `e6c71ec`):** resumed the
  priority offline program under the owner `/goal` (更多 agents 按优先等级推进; 难度分级模型; 复用轮子禁止重造).
  Proxy is `[1210]`-flaky → direct-write (opus) chosen over dispatch for coherence + token-efficiency.
  (1) **`f6e0536`** — Slice-2 "S cleanup": DRY'd the identical archive→cumulative→ledger tail of the 3
  forward collectors (13D/macro/8-K) into `_common.persist_snapshot(...)` (n_rows appended LAST to keep
  per-collector ledger key order → byte-identical output, H6). Also dropped the redundant `keyfn=str.upper`
  dead branch in earnings_8k. (2) **`e6c71ec`** — full-suite was RED (12 `test_static_site.py` failures,
  pre-existing on clean HEAD): tests were stale vs the committed Track B page (English/base64/tabs). Aligned
  them (Chinese Track B assertions: 探索性/非投资建议/null-预期可发表, SESOI 0.010, 诚实边界, 七主题, 差分
  #41/#42, FF5/mounts, data-driven plotly, no runtime fetch, H6 determinism) AND added `--out-dir` so tests
  build to tmp_path — **hermetic, never touches the `site/` WIP** (Track B's uncommitted `M site/index.html`
  + `D` 2 JSON files stay untouched). **Full hermetic suite now 1352 passed / 0 failed; ruff clean.** Both
  pushed. 状态: state/current.md updated.
- **2026-08-03 ORCH-02 second wave (REJECTED — no code change):** attempted to mirror the
  cumulative-preserve test for 8-K, but the premise was a **grep-suffix miss**: 8-K already has the
  invariant via `test_8k_forward_idempotent_and_cumulative_preserve` (`tests/test_forward_ingest.py:504`).
  A `[1210]`-failed executor had nonetheless written a complete (redundant) test into the working tree
  before its API error; detected via `git diff`, discarded via `git restore` (redundant duplication,
  contra 治理复杂度 ≤ 产出). **Three binding findings**: (1) `[1210]` hit 2 consecutive sonnet spawns
  (`oh-my-claudecode:executor` + `general-purpose`) — today's proxy is flakier than the handoff's
  "transient, single retry works" note, and `general-purpose` did NOT bypass it this time; (2) a
  "failed" subagent can mutate the tree before its API error — always `git status`/`git diff` after a
  failed spawn (folded into `docs/orchestration-protocol.md §8`); (3) gap-analysis must grep the
  CONCEPT (`grep -iE "cumulative.*preserve"`), not a name suffix — the suffix grep manufactured a
  false gap. Task recorded as REJECTED in `tasks/rejected/TASK-ORCH-02-*.md`. Subagent dispatch is
  currently unreliable in this proxy — for the next wave, prefer direct-write (opus) for S test
  mirrors unless the proxy recovers.
- **2026-08-03 ORCH-01 first wave (COMMITTED `8d19b28`):** validated the ADR-012 dispatch protocol
  end-to-end. Picked the backlog "macro cumulative-preserve test" (S, hermetic). Ran
  `scripts/orchestrate_dispatch.py --lane executor` → clean 6-layer contract (exit 0). Dispatched sonnet
  `executor` (orch01-executor) → implemented `test_macro_forward_cumulative_parquet_preserves_prior_rows`
  (tests/test_forward_ingest.py:373, +75 lines; faithful 13D mirror — cumulative==24, snapshot_ts=={t1,t2},
  T1+T2 pub-dates ⊂ cum). Orchestrator independent verify: pytest 16/16 green, ruff clean.
  **Reviewer-lane operability gap (binding finding)**: the dispatched `code-reviewer` (sonnet) went idle
  WITHOUT returning a verdict (×2); per WORKFLOW §17 (2-identical-failures stop) the Orchestrator
  proceeded on independent deterministic verification + line-by-line diff review, deviation explicitly
  disclosed in the commit. **Harness behavior**: sync subagents return via `idle_notification`, not inline
  — reclaim L6 via SendMessage; for code lanes, recover from repo state (git diff + pytest + ruff), never
  trust worker prose. Folded into `docs/orchestration-protocol.md §8`.
- **2026-08-03 orchestration protocol (COMMITTED `daa92e8`):** owner directive — "主agent编排+验收,
  高等级模型监工(低频), 分配任务给其他模型, review+e2e会话, 跨会话降噪, issue编排任务" — implemented by
  **binding existing OMC primitives**, not building a new framework (reuse-first). Owner chose **local task
  files = issues** (zero GitHub surface; minimizes the 治理复杂度>产出 drift). New additive artifacts:
  `decisions/ADR-012-orchestration-protocol.md` (ACCEPTED) + `docs/orchestration-protocol.md` (operational
  spec) + `scripts/orchestrate_dispatch.py` (6-layer contract emitter, reuses RD-01 `lint_task_file`) +
  `tests/test_orchestrate_dispatch.py` (11/11 green, ruff clean) + `tasks/templates/DISPATCH-CONTRACT.md`.
  Registered ADR-011 + ADR-012 in `decisions/index.md`; added CLAUDE.md see-also pointer. Lane model: opus
  Orchestrator + **low-freq opus Supervisor (监工, gates only)** + sonnet `executor`/haiku workers
  (serialized, ≤2 concurrent — parallel-writer race + `[1210]` cap) + independent `verifier`(验收) /
  `code-reviewer` / `qa-tester`(e2e) lanes. Denoising = 6-layer dispatch contract (WORKFLOW §10) + structured
  handoff (workers return files/tests/evidence/next-action, never narrative; no full-chat forwarding).
  Anti-leakage guardrails binding on every dispatch (no real network/LLM/forward; frozen surfaces read-only;
  config_committed-before-result; ledger 0-diff). **Additive only** — no frozen surface / ledger / data /
  Track-B code touched; no real network/LLM/trial ran. Next: owner commissions the first wave (pick a task →
  run the helper → dispatch to `executor`).

- **2026-08-02 strategic review:** "是否跑偏 + 七主题低成本覆盖" deep-dive → `reports/2026-08-02-strategic-review-coverage-and-alignment.md` + 6 `reports/design/` artifacts (Track A/B slice plans, slice review, qlib POC, wheel-mount pack, reuse-catalog v2) + `src/aionis/eval/ff5_residual.py` (挂接③, 18 tests green, ruff clean; exploratory, not wired to pipeline/ledger). Verdict: direction sound; two失调. **Owner decision (2026-08-02):** Track B adopted + new prereg (`decisions/ADR-011-track-b-seven-theme-platform.md` + `docs/track-b-preregistration.md` PROPOSED); 挂接③ first slice done. **Pending:** owner freezes config sha256 before real-data. 未触冻结面/ledger/E3；无真实 network/LLM/trial.
- **round:** Wave-A execution. AUD-05B is closed after authorized re-Review. Dashboard extraction
  and C4 Option A cleanup are committed in `7dede9b`. C1 BLS disable, C2 VIX FRED adapter and C3
  PRAW requestor wrapper are COMPLETE after Engineer evidence, independent Verifier PASS and
  independent Reviewer APPROVE, and are ready for the Group A commit. 2026-08-01.
- **outcome:** project remains an evidence-first PIT research harness, not a validated stock-picking strategy.
  Historical B/C/D/E1 are shared-fold purged CV-proxies (not chronological OOS); LLM not in headlines;
  E3 NO-GO for headline.
- **COMPLETE:** AUD-01/02/03/04/05A/05B (each Verifier PASS + Reviewer APPROVE); AUD-05C disposition
  (Reviewer APPROVE; 10 boundaries → C1-C5 + Kenneth-French task files); **AUD-07 FROZEN** via
  [ADR-010](../decisions/ADR-010-sesoi-tost-sequential-gate.md) + E3 pre-reg §7 (SESOI ±0.010 / HAC-TOST
  90% / O'Brien-Fleming 60·90·120mo / n_trials=30; 3× cross-validated; equivalence+sequential
  construction amended).
- **STATISTICAL HOLD:** AUD-07B reopens the implementation-level proof only: ADR-010's amendment says
  TOST p-values “exceed alpha”, which appears reversed, and the sequential equivalence construction
  requires strong independent review. Do not implement or expose E3 inferential verdicts meanwhile.
- **C-series prepped → owner-decidable:**
  - **C3 (PRAW 7-gate)**: OWNER APPROVED WITH CONDITIONS (all 7 gates PASS; G1 BSD-2/Apache-2.0, G2 PIT,
    G3 snapshot handles user-edits, G4 sha256+append, G5/G6 exploratory-only, G7 PRAW 1.5s+ToS).
    Conditions: Reddit ToS internal-only/no-redistribute; permanent `mode:exploratory`. Engineer,
    Verifier and Reviewer are complete; no live pull is authorized.
  - **C1 (BLS disable)**: owner-authorized disable-only implementation is complete. CPI/NFP cache
    misses fail closed before HTTP; FOMC/cache behavior is preserved. Independent Verifier PASS and
    Reviewer APPROVE are recorded; Group A commit is next.
  - **C2 (VIX/FRED)**: owner-authorized implementation replaces SDK fetches with the shared-policy
    FRED observations adapter while retaining ADR-003 PIT/cache/ledger behavior. Independent
    Verifier PASS and Reviewer APPROVE are recorded.
  - **C4 (health_check)**: standalone Option A is owner-authorized and complete in `7dede9b`.
    The blocked data/wheel probes and stale text are removed; seven hermetic tests, lint, scan and
    review pass.
  - **C5 (model-API ≥2s)**: **Option A (SDK-exempt)** recommended — model APIs throttled by provider
    RPM/TPM + ProviderRouter cooldown + idempotent cache; ≥2s redundant for GLM (RPM 30), harmful for
    SiliconFlow (RPM 1000). Rule wording drafted. → owner accept.
- **P2 legacy split → partially replan-required**: 10 prior `TASK-RES-01..10` files exist (baseline-ladder
  RES-01/02/03 [mom/FF5/rank-objective]; economic-lens RES-04/05/06/07 [next-open/turnover-slippage/
  liquidity-borrow/delisting-capacity]; LLM-eval RES-08/09/10 [gold-set/zero-LLM-ablation/eval-metrics]).
  RES-02/03/08/10 are now HOLD/REPLAN because of cross-sectional-variation, rank-label,
  durable-gold and remote-determinism defects. Do not authorize those files as written; use RD tasks first.
- **owner-decision queue (consolidated — further progress needs these):**
  - **C5**: accept Option A + record the rule wording?
  - **Kenneth-French / selection-panel FRED+Fama-French**: data-intake 7-gate decision.
  - **AUD-06**: owner contract (E3 live-input readiness acceptance points).
  - **RES program**: no legacy RES task should start before RD-17 and its listed prerequisites; RES-02/03/08/10
    specifically require rewritten specs.
  - **RD program**: launch only P0 closure, P0 + the offline RD-01..17 program, or selected RD tasks?
  - **Commit?** audit remediation is committed as `e8545d4` and dashboard/C4 remediation as
    `7dede9b` (both on remote `main`). C1/C2 await independent review before their own commit.
- **verification:** the full hermetic pytest suite currently passes (existing forward-score warnings
  only), `uv run --offline ruff check` and `git diff --check` pass, and frozen
  prereg/ADR/config/ledger/results/data/forward remain untouched. Group A C1/C2/C3 each have
  independent Verifier PASS and Reviewer APPROVE. `runs/ledger.jsonl` remains unchanged; no E3
  outcome was observed and no confirmatory/strategy/horizon/forward/real-network/LLM script ran.
- **planning artifact:** `reports/milestone/2026-08-01-low-reasoning-development-roadmap.md` and
  the Wave-A launch brief and `TASK-RD-00..17` split the next safe work into a 10.75–16 hour first
  offline wave and a 25.5–40 hour complete Engineer package. `TASK-AUD-07B` is strong-only. This is a
  frozen task proposal. The final unattended prompt selects C1/C2/C3 + RD-04/05/06/07/09/10/12,
  has explicit context-compaction/token rules, and received independent Reviewer APPROVE. It becomes
  implementation GO only when the owner pastes it into the new Goal session.
- **proxy note:** 3-parallel subagent spawns fail with proxy 400 `[1210]`; ≤2-parallel / single work.
  Future dispatch ≤2 concurrent.
- **do NOT:** run confirmatory/strategy/horizon/forward scripts; edit frozen prereg/ADR/config; infer
  B's paired differential CI; call historical cross-fit chronological OOS; inspect E3 outcome metrics;
  ignite E3 headline.
- **git:** branch `feat/e3-forward-ledger`; remote `main` includes `7dede9b`. Current uncommitted
  code includes approved C1/C2/C3 implementation/tests plus planning/state/task documentation; the
  Group A commit will use explicit file lists only.

## Overnight checkpoint (Wave-A)

- Goal: execute Wave-A C1/C2/C3 + RD-04/05/06/07/09/10/12 with independent gates and safe push. **COMPLETE.**
- All gates passed: C1/C2/C3 + RD-04/05/06/07/09/10/12 each have independent Verifier PASS + Reviewer APPROVE.
  Fixes applied and re-gated: RD-07 (generated_at caller-provided for byte-stability), RD-10 (vol_adj_mom
  last-12 window + std<=0), RD-12 (additive constituents_manifest_on + 3 unskipped manifest oracles;
  constituents_on behavior unchanged).
- Commits: `6085e92` Group A, `2653907` Group B, `5f884a3` Group C. Final docs/state bundle (this commit).
- Final gates: full hermetic pytest green (zero skips; only pre-existing forward_score warnings);
  `uv run --offline ruff check` clean; `git diff --check` clean; frozen/ledger/results/data/forward diff
  empty; no data/.env/*.parquet staged; no real network/LLM/research/forward script ran; E3 outcome unobserved.
- Files: RD-01/02/03/08/11/13..17 task specs remain PLANNED (future waves) — committed as planning docs.
- Blockers: none. Next: optional fast-forward push HEAD:main (origin/main is ancestor of HEAD).

## Wave-B checkpoint (2026-08-01, in progress)

- **Launch authorization:** owner `/goal` — "启用更多 agents 根据优先等级在不影响各自进程的前提下各自推进".
  Treated as owner authorization for the priority (P0→P1) offline RD program (the safe sonnet-tier set).
  Per-task authorization is recorded in each task file's 状态 line by the Orchestrator as the audit trail.
- **COMPLETE so far** (each: Engineer → independent Verifier PASS → independent Reviewer APPROVE → atomic
  commit; offline/hermetic; `runs/ledger.jsonl` untouched; no frozen surface touched):
  - RD-02 validation manifest — `97e5688`
  - RD-01 task-contract linter — `feb80ba` (first attempt lost to the parallel-writer race below; redone serially)
  - RD-13 cross-sectional variation guard — `2f0efd0`
- **KEY OPERATIONAL FINDING (binding):** spawning ≥2 writer subagents concurrently in the SHARED working tree
  loses one agent's untracked deliverables (RD-01 first attempt: `.pyc` survived in gitignored `__pycache__`,
  `.py` + README diff gone — consistent with a `git clean -fd`/`restore` across parallel-agent boundaries).
  **Writers are now SERIALIZED: exactly ONE Engineer subagent per message.** Parallel is reserved for read-only
  preflights only. See memory `aionis-parallel-writer-race`.
- **Model routing (binding):** only `sonnet`/`haiku` subagent aliases resolve to subagent-safe IDs; `opus`/`fable`
  resolve to `[1M]`-suffixed IDs and are DENIED by the enforcer. The RD program is sonnet-tier so this is fine.
  `TASK-AUD-07B` (strong-only, STATISTICAL HOLD) and `RD-15` (strong precondition) are DEFERRED until opus
  routing is fixed (drop `[1M]` suffix from `ANTHROPIC_DEFAULT_OPUS_MODEL`).
- **Authorization bookkeeping:** the first RD-02 Reviewer returned BLOCKED solely because the task file still said
  "PLANNED — not implementation-authorized"; resolved by recording the /goal authorization in the task 状态 line.
  All subsequently launched RD tasks are pre-authorized in their task files before dispatch.
- **Remaining safe queue (P1, sonnet-tier):** RD-17 (trial-intent registry) → RD-16 (eval uncertainty) → RD-11
  (provider replay) → RD-03 (chronological oracle, unlocked by RD-02 APPROVE) → RD-14 (reproducibility capsule,
  unlocked by RD-02 APPROVE). RD-08 remains HOLD (needs a strong-Researcher-frozen rule table first). RD-15 deferred (strong).
- **Verification status:** per-task pytest + ruff green; ledger empty diff across all Wave-B commits; no frozen
  prereg/ADR/config/result/data/forward surface touched; no real network/LLM/trial ran. The full hermetic suite
  has NOT been re-run this wave yet (defer to a pre-push gate).
- **Git:** branch `feat/e3-forward-ledger` ahead of origin by 8 (Wave-A + Wave-B). Not pushed (owner's call).
- **Do NOT:** run confirmatory/strategy/horizon/forward scripts; edit frozen prereg/ADR/config; observe E3
  outcome; spawn >1 writer subagent per message.

## Wave-B FINAL (2026-08-01, COMPLETE)

All 8 safe sonnet-tier RD tasks implemented, each with independent Verifier PASS + Reviewer APPROVE and an
atomic commit; offline/hermetic throughout:
- RD-02 validation manifest — `97e5688`
- RD-01 task-contract linter — `feb80ba` (first attempt lost to the parallel-writer race; redone serially)
- RD-13 cross-sectional variation guard — `2f0efd0`
- RD-17 trial-intent registry (HIGH-risk; ledger-bypass cleared) — `5dfe849`
- RD-16 eval uncertainty (Wilson≠Wald; seed=0 stratified bootstrap) — `ee223ae`
- RD-11 provider replay (salvaged a cut-off partial; audited + completed; providers/llm_client 0 diff) — `8a46179`
- RD-03 chronological oracle (HIGH-risk; cv.py 0 diff; lookahead rejected; real purgedcv) — `af7d673`
- RD-14 reproducibility capsule (outcome-free; deterministic capsule_id; atomic write + refuse-overwrite) — `f397383`

Final pre-push verification: full hermetic pytest GREEN (zero failures/skips; only the pre-existing
forward-score UserWarnings documented in Wave-A); `uv run --offline ruff check` clean; `runs/ledger.jsonl`
0 diff across the whole wave; frozen-surface audit (docs/phase-*, decisions/, runs/ledger, config/, data/,
*.parquet, pyproject.toml, uv.lock) — NONE touched; no real network/LLM/trial/forward script ran; E3 outcome
unobserved.

Process notes (binding for future waves):
- Writers are SERIALIZED (exactly one Engineer subagent per message) — parallel writers in the shared tree
  lost untracked deliverables (see memory aionis-parallel-writer-race).
- Only `sonnet`/`haiku` subagent aliases are dispatchable; `opus`/`fable` resolve to `[1M]` IDs and are
  denied by the enforcer → `TASK-AUD-07B` (strong-only) + `RD-15` (strong precondition) are DEFERRED until
  opus routing is fixed.
- The `[1210]` proxy "API parameter" error is transient on Reviewer spawns — a single retry has succeeded
  every time; it is NOT the 5-hour usage cap.
- Owner authorization for the priority RD program was the `/goal` directive; recorded per-task in each task
  file's 状态 line. (The first RD-02 Reviewer BLOCKed on the stale "PLANNED — not implementation-authorized"
  status, which is why all later tasks were pre-authorized in their task files before dispatch.)
- Per the owner: do not spend tokens checking whether the 5-hour usage cap has reset — if the session is
  running, it is reset (see memory aionis-no-rate-limit-check).

Remaining (NOT started — legitimately blocked, not merely unauthorized):
- RD-08 HOLD — needs a strong-Researcher-frozen zero-LLM rule table before low-reasoning implementation.
- RD-15 DEFERRED — rank-objective contract is a strong-model decision precondition (lambdarank vs rank_xendcg,
  monthly relevance binning, ties, missing, group=query-month); also needs opus routing.
- AUD-07B — STATISTICAL HOLD on ADR-010 TOST p-value direction / sequential-equivalence construction; strong-only.
- RES-02/03/08/10 — HOLD/replan per roadmap; their foundations (RD-13 done; RD-15/RD-08 still pending) must
  precede them.

Git: branch `feat/e3-forward-ledger` ahead of origin by 13 (Wave-A + Wave-B). Not pushed — owner's call.
Safe RD queue now exhausted for the sonnet tier.

## Track B 首个 OOS 观察（2026-08-02）

**treatment 臂（config #41）**: mean_ic 0.0055, 95% HAC CI (-0.021, 0.033), p=0.689（null）。**price-only 臂（#42）**: mean_ic -0.0021, CI (-0.032, 0.028), p=0.891（null）。**差分（#41 − #42, §1 headline）**: mean_diff 0.0076, CI (-0.004, 0.020) 跨零, p=0.219 → treatment 未显著优于 price-only（null，符合 null-favored）；CI 上界 0.020 > SESOI 0.010 → 不构成严格等价（需更多样本）。见 docs/track-b-results.md。

## AUD-07B — statistical review COMPLETE (2026-08-01, CRITICAL finding)

AUD-07B (P0 / CRITICAL) is now reviewed by TWO opus agents (a strong-statistician audit + an INDEPENDENT
opus Reviewer, APPROVE). Both confirm ADR-010's equivalence/sequential gate has TWO CRITICAL defects:
1. **TOST rejection direction is REVERSED.** ADR-010 Line 42 requires the two one-sided p-values to
   "exceed alpha" (p > α); the correct Schuirmann (1987) rule is: declare equivalence iff p1 < α AND p2 < α.
   As written, the gate would declare NON-equivalence, not equivalence.
2. **Sequential CI duality is BROKEN.** ADR-010 pairs a fixed 90% CI with look-specific O'Brien-Fleming αk,
   which breaks the TOST⇔CI duality at looks 2–3 and inflates first-look Type I error ~9.6× (0.05 vs
   ~0.0052). Correct construction: look-specific (1−2αk) CIs (98.96% / 96.84% / 91.26%), or a recognized
   group-sequential equivalence construction (Jennison–Turnbull 2000).
CI duality at α=0.05 (90% CI), the union–intersection composite null, and HAC (Newey-West) SE all PASS.
Report: `reports/audits/e3-tost-sequential-correction-review.md`.

CONSEQUENCE (binding): the E3 inferential-verdict and headline remain HOLD. Implementing or exposing any E3
equivalence verdict before the owner authorizes an ADR-010 + prereg §7 amendment (p < αk; look-specific CI)
is FORBIDDEN. This is an owner decision — ADR-010 and the prereg are frozen; the audit does NOT modify them.
Open non-blocking note: ADR-010's αk source (0.0052 / 0.0158 / 0.0437) is undocumented and did not match the
reviewer's independent Lan-DeMets OBF recomputation — owner should confirm the αk provenance as part of the
amendment.

## Model-differentiation policy (2026-08-01, per owner /goal)

opus subagent routing was fixed (`ANTHROPIC_DEFAULT_OPUS_MODEL` now `claude-opus-4-8`, no `[1M]` suffix).
Difficulty-based dispatch is now in effect to save tokens:
- **opus** — only genuinely hard analysis/decisions (AUD-07B statistician + reviewer done; RD-15 rank-objective
  contract and the RD-08 zero-LLM rule-table draft are the next opus candidates).
- **sonnet** — standard code/review (Wave-B RD tasks).
- **haiku** — mechanical verification, simple doc/grep checks.
Writers remain SERIALIZED (one Engineer per message; parallel-writer rule still binds).

## RD-15 — rank-objective DECISION PACKET proposed (2026-08-01, pending owner freeze)

RD-15 (P2 / HIGH-risk) decision precondition is now drafted by an opus Architect at
`reports/design/2026-08-01-rd15-rank-objective-contract.md` (PROPOSED — pending owner freeze). 7 of 8
choices are determined by theory; ONE is an owner-preference question:
- **Open owner question:** bin count for monthly relevance — **quintiles (5, robust, default)** vs
  **deciles (10, aggressive)**. Ranking theory does not uniquely determine this for the rank-IC estimand.
Theory-fixed choices: objective = **lambdarank** (rank_xendcg rejected; allowed-enum fixed so non-existent
objectives are rejected); per-month quantile binning fit ONLY on the train fold; group = query-month; ties
share the relevance integer; NaN returns excluded (NaN features → LightGBM default); test out-of-range
returns clamped to nearest train-fold edge + reason code (never refit). Four testable leakage invariants
specified (month-permutation, future-truncation, train-fold-only fit, group-size stability).

After owner freeze, a sonnet Engineer implements `src/aionis/eval/ranking_contract.py` + tests mechanically
(no self-selection). No code/learner/frozen surface changed by the decision packet.

### Update (2026-08-01, continued — model-differentiated dispatch)
- **RD-15 implementation COMPLETE** — `ea335c8` (sonnet Engineer + independent Verifier PASS + Reviewer
  APPROVE; 0 blocking). `src/aionis/eval/ranking_contract.py` implements the decision packet (objective enum
  lambdarank/rank_xendcg; per-month train-fold-only binning; out-of-range clamp+reason; group=query-month; 4
  leakage invariants). `bin_count` is a parameter (default 5/quintiles, supports 10/deciles) — the methodology
  freeze of the actual value remains the owner's (via config), not hard-coded. learner.py untouched (0 diff);
  31 module tests + full suite (1348) green.
- **RD-08 rule table PROPOSED** — `evals/expected/zero_llm_rules_v1.yaml` (opus strong-Researcher), pending
  owner freeze. 10 conservative abstain-heavy rules (FOMC×3, CPI×2, NFP×2, 13D×3); default/conflict=abstain;
  8k_2_02 deferred. Two owner decisions flagged: 13D actor_type (COLLECTIVE vs ORGANIZATION) and whether to
  include 8k_2_02. After freeze, a sonnet Engineer implements `src/aionis/extraction/zero_llm_baseline.py`
  verbatim from the table.
- **Tier usage this session:** opus for AUD-07B (statistician + independent reviewer) and RD-15 decision +
  RD-08 rule-table draft (genuinely hard analysis/domain-modeling); sonnet for all Wave-B code + RD-15 impl +
  verifications/reviews (standard). haiku unused — no remaining priority task is mechanical-tier (forcing it
  would be false economy). Reviewer `[1210]` proxy errors were bypassed by switching `oh-my-claudecode:code-
  reviewer` → `general-purpose` (same sonnet tier) when they recurred.

## Owner decisions + independent opus reviews (2026-08-01)

Owner decisions: ADR-010 → Jennison-Turnbull construction (B); RD-15 bin_count → quintiles/5 (A); RD-08 → freeze
(A) + COLLECTIVE + defer 8k_2_02; RES → hold (A); commission independent opus review of RD-08 + RD-15 (5B);
housekeeping done (local main FF to origin/main; remote feat/e3-forward-ledger deleted). All Wave-B/AUD-07B/
RD-15/RD-08 work pushed to origin/main (HEAD e58b16e).

Independent opus review outcomes:
- **RD-15 decision packet: APPROVE** (0 CRITICAL/MAJOR; leakage guards sufficient, implementation faithful).
  Owner froze bin_count=5.
- **RD-08 rule table: REQUEST CHANGES → FIXED → FROZEN.** Review found 4 CRITICAL (enum NAME vs lowercase VALUE;
  FOMC forward-guidance false positives; 13D→13d; negation-window unit undefined) + 2 MAJOR (CPI/NFP secondary
  patterns; rule-count comment). An opus fixer resolved all: lowercase enum values; added fomc_guidance_abstain_001
  (precedence 110, abstain-only); 13d; negation = whitespace words; tightened CPI/NFP; accurate count (now 11).
  event_type semantics confirmed: FOMC/CPI/NFP are valid (`src/aionis/config.py` ECONOMIC_EVENT_TYPES); the gold
  `Literal["13d","8k_2_02"]` is filing-specific. Table FROZEN.

Still queued (owner-authorized, not yet done this session): RD-08 sonnet implementation of `zero_llm_baseline.py`;
ADR-010 Jennison-Turnbull amendment (opus design + independent opus review + apply to frozen ADR-010/prereg §7).

## ADR-010 Amendment APPLIED (2026-08-01) — Jennison-Turnbull; RD-08 implemented

- **RD-08 zero-LLM baseline COMPLETE** — `src/aionis/extraction/zero_llm_baseline.py` (sonnet Engineer + haiku
  lint-fix + independent Verifier functional PASS + independent Reviewer APPROVE). Mechanically applies the
  FROZEN rule table (11 rules; lowercase enum values; sha256 provenance; 6 abstain paths; fomc_guidance_abstain_001
  precedence-110 suppresses forward-guidance false positives). Structural-only (no sentiment/market_impact);
  providers/llm_client/frozen table untouched. Committed + pushed.
- **ADR-010 Amendment 2026-08-01 APPLIED** (owner Decision 1 = option B). The broken "Cross-validation amendment
  (2026-07-31)" is VOID; replaced by a Jennison-Turnbull (2000) group-sequential equivalence construction
  (OBF zₖ = z_α/√Iₖ → look-specific RCI levels 99.44 / 97.64 / 95.00%; equivalence iff RCIₖ ⊂ [−SESOI, +SESOI],
  which structurally prevents the reversed-direction error; Type I ≤ 0.05). Prereg §7 amended in lockstep.
  Ratified sub-choices: standard OBF (over Lan-DeMets — more conservative early), no futility, 95% final look.
  Frozen params unchanged (SESOI ±0.010, looks {60,90,120}, n_trials=30, HAC SE). Double-opus (design +
  independent review) at `reports/audits/e3-jt-amendment-proposal.md`; audit at
  `reports/audits/e3-tost-sequential-correction-review.md`.
- **CONSEQUENCE:** the E3 statistical-gate HOLD from AUD-07B is LIFTED (the gate is now mathematically valid).
  E3 itself remains gated by AUD-06 (live-input readiness) + a separate owner GO (per the AUD-00 dependency
  graph); no E3 ignition is authorized here. Eval-code implementation of the RCI rule is a separate future task.

All owner decisions 2026-08-01 are now executed except RES restart (intentionally held) and optional follow-ups
(RD-08 rule-table re-review, eval-code RCI implementation). Everything is on origin/main.

## Dashboard v2 — near-final-product analysis interface (2026-08-01, built + gated)

Per owner intent ("把现有研究工作台做成接近最终产品形态的分析界面"; data demonstrative only), built a Streamlit+plotly
dashboard realizing `docs/dashboard-v2-design.md`'s 5 dimensions on deterministic synthetic data:
- `dashboard/{demo_data,charts_v2,app_v2}.py` + `dashboard/README_v2.md` + `tests/test_dashboard_v2.py` +
  `reports/design/2026-08-01-dashboard-v2-deploy-research.md`.
- 5 tabs (拟合质量/波动结构/曲线演化/事件前后差异/不确定性), sidebar (Phase/Arm/Horizon/Event-type), publishability gate
  (ci_half<0.015) + "Preliminary data — demonstrates the method" caption on every tab. 11 plotly chart builders
  (alphalens/pyfolio/empyrical methodology, Apache-2.0; no new deps).
- Gated: independent Verifier (AppTest headless render — caught + fixed a `StreamlitDuplicateElementId` crash via
  unique `key=`) + Reviewer APPROVE. 32 tests pass; ruff clean. `src/aionis/**`, `dashboard/app.py` (v1),
  `runs/ledger.jsonl`, data, frozen surfaces all UNMODIFIED.
- RUN: `uv run streamlit run dashboard/app_v2.py`. Deploy: GitHub Pages CANNOT host Streamlit (static-only);
  for the interactive dashboard on a private repo, Hugging Face Spaces (Streamlit runtime, free, private-OK) is
  the recommended host (see the research report). Not yet deployed — owner's call.
- **STATIC site DEPLOYED to GitHub Pages (2026-08-01):** `https://rethymus.github.io/Aionis/` — owner chose
  "static, no interactivity, early-stage presentation." `scripts/build_static_site.py` reuses charts_v2/demo_data
  read-only → `site/index.html` (13 plotly charts, 5 dimensions, EXPLORATORY/DEMONSTRATIVE banner, publishability
  gate). `.github/workflows/deploy-pages.yml` (astral-sh/setup-uv + `uv sync --extra dashboard`; build→upload→deploy
  on push to main). Repo stays PRIVATE; Pages site is public (owner account supports private-repo Pages). Verified
  live (HTTP 200, full content). Independent Verifier PASSED (build, 13 Plotly.newPlot, MD5-deterministic, boundaries).
- **J-T SESOI gate IMPLEMENTED (2026-08-01):** `src/aionis/eval/sesoi_gate.py` + `tests/test_sesoi_gate.py` — the
  executable follow-through of ADR-010's Amendment 2026-08-01. Pure statistical functions (obf_z/obf_alpha/rci_level/
  compute_rci/equivalence_verdict/look_summary/sequential_equivalence_gate) implementing the frozen OBF zₖ=(2.772,
  2.263, 1.960), look-specific RCI levels (99.44/97.64/95.00%), strict-containment equivalence RCIₖ⊂[−0.010,+0.010],
  first-look stopping; reuses `aionis.eval.rank_ic.rank_ic_summary` for HAC SE (not reimplemented). Consumes
  caller-provided IC series ONLY (no E3/ledger/result reads — pure gate logic). Independent Verifier PASS (oracle
  recomputed, strict-boundary, first-look stopping) + Reviewer APPROVE. 28 tests; ruff clean. NOTE: implementing the
  gate does NOT ignite E3 or observe any outcome; E3 still needs AUD-06 + owner GO.
- **AUD-06 live-input readiness gate IMPLEMENTED (2026-08-01, parameterized):** `src/aionis/eval/forward_live_readiness.py`
  (+ tests) + opt-in wiring in `forward_commit_runner.py` (`enforce_live_readiness: bool = False` → historical/no-ledger
  paths SKIP the gate, preserving `_clean_panel`/forward behavior; the live Slice 6/7 caller sets the flag). Fail-closed
  preflight BEFORE any fit/LLM/write/ledger (spy-asserted fit_calls==0 on failure); 25 actionable reason codes; concrete
  checks (predict_session via NYSE, train realized+21-embargo / test retains unknown labels via a forward-specific helper
  NOT `_clean_panel`, price coverage, universe match `constituents_on(t)`, empty-LLM-text→fail, provider-cutoff-not-faked).
  The 2 OWNER-GATED checks are PARAMETERIZED + FAIL-CLOSED when unset: `membership_freshness_contract` (max age /
  authoritative refresh) + `provider_cutoff_policy` (block_on_unknown) — the owner must freeze these before E3 launch
  (the task forbids self-freezing, e.g. treating a 2026-04 snapshot as fresh for 2026-07). Salvaged from a rate-limited
  partial (opus fixer: opt-in flag fixed 2 regressions; fixture/timezone fixes for 8 new tests; ruff). Independent opus
  Verifier PASS (historical-preserved, `_mem_stub` change benign, spy-asserts, fail-closed) + sonnet Reviewer APPROVE.
  47 forward tests pass; ruff clean; ledger/prereg/forward_commit.py untouched. Does NOT ignite E3.
