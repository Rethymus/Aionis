# 业主门裁决请求包 — 2026-09-02（轮 55–57 接手验收收官）

> 本文件是三项不可代行裁决的正式请求包。每项附：现状证据、裁决将解锁什么、
> 建议的决策时点。工程侧已就绪并全部上远程（`314a57d2..b639c3a1`，13 commits）；
> 全套 pytest exit 0、ruff 全仓 0、账本六轮烟雾零写入（sha `91bc7640`，57 行）。

---

## 门 ① — E3 headline GO（roadmap P0-2：唯一不可代行）

**这是什么**：对 E3 前向积累的**首次非影子（真实账本）提交**点头。影子模式
（`PHASE_E3_NO_LEDGER=1`）只算不写；headline GO 解锁真实 `forward_prediction_committed`
账本行——不可逆。

**现状证据（全部一手）**：
- 2026-08-31 真实月末烟雾 **READINESS PASS 13/13**：223/223 事件带真实 EDGAR
  主文档原文 → 冻结 LightGBM fit → scores（config `1f4ca1b6`/scores `f29d0496`）；
  v6 重放双 sha **逐位一致**（确定性侧证）。日志存
  `reports/audits/2026-09-02-e3-smoke-*-*.log`。
- 结构性阻塞清零：membership 续造（124 月对账门 0 未解释）、面板 predict 截面、
  12 只覆盖缺口、429 自愈全部工程化消化。
- 尚无任何影子月账本（九月为第一个）。

**GO 解锁什么**：`e3-forward.yml` 按 workflow 头注三步启用（uncomment cron +
去掉 `PHASE_E3_NO_LEDGER=1`）；或继续手动通道。

**建议**：按 roadmap——**10 月末影子满 2 个月（9-30 + 10-31）后一并裁决**。
9-30 runbook 已武装：⓪`extend_membership_wikipedia.py` + `e3_extend_prices.py`
①volume ②materialize ③`e3_forward_trigger --run-date 2026-09-30`（NO-LEDGER）。

---

## 门 ② — P1 三项研究线的预注册级 GO

| # | 项目 | 地基已备 | GO 解锁 | 备注 |
|---|---|---|---|---|
| 4 | **Track A 因子生成器** | RD-01~17 任务单；AlphaAgent 三件套（原创性/对齐/复杂度）Aionis 化方案 | 新冻结面开发（trial registry 先注册后评估、haircut p 值判定） | 研究线新相位，需预注册 |
| 5 | **LLM vintage 纪律 CI 化** | probe v1 模板在案（GLM cutoff 2023-03-10 经验探针，冻结 YAML） | 探针套件定期化 + 模型卡 vintage 字段联动 | 防 LLM 回忆泄漏的长效机制 |
| 6 | **R1-full decile 收益单调性** | 冻结收益口径分析在案（R1-lite 分数面已上线） | 收益口径对齐工程 → 面板 + atlas 第五区块 | 金标准透镜，口径必须先对齐 |

**建议**：三项互相独立，可分别裁决；⑤与 9-30 窗口无耦合（cutoff 已钉）。

---

## 门 ③ — frozen_beta 行业符号表的一手出处（**含引用更正**）

**防幻觉发现（2026-09-02 一手核证）**：仓内原引用 "Boudt-Neely-Sercu, Fed WP
2017-020, Table 7" 的**编号是错的**——FEDS WP 2017-020 实为 Reifschneider &
Tulip《Gauging the Uncertainty of the Economic Outlook…》（官方 PDF 已抓取并
核对标题页，48 页，存 `runs/feds_2017_020.pdf`）。Crossref 可证的 2017 年
Boudt-Neely-Sercu(-Wauters) 合作论文主题是**跨国公司汇率敞口对宏观新闻的响应**，
并非行业级股票响应。当日学术搜索 API（WebSearch/Semantic Scholar/OpenAlex）
配额尽，未能在线定位真正的行业符号表一手论文。

**已做的更正**（趁 E3 账本零行的安全窗口）：
- `frozen_beta.py`：`FROZEN_BETA_SOURCE` 改为“待业主核证”表述（保留证伪语境），
  TODO(headline) 更新为指向业主一手来源；测试同步钉死。
- `docs/phase-e3-implementation-plan.md`：原行保留 + 追加日期更正注。

**需要您提供**：您所知的那篇 Boudt-Neely(-Sercu) 行业响应论文的**一手出处**
（题目/工作论文编号/链接）及其行业符号表（原称 Table 7）的数值/符号。收妥后：
符号入表 → `FROZEN_BETA_VERSION` 升版（绝不静默变更）→ TODO 移除。
在此之前现状是安全且如实的：`exploratory-v1-qualitative` 定性先验已随每个
forward config 记录在案。

---

## 附：接手验收以来的一手证据索引

| 主张 | 证据 |
|---|---|
| 测试/lint 基线 | 全套 pytest exit 0（多轮）、ruff 全仓 0（首次达成并保持） |
| E3 链全通 | `reports/audits/2026-09-02-e3-smoke-2026-08-31-readiness-pass.log`（v5）+ `-v6-ratelimit-selfheal.log` |
| membership 续造 | `reports/audits/2026-09-02-membership-gate-report.json`（124 月/281 分类/0 未解释） |
| 文本切片真实探针 | AAPL/MSFT 真 8-K 原文（`scripts/probe_edgar_primary_text.py`） |
| 零不可逆写入 | ledger sha `91bc7640`/57 行，v1–v6 六轮不变 |
| 视觉核查 | 仪表盘截图经视觉模型核验，四相 NULL 差分与 README 逐位一致 |
| 引用更正 | `runs/feds_2017_020.pdf`（官方原文）+ 上方 Crossref 记录 |
