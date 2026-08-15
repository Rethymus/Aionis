> Superseded by owner decision (publication track retired) on 2026-08-15.
# Aionis 可发表单元 — 期刊/会议定位 brief

> 状态：**PROPOSED · 2026-08-05 · opus Orchestrator 起草（positioning agent [1210] 失败后 §8 fallback）· 业主审阅**。
> 本 brief 把"反泄漏纪律 + 15 null + power-limit"这个可发表单元匹配到候选 venue，给出推荐。
> 复用：venue 规格来自公开作者指南/编辑声明（web search 验证；部分出版商页面 403，已诚实标注验证等级）。
> 不写 ledger、不触冻结面、不改 config/data/E3。纯决策文档。

---

## 摘要（推荐）

**分层策略**：① **arXiv q-fin.ST preprint**（立即、免费、可引用，作为所有正式投稿的 baseline 与时间戳）；② 正式期刊首选 **Critical Finance Review (CFR)** —— 其"replication / re-examination / takes more risks"的编辑立场与"反泄漏纪律作为研究对象 + power-floor 方法论发现"的框架高度契合，且免费、~28 天 turnaround；③ 备选 **Journal of Financial Econometrics**（若强调 power-floor + J-T 门作为计量方法论贡献）或 **Review of Finance**（明示 null-result 友好）。

**理由**：Aionis 的可发表单元 **不是"发现 alpha"**，而是 ① 一个反泄漏研究治理框架 + ② 一个 dual-region 联合 rank-IC 估计量的方法学构造 + ③ 一个 power-floor 定理（equivalence testing 在月频 rank-IC 需 36+ 年）。这类"方法/纪律/再检验"导向的论文，在期望"显著发现"的实证金融期刊（JEF/Quant Finance 主流轨道）会被 desk-reject 为"no finding"；在方法/再检验导向的 venue（CFR、JFEc、RevFin）才能被公正评估。

---

## 1. 贡献画像（匹配 venue 的依据）

| 维度 | 内容 | 对 venue 的含义 |
|---|---|---|
| 主贡献 | 反泄漏纪律**作为研究对象**（config-before-result / PIT 全栈 / purged CV+embargo / H6 bit-identical / J-T 门 / 两尾 null-favored 预注册 / multiplicity 预算=1） | 方法/治理导向，非"新因子" |
| 方法学新点 | dual-region（US S&P500 + CN CSI300）联合 chronological walk-forward rank-IC 估计量；month-end+日历月折边界⇒per-region 21-session embargo 自动满足（定理） | 计量方法贡献 |
| 证据 | 15 null 点估计（4 CV-proxy + 2 chronological Track B + Track C 联合 exploratory + 2 baseline + h-sweep + **confirmatory #49**），全 CI 跨零 | null = 预期可发表产物，**非失败** |
| 首条 confirmatory | ledger #49：combined IC −0.0088（null），J-T look-1 NOT_EQUIVALENT | 反泄漏纪律端到端演示 |
| power-floor 定理 | SESOI ±0.010 + 月频 rank-IC 噪声 σ≈0.10 ⇒ 宣告等价需 look-3 n=435 月（36.2 年）| 可独立成立的方法论发现 |

**关键诚实点**：这不是"我找到了 alpha"。任何 desk-editor 以"是否有显著正向发现"为筛选项的 venue 都会拒。能接受"no alpha, but here's the discipline + a power-floor theorem + a clean confirmatory null"的 venue 才 fit。

---

## 2. 候选 venue 表（验证等级标注）

