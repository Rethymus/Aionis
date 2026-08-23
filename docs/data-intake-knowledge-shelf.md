# 数据接入 7 门 — 方法书架（knowledge_shelf / /shelf 面板）

> **状态**：**v0.1 · 2026-08-23** · reference 显示模块（业主废除豁免后的小隐寺"书架"等价物）。
> **范围**：本面板通过 7 门强制清单（`docs/data-intake-rubric.md`）。与其它面板不同，本面板
> **自有内容层零第三方版权面**（全部为仓库 MIT 自有文档的目录）；外链层为**编辑精选书签**
> （只链出 + 一句静态描述，不抓取）。
> **等价物立场**：小隐寺"书架"= 其自有投研内容产品；Aionis 的等价物不做内容盗用，做
> **Aionis 方法书架**——自有方法资产的可浏览目录 + 公共域一手研究源的链出目录。

---

## 数据源概述

**两层结构**：

1. **自有文档层（核心，零版权问题）**：`scripts/export_terminal_data.py::export_knowledge_shelf()`
   在**导出时静态读取**仓库 `docs/*.md`（53 篇）与 `decisions/*.md`（13 篇，12 ADR + 索引），
   提取元数据 + 首段摘要进 `web/src/data/aionis/knowledge_shelf.json`：标题（首个 `#` 行）/
   仓库相对路径 / 分类 / 最后提交日期（本地 `git log -1`）/ 字符数 / 首 2-3 句摘要
   （safe slice，硬上限 240 字符）。**内容本体不搬运**——每条目外链 GitHub 页面阅读。
   分类为固定 5 轨白名单：`preregistration` / `adr` / `results` / `rubric` / `theory`。
2. **公共域研究链出层**：固定 ~8 项**编辑精选**一手研究源书签（BIS working papers、Fed FEDS、
   IMF WP、NBER 摘要页、arXiv q-fin、FRASER、FRED/ALFRED、RePEc/IDEAS），冻结为导出器内的
   字面量（`_KS_RESEARCH_SOURCES`）：**只链出 + 一句静态双语描述**，不抓内容、不调摘要 API。

**web 构建环境无仓库文件**——所以面板必须在导出时自带目录（构建时静态读取，非运行时 fs 访问）。

---

## G1 — License allowlist（许可协议白名单）

### 结论：✓ **PASS（自有内容 = repo MIT；外链层 = editorial）**

- **规则**：仅 MIT / Apache-2.0 / BSD-2/3-Clause / CC0 / CC-BY-4.0（数据）或等价的开放数据。
- **自有层**：`docs/` + `decisions/` 是仓库自有内容（repo MIT）——目录化自己的文档**零第三方
  版权面**；摘要 slice 是自有内容的导航片段（≤240 字符，远超 fair-use 门槛，且本来就是我们
  自己的 MIT 文本）。
- **外链层（诚实边界）**：第三方研究内容版权在作者/机构——我们**只做目录**（名称 + 一句静态
  描述 + 链出），与 news_feed 面板"文章正文留在出版商处"同一立场。**绝不请求/爬取
  data.xiaoyinsi.com**（本项目铁律）；也绝不复制第三方论文内容或摘要 API 输出。

---

## G2 — PIT / as-of 时点（point-in-time）

### 结论：✓ **PASS**

- **机制**：每条文档日期 = 该文件**最后一次提交日期**（本地 `git log -1 --format=%cI`，取
  YYYY-MM-DD）；面板 `as_of` = 全部收录文档中的最新提交日期。文档目录随仓库提交演进——
  快照即时点，无"今天的目录覆盖昨天的 docs"错配。
- **实现**：`_ks_git_date()` 本地 git 查询失败时诚实置 null（绝不用 mtime 冒充——checkout 会
  重置 mtime，不可作 PIT 锚）。另带 `snapshot_ts`（`_stamp`）。

---

## G3 — No-revision contract（无回改契约）

### 结论：✓ **PASS（带如实披露）**

- **机制**：git 历史本身是不可变账本——同一 commit 上重跑导出，目录与日期**比特一致**（确定性
  排序：分类轨序 + 路径字典序）。文档被修订 = 新 commit = 新日期，历史不被改写。
- **披露**：若某文档经 `git revert` / rebase 改写历史，其"最后提交日期"随之变化——这是 git
  语义的如实反映，面板不做额外缝合。

---

## G4 — Reproducibility / snapshot discipline（可复现）

### 结论：✓ **PASS**

- 导出 = 纯本地文件扫描（`docs/` + `decisions/`）+ 本地 git 查询；**零网络请求**（无 fetch、
  无 API、无 RSS 拉取——BIS 的 RSS 只作为链出目标，不抓取）。
- 解析（`_ks_title` / `_ks_summary` / `_ks_classify` / `_ks_clean_line`）全为纯函数，
  hermetic 测试锁定（`tests/test_knowledge_shelf_panel_contract.py`，fixture 手写且显式标注）。
- 面板缺源时走 `_safe_export` FileNotFoundError 约定（fresh checkout 上 `docs/` 永远在，
  此为防御性一致）。

---

## G5 — Exploratory-only 边界

### 结论：✓ **PASS**

- **display-only / reference 车道**：仅进终端 `/shelf` 面板与静态数据 API（`knowledge_shelf.json`）。
- **绝不进研究管线**（features/eval/ingest/extraction of research data/OOS）；无 frozen claim
  依赖此数据。书架是给人读的方法目录，不是模型的特征源。

---

## G6 — Selection honesty（选择诚实）

### 结论：✓ **PASS（范围如实声明）**

- **自有层无 cherry-pick**：扫描 `docs/` + `decisions/` 下**全部** .md（66 篇全收，无手工挑选）；
  分类是机械规则（文件名/目录 → 5 轨白名单），不是编辑评级。
- **外链层是显式编辑精选**：~8 项固定书签在 methodology 与面板 UI 中**明示 editorial curation**
  ——选择标准（一手公共域研究发布处）写进描述；列表冻结在导出器字面量里，改动 = 新 commit。
- 覆盖偏差如实声明：只收仓库顶层 docs/ 与 decisions/（不含 tasks/、reports/、evals/ 等操作
  目录）；theory 轨是方法/理论/intake 评估的混合收纳轨，标签如实（"理论与方法"）。

---

## G7 — Politeness / rate limit（礼貌抓取）

### 结论：✓ **PASS（零网络 = 无需限速）**

- 本面板**零网络请求**：自有层是本地文件 + 本地 git；外链层是静态书签（浏览器端链出，
  服务端无请求）。无 host 可限速——礼貌性由构造保证。
- 渲染端外链一律 `target="_blank" rel="noopener noreferrer"`。

---

## 结论

**7/7 PASS（G1 自有 MIT + 外链 editorial 目录；G7 零网络由构造成立）** — 准入为
**display-only / reference**。违反任一门（如开始抓取外链源内容、把书架数据接进研究管线、
或请求 data.xiaoyinsi.com）即失效。
