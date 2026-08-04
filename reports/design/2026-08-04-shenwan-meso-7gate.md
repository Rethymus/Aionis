# 申万（SWFC）行业分类 meso 层 — 7-gate 核验报告

> 状态：**PROPOSED · 2026-08-04 · opus 会话内完成（Lane A agent 死于 [1210]，orchestrator 直接接手）**。
> 结论先行：**CN 申万 meso via baostock = G3 不可证 → 快照冻结 + exploratory-only，不进 confirmatory headline**（与 cninfo 基本面 #47、EPU 同处置）。confirmatory meso 层 = **US-only（SIC，EDGAR 公共域 PIT）**。
>
> 关联：[`data-intake-rubric.md`](../../docs/data-intake-rubric.md)、[`track-c-preregistration.md`](../../docs/track-c-preregistration.md) §1.1（meso 定义）、`src/aionis/features/regime_meso.py`（现有 fetch 实现）、`reports/2026-08-03-qlib-dualregion-poc.md` §3 证据⑤（baostock 基本面 G3 结构性失败先例）。

---

## 0. 任务背景

Track C `regime_state` 三层复合的 **meso 层**（`track-c-preregistration.md` §1.1）定义为「美股 SIC-peer 动量 + A 股申万（SWFC）行业动量，等权」。当前实现（`regime_meso.py`）的 meso 是 **US-only**（`enable_cn_fetch=False` 默认）。本核验回答：**baostock 的申万行业分类能否进 confirmatory headline 的 meso 层？**

**关键先例**：baostock **基本面**（`query_profit`/`query_balance_data`）已被 **G3-reject**（期末键、无 as-of/vintage → 结构性不可合规；见 qlib POC §3 证据⑤）。本核验判定 **行业分类** 是否有**同样的 G3 失败**。

---

## 1. baostock 申万分类的 API 实情（基于代码 + 文档）

现有 fetch（`regime_meso.py:123-137`）：
```python
rs = bs.query_stock_industry(ticker)
while rs.next():
    industry = rs.get_row_data()[1]  # column 1 = industry name
    break
```

观察：
- `bs.query_stock_industry(code)` **无 date 参数**——返回单条分类（最新），不按 as-of 日期检索历史。
- 返回字段含 `code / code_name / industry / industryClassification / updateDate`。现有代码只取 `industry`（column 1），**忽略** `industryClassification`（SWFC 版本：2014/2021）与 `updateDate`。
- baostock **不提供** per-stock 的历史改分类序列（无 vintage API；`updateDate` 是该分类的录入日，非逐日历史）。

⚠ **API 不确定性（诚实声明）**：baostock 是否允许按 `industryClassification` 选版本（SWFC-2014 vs SWFC-2021）查询，本报告**基于文档/代码推理，未做活拉取实证**（Lane A agent 被指派做此核验但死于 [1210]）。即便可按版本查询，那也只是**版本选择**，**非 as-of 日期**——版本内某股 2019 年从「银行」改「综合」仍会被回填。故 G3 判定**不依赖**此不确定性的解决（见 §G3）。

---

## 2. 逐门核验

### G1 — License（许可）
baostock = **MIT**（项目 `data-license-allowlist.md` 已含；`regime_meso.py` docstring 明示 MIT）。
→ **PASS** ✓

### G2 — PIT / as-of 时点
申万分类在分类日**原则可知**（SWFC 公告），但 baostock `query_stock_industry` **不暴露 as-of 检索**（无 date 参数，返回最新值）。无法构造「t 时刻可知」的分类序列——等同 rubric G2 失败例「某指数 provider 无 vintage 声明，只给一条现值序列」。
→ **CONDITIONAL/FAIL**（无 as-of 检索；可快照但非 PIT-correct）

### G3 — No-revision（无回改——**杀手级**）
申万分类**已被回改**：SWFC-2014 → SWFC-2021 两个版本（2021 大规模重分类）；版本内单股偶发改分类。baostock 把**当前分类回填到全历史**，无 vintage/版本-日期 API。→ SWFC-2021 边界前的数据被 2021 分类污染（某股 pre-2021 标成 2021 后属行业）。
→ **FAIL**（与 EPU、baostock-基本面同类结构性失败；rubric 判定矩阵：G3 不可证 → 快照冻结 + exploratory）

**与基本面 G3 的严重度对比（重要）**：
- 基本面：**每季**改 → 回填污染重。
- 行业分类：**年间**改（版本级）+ 偶发单股 → 回填污染**较轻**但**非零**且在 SWFC 边界系统性发生。
- 对 meso regime（市场级日序列）的影响：单股误分类只轻微扰动该 sector 动量；市场级 meso 影响小但**系统性**存在于 SWFC 边界。→ 即便污染轻，**G3 仍 fail**（rubric 是 binary：回改即 fail，不论幅度）。

### G4 — Reproducibility / snapshot
现有 `_fetch_shenwan_sector_for_tickers` 已 per-ticker JSON cache + 可 sha256。快照可行。
→ **PASS** ✓（冻结当前 map + sha256 = 可复现）