| Venue | 范围 fit | 篇幅 | OA/费用 | Turnaround | null+方法 fit | 验证等级 |
|---|---|---|---|---|---|---|
| **arXiv q-fin.ST**（Statistical Finance）/ q-fin.PM | 宽（preprint） | 无限制 | **免费** | 即时 | baseline（可引用时间戳） | ✅ 已知 |
| **Critical Finance Review**（Ivo Welch） | 金融经济全领域；编辑立场"takes more risks"、重视 replication/re-examination/reconciling | 未明示硬限（"all types of documents"） | **免费**（boutique） | **~28 天**（编辑自述） | **最高**——"再检验/纪律"导向；但极选择性（10-20 篇/年） | ✅ 编辑声明验证（cfr.ivo-welch.info/about；jfresearch.org SWFA 报道） |
| **Journal of Financial Econometrics**（Elsevier） | 金融计量方法 | 未取到精确值（出版商页 403） | 混合 OA（Elsevier 标准 APC ~$3000+） | Elsevier 标准（数月） | 高——power-floor + J-T 门作为计量方法论 | ⚠️ 出版商页 403；精确篇幅/APC 待投稿时核实 |
| **Review of Finance**（RevFin） | "the very best research in financial economics, **irrespective of ... whether the findings**"（明示 null 友好） | 标准 | 混合 OA | 标准 | 中高——明示 null-result 友好；但"very best"门槛高 | ✅ aims-and-scope 验证（revfin.org/aims-and-scope） |
| **Quantitative Finance**（T&F） | 跨学科，理论+实证，"rapid publication" | 标准（feature article） | 混合 OA（T&F；机构协议可减免） | rapid | 中——接受方法+实证，但主流仍偏好 finding | ✅ about-this-journal 验证（tandfonline.com/journals/rquf20） |
| **Journal of Empirical Finance**（Elsevier） | 实证金融 | 标准 | 混合 OA | 标准 | 中低——"empirical"导向，null 风险更高 | ⚠️ scope 验证；精确规格待核实 |

> ⚠️ 验证诚实声明：出版商 sciencedirect.com / tandfonline.com 的 guide-for-authors 页面对自动化 fetch 返回 **HTTP 403**（反爬），故精确 word limit / APC 数字未能逐项引用。上表"✅"= 编辑声明或 about 页验证；"⚠️"= 仅 scope 验证，精确篇幅/费用需投稿时从作者指南确认。**未编造任何具体数字**。

---

## 3. Fit-gap 分析（诚实）

**Aionis 是 "NULL RESULT + 方法-纪律" 论文。** 这是它的力量，也是它的 venue 风险：

- **会 desk-reject 的 venue**：任何以"显著正向发现"为隐性筛选标准的顶刊主流轨道（JF/JFE/RFS 主轨、JEF 实证主轨）。编辑看不到 alpha 会默认 "no contribution"。**不要**把这些作为首选——投了大概率浪费 review 周期。
- **能公正评估的 venue**：
  - **CFR**：编辑立场明确支持 replication/re-examination；power-floor + 反泄漏纪律正是它偏好的"再检验"类型。**最大风险是选择性**（10-20 篇/年），需 framing 足够 sharp。
  - **JFEc**：若把 power-floor（equivalence testing 的 power 下限）+ J-T group-sequential 门作为**计量方法论**贡献，JFEc 是自然归宿。风险：Aionis 的"方法"偏治理/工程而非纯计量新估计量，可能被视作"applied discipline"而非"methods contribution"。
  - **RevFin**：明示 null 友好——风险最低的"严肃金融"选项；但"very best"门槛意味着 framing 必须把 power-floor 提升到一等方法学发现。

**最尖锐的 framing 选择**（决定 venue）：
- (a) **"反泄漏研究治理框架"为主** → CFR / RevFin（金融，重纪律与再检验）。
- (b) **"power-floor 定理 + J-T 门"为主** → JFEc（计量方法）。
- (c) **双区域联合估计量构造为主** → Quant Finance / JFEc。

推荐 **(a)**——它是 Aionis 最独特、最难被竞争的工作（反泄漏纪律作为研究对象 + 真实 confirmatory 端到端演示），也最契合免费/快速的 CFR。

---

## 4. 推荐路径 + 强调映射

**主路径**：
1. **立即**：arXiv q-fin.ST preprint（用 `docs/methods-and-results-draft-en.md` v1.0-en 转 arXiv tex；建立时间戳 + 可引用）。
2. **正式投稿首选**：**Critical Finance Review** —— 框架 (a)，强调"反泄漏纪律作为研究对象 + power-floor 披露"，免费 + ~28 天 turnaround。
3. **备选**（若 CFR 拒或 framing 偏计量）：**Journal of Financial Econometrics**（框架 b，power-floor 作为计量方法论）或 **Review of Finance**（null 友好）。

**篇幅目标**（基于 v1.0-en 当前 ~3500 词正文 + 15 行证据表 + power analysis；arXiv 无限制）：
- CFR / RevFin：目标 **6000–8000 词**（full paper），证据表 + power analysis 入 appendix。
- JFEc：目标 **25–35 页**（计量方法惯例），强调 J-T 门构造 + power-floor 推导 + dual-region 估计量定理。
- 若选 **short note** 路径（仅 power-floor 定理 + confirmatory null）：**3000–4000 词**。

**v1.0 → venue 的强调/压缩映射**：
| v1.0 章节 | CFR/RevFin | JFEc | short note |
|---|---|---|---|
| §1 贡献（反泄漏纪律） | **lead** | brief | brief |
| §3 dual-region 联合折叠定理 | 中 | **lead** | 摘要 |
| §4 15 行 null 证据表 | 中（appendix） | 中 | 摘要 |
| §5 confirmatory climax | **lead** | 中 | 中 |
| §6 power-floor 定理 | **lead** | **lead** | **lead** |

---

## 5. 复用优先的投稿工具（权威来源）

- **arXiv**：官方 LaTeX 模板 https://arxiv.org/help/submit_tex （免费；docclass `article` + arxiv sty）。
- **Elsevier**（JFEc/JEF）：官方 `elsarticle.cls` https://www.elsevier.com/researcher/author/tools-and-resources/research-writing-tools （从 CTAN 或 Overleaf 模板获取）。
- **Overleaf**：官方模板库 https://www.overleaf.com/templates （含 Elsevier / T&F / arXiv；协作友好）。
- **T&F**（Quant Finance）：作者 LaTeX 模板见 https://authors.taylorandfrancis.com/ （引用风格见 `files.taylorandfrancis.com/ref_rquf.pdf`，已验证）。

> 验证：arXiv/Elsevier/Overleaf/T&F 模板入口为公开稳定 URL；具体 cls 版本以投稿时官方页为准。

---

## 6. 风险（诚实）

1. **中文 v1.0 → 英文**：英文 v1.0-en-draft 已落地（`docs/methods-and-results-draft-en.md`，数字与 ledger #49 交叉核对），但 venue-specific tailoring 待本 brief 落定后做一次强调调整。**非阻塞**。
2. **数据可用性（replication appendix）**：Aionis 的 PIT 数据是 **gitignored**（`data/`、`*.parquet` 不入库；含 Tiingo/Alpaca/EDGAR/FRED 真实数据 + 凭证）。大多数严肃 venue 要求 replication package。诚实路径：**config_committed ledger + frozen config sha256 + 全套 fetch 脚本**（可从公开源重建 bit-identical 结果，H6 保证）作为 replication 附录；原始数据按各源 ToS 不再分发（Tiingo/Alpaca 需用户自有 key）。**这是可发表的**（pre-registered + reproducible-by-construction），但需在 cover letter 诚实说明。
3. **CFR 选择性**：10-20 篇/年意味着 desk 拒概率不低；备选 JFEc/RevFin 作为并行/兜底。
4. **"no alpha" 先验**：即便 null 友好 venue，reviewer 仍可能问"so what's the contribution?"——必须在 intro 把"反泄漏纪律作为研究对象 + power-floor 定理"提升为**一等方法学贡献**，而非"我们试了，没用"。
5. **非投资建议**：保持 v1.0 §6 边界声明；不构成可交易策略。

---

## 7. 不越界声明（PROPOSED）

- `[F]` 本 brief 是决策文档；未写 ledger；未改 SESOI / look schedule / ADR / prereg / config。
- `[F]` venue 规格来自公开 web 检索；出版商精确页 403 处已诚实标注验证等级，未编造数字。
- `[I]` 业主决策待定：① 选哪条路径（CFR / JFEc / RevFin / 仅 arXiv）；② 是否授权 arXiv preprint 上传（外发，不可逆——需业主点头）；③ framing 选择（a 治理 / b 计量方法 / c 估计量）。
- `[I]` 独立性局限：positioning agent（sonnet）因 [1210] proxy 失败；本 brief 由 opus Orchestrator §8 fallback 直接起草（非独立 subagent pass）。数字（ledger #49 + power analysis）由既有独立审计背书（2026-08-05 power-analysis sonnet review + climax diff review 双 APPROVE）。