### G5 — Exploratory-only
G3 fail → 按矩阵**强制 exploratory-only**，不进 headline。
→ **PASS**（条件性：须标 `mode: exploratory`）

### G6 — Selection / survivorship honesty
行业分类有**幸存者偏差**（退市股可能缺分类；baostock 历史含部分退市但不全）+ SWFC 回填限制。须声明为 scope 限制，非 ground truth。
→ **PASS**（条件性：须声明 scope）

### G7 — Politeness / ToS
现有 `_BAOSTOCK_PAUSE = 2.0`（`regime_meso.py:42`）+ `finally: bs.logout()`（line 161-165）。符合 ≥2s。
→ **PASS** ✓

---

## 3. Headline-eligibility 裁定

| 门 | 裁定 |
|---|---|
| G1 license | ✓ PASS |
| G2 PIT | ✗ CONDITIONAL/FAIL（无 as-of 检索） |
| **G3 no-revision** | **✗ FAIL（结构性，与基本面同类）** |
| G4 snapshot | ✓ PASS |
| G5 exploratory | ✓ PASS（强制 exploratory） |
| G6 honesty | ✓ PASS（须声明） |
| G7 politeness | ✓ PASS |

**rubric 判定矩阵**：G1 + G2 过 + **G3 不可证** → **快照冻结 + exploratory-only**。

### 结论
**CN 申万 meso via baostock 不得进 confirmatory headline。** 处置 = **快照冻结（SWFC-2021 当前 map + sha256）+ `mode: exploratory`**，作 meso 层的探索性诊断。这与 cninfo 基本面（#47 → exploratory）、EPU（G3 → exploratory）同构——A 股特有的、无法过 G3 的第三方源，一律降 exploratory，claim 收窄到 US 侧。

---

## 4. 对 Track C spec 的影响（confirmatory meso = US-only）

**spec §1.1 的 meso 定义需修订**（= 新 ledger 行，owner 动作）：

| 项 | 原 §1.1（PROPOSED） | 修订（confirmatory） |
|---|---|---|
| meso 层 | US SIC-peer + CN 申万，等权 | **US SIC-peer only（EDGAR 公共域 PIT）** |
| CN 申万 | headline | **exploratory-only**（快照 + sha256，作诊断层） |

**重要**：这**正好是当前实现的状态**（`regime_meso.py` 默认 `enable_cn_fetch=False` → meso = US-only）。故本裁定 = **正式化现有状态为 spec-faithful confirmatory config**，而非新方向。

**对 conditional-IC 的影响**：本会话早先的「3-layer（US-only meso）双区 conditional-IC null」结果**就是 spec-faithful 的 exploratory 结果**（β_US=-0.001 p=0.95；β_CN=+0.015 p=0.36，均 null）。confirmatory 跑用同一 US-only-meso composite——不需为 CN meso 重做 regime。

---

## 5. 缓解选项（若 owner 想让 CN 申万进 headline）

1. **Tushare `industry`（含 `ann_date`）**——付费/ToS，G1 需核；非 permissive-default。
2. **Wind / iFinD**——商业付费，禁入。
3. **自建申万 PIT**：从 [swsindex.com](http://www.swsindex.com) 或 cninfo 抓历史调整公告，按公告日重建 as-of 序列。**高成本**（反爬 + 调整公告解析）；类比 `index-constitution` 重建 CSI300 成分的方式，可行但工作量大。
4. **冻结单版本快照**（SWFC-2021 当前 map）——可复现但**非 PIT-correct**（pre-2021 仍污染）→ 只能 exploratory。

**推荐**：**不投入缓解**。null-favored + 现有 US-only-meso 已出双区 null → CN 申万 headline 化的边际证据价值低、成本高。confirmatory 用 US-only-meso，CN 申万留 exploratory 诊断。

---

## 6. 待 owner-gated 的活拉取实证（可选，非阻塞）

本报告 G3 判定基于文档/代码推理（足够下 exploratory 裁定）。若 owner 想把裁定升格为"实证确认"，最小活检查（`ENABLE_CN_FETCH=1` + baostock，~10min）：
- 取一只已知在 SWFC-2021 重分类的股票（如某股 2014 版属「化工」、2021 版改「新材料」）；
- 查 baostock `query_stock_industry` 返回的 `industryClassification` 字段 + 是否支持按版本/日期查询；
- 若返回的 pre-2021 历史 = 当前分类 → 实证确认 G3 fail。若 baostock 意外支持 as-of → 升格裁定（低概率）。

**不阻塞**：当前裁定（exploratory-only）是 fail-safe 保守处置，与实证结果一致或更严。

---

## 7. 不越界声明

- `[F]` 本报告是研究/裁定文档；未活拉取 baostock 数据；未写 ledger；未触冻结面/prereg/ADR。
- `[F]` 裁定 = recommend CN 申万 meso 降 exploratory；**正式化**需 owner 在新 ledger 行修订 spec §1.1（meso = US-only for confirmatory）。
- `[I]` Lane A sonnet agent 死于 [1210] proxy；本报告由 orchestrator（opus）直接完成，非独立 agent 产物——独立性局限已声明（裁定基于文档/代码推理，保守 fail-safe）。
