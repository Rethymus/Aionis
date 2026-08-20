# A 股价格数据接入评估 — baostock（PROPOSED）

> **状态**：PROPOSED · 2026-08-04 · Track C S0 数据构造前门评估  
> **范围**：A 股日线价格 via baostock（`baostock` PyPI 包）  
> **关联**：[`track-c-preregistration.md`](track-c-preregistration.md) §3 ①、[`data-intake-rubric.md`](data-intake-rubric.md)、[`reports/2026-08-03-qlib-dualregion-poc.md`](../reports/2026-08-03-qlib-dualregion-poc.md)、[`data-license-allowlist.md`](data-license-allowlist.md)

---

## 0. 裁决摘要（7 门 verdict）

| 门 | 结论 | 关键证据 |
|---|---|---|
| **G1 许可协议** | **PASS** | PyPI `baostock` = **BSD**（2026-08-20 复核：直接下载官方 sdist/wheel 验证 setup.py 与 METADATA 一致；早先引用的 GitHub `baidstock/bs_stock` 已 404 不存在，予以更正——见 docs/data-intake-baostock-industry.md §G1）；在 ALLOWED 列 |
| **G2 PIT 时点** | **PASS** | 交易所固定收盘价 → 交易日期自然对齐；pandas-market-calendars XSHG/XSHE 交易日历 |
| **G3 无回改契约** | **CONDITIONAL** | 原始价格交易所固定（低风险），但 `adjustflag` 复权因子可追溯修订 → 需冻结策略 |
| **G4 快照+sha256** | **PASS** | 首次获取即落 `data/cache/` + sha256 pinning；复权因子快照隔离 |
| **G5 探索性 vs headline** | **PASS（headline）** | Track C 价格是 headline 输入（非探索性） |
| **G6 幸存者诚实** | **PASS** | `query_all_stock` 含历史退市；`tradestatus` 停牌→NaN；涨跌停距可算 |
| **G7 礼貌** | **PASS** | ≥2s 请求间距（免费公开 API；无显式速率限制声明但保守合规） |

**总体判定**：**通过（带 G3 缓解）** —— 可入 Track C headline，需冻结复权因子快照 + sha256。

---

## G1 — License（许可协议）

### 规则
仅 MIT / Apache-2.0 / BSD-2/3-Clause / CC0 / CC-BY-4.0（数据）。拒绝 Commons-Clause / GPL / AGPL / LGPL。

### 证据
- **PyPI 包**：`baostock==0.9.3`（2024-12 维护停止，但包仍可用）
- **License 声明**：PyPI 分发元数据 `License: BSD License`（sdist setup.py 与 wheel METADATA 双验）；早期记录的 GitHub `baidstock/bs_stock` MIT 引用有误（repo 不存在），2026-08-20 更正为 BSD
- **ALLOWED 核对**：MIT 在 [`data-license-allowlist.md`](data-license-allowlist.md) §ACCEPTED 列

### Verdict
**PASS（无争议）** —— baostock 包本身是 MIT，符合 G1 要求。

---

## G2 — PIT / as-of 时点

### 规则
每个观测带「当时可知」timestamp；t 时刻的值不得依赖 >t 的信息。对价格数据 = 交易日期对齐。

### 证据
- **交易所固定价格**：A 股 OHLCV 收盘价 = 交易所当日收盘时确定，次日公布即 PIT（非美式的 period-end 报告延迟）
- **API 返回字段**：`query_history_k_data_plus` 返回 `date`（交易日 `YYYY-MM-DD`）、`open/high/low/close/volume`、`tradestatus`（停牌标记）
- **交易日历隔离**：需 `pandas-market-calendars` XSHG（沪）/ XSHE（深）交易日历，月末日截面采样（与美股 NYSE 隔离但并行）
- **复用模式**：与 `src/aionis/ingest/market.py` Tiingo/Alpaca 模式一致 —— 每次按交易日拉取，按区域日历对齐

### Verdict
**PASS（低风险）** —— 价格是交易所固定事实，无「报告日 vs 期末」的 PIT 错位问题。

---

## G3 — No-revision contract（无回改契约）⚠️

### 规则
Provider **不得**追溯重算历史。若不可证：首次接入即**快照 + sha256 = 冻结真相**；之后修订 = **新版本 = 新 ledger 行**。

### 证据（关键门）

#### 3.1 原始价格（PASS）
- **交易所固定**：当日 OHLCV = 交易所成交事实，事后不会修改（与 EDGAR filed-date 事实同等级）
- **`qlib-dualregion-poc.md` §2.5 确认**：价格是「exchange-fixed → G3 低风险」（与基本面 period-end 键的结构性失败无关）

#### 3.2 复权因子 `adjustflag`（CONDITIONAL）⚠️
- **API 参数**：`query_history_k_data_plus(fields="...", adjustflag="2")` 其中 `adjustflag`：
  - `"1"` = 前复权（forward-adjusted，基于最新除权事件）
  - `"2"` = 后复权（backward-adjusted）
  - `"3"` = 不复权（raw price）
- **风险机制**：**前复权因子可追溯修订** —— 当公司新除权时，历史序列的复权因子会被重算（与美股 splits/dividends 同理）
- **类比美股**：Tiingo `adjClose` / Alpaca `adjustment='all'` 也有前复权风险，Aionis 通过「首次拉取即冻结快照」缓解（见 `market.py:1-10` 注释 "Always returns *adjusted* close... Every fetch is validated against the NYSE calendar"）

#### 3.3 缓解策略（冻结机制）
**方案 A（推荐）**：首次拉取时，冻结 `adjustflag` 快照：
1. 拉取 `adjustflag="3"`（不复权 raw price）+ 原始除权事件序列
2. 在本地**一次性**计算复权因子（快照时间戳 t₀）
3. 快照入 `data/cache/ashare_price_adjustment_{date}.parquet` + sha256
4. 之后复算 = 新版本 = 新 ledger 行（绝不用最新因子重算历史）

**方案 B（备选）**：直接拉取 `adjustflag="1"`（前复权），但：
1. 首次拉取即冻结全序列快照（`data/cache/ashare_price_adjusted_{start}_{end}.parquet`）
2. 记录拉取时间戳 + baostock 版本
3. 后续发现序列变化 = **立即告警 + 新 ledger 行**（不静默覆盖）

**方案 C（保守）**：用 raw price（`adjustflag="3"`）+ 本地因子库（如 `qlib` 的 adjust 模块），完全本地化复权逻辑。

### Verdict
**CONDITIONAL（需缓解）** —— 原始价格 PASS，但复权因子需冻结策略。推荐 **方案 A**（raw + 本地因子快照）或 **方案 B**（前复权快照）。

---

## G4 — Reproducibility / snapshot discipline

### 规则
第三方接入是冻结产物 —— ledger 记录 data-sha256 + as-of + source-URL + fetch-ts；rerun 零 HTTP。

### 证据
- **复用架构**：与 `ingest/market.py` 一致 —— 首次拉取落 `data/cache/ashare_price_{start}_{end}.parquet`
- **sha256 pinning**：`runs/ledger.jsonl` 记录 `data_sha256`（同 `CONTRIBUTING.md` §2）
- **版本声明**：baostock `0.9.3`（PyPI 版本 pinning，`uv.lock` 冻结）
- **复权因子隔离**（G3 方案 A）：`data/cache/ashare_adjustment_factors_{snapshot_date}.parquet` 独立快照

### Verdict
**PASS** —— 架构与美股侧一致，快照 + sha256 落地机制成熟。

---

## G5 — Exploratory-only vs headline

### 规则
未通过 G2+G3 PIT 验证的 = **EXPLORATORY ONLY**；通过后可入 confirmatory headline。

### 证据
- **Track C spec**：[`track-c-preregistration.md`](track-c-preregistration.md) §3 ① 明示价格是 headline 输入（`cn_price_12` 字段）
- **G2+G3 状态**：G2 PASS（交易日期对齐），G3 CONDITIONAL（原始价格 PASS，复权因子需冻结）
- **对比基本面**：A 股基本面因 G1/G7 已降 exploratory（见 [`ashare-fundamentals-source.md`](../reports/design/2026-08-03-ashare-fundamentals-source.md) §3），但 **价格不是基本面** —— 价格是交易所固定事实，无爬虫/授权问题

### Verdict
**PASS（headline 入格）** —— 价格数据满足 headline 条件（G2 PASS + G3 原始价格 PASS + 复权因子冻结策略）。

---

## G6 — Selection / survivorship honesty

### 规则
声明 selection bias；幸存者偏差用 PIT 成分缓解；停牌→NaN；不当 today-snapshot。

### 证据
- **`query_all_stock()`**：baostock API 返回**历史全量股票**（含已退市），非今日快照
- **`tradestatus` 字段**：停牌返回 `"停牌"` → 代码中转为 `NaN`（与美股 Tiingo/Alpaca 缺失值一致）
- **涨跌停处理**：A 股特有 —— 可算 `limit_up_down_distance = (close - prev_close) / prev_close`，当日触及±10%/±20% → 标记 `is_limit_up/down`
- **PIT 成分**：用 `index-constitution` MIT 包的 CSI 300/500 历史成分（`track-c-preregistration.md` §2），非今日 500

### Verdict
**PASS** —— 幸存者偏差通过历史成分 + 停牌缺失化缓解；selection bias 明确声明（headline = 保守上界）。

---

## G7 — Politeness / ToS

### 规则
限速、≥2s 间距、遵守 robots.txt、用描述性 User-Agent。

### 证据
- **baostock.com 公开声明**：免费 API，无显式 RPM/TPM 限制（但需登录 `bs.login()`）
- **保守策略**：符号间 ≥2s 间距（复用 `ingest/http_policy.py` 指数退避）
- **User-Agent**：`aionis/0.1`（与美股侧一致，`market.py:36/79`）
- **登录会话**：`bs.login()` + `bs.logout()` 包裹；session 失效指数退避（与 EDGAR 一致）

### Verdict
**PASS** —— 免费公开 API，≥2s 间距保守合规（无反向工程，无批量爬）

---

## 与基本面源 baostock 的关键区别

| 维度 | **基本面（PROCESSED, 已拒）** | **价格（本评估, PASS）** |
|---|---|---|
| **API** | `query_profit_data(year, quarter)` | `query_history_k_data_plus(date, adjustflag)` |
| **时间键** | **期末键**（无 filed-date） | **交易日键**（交易所固定） |
| **G3 风险** | **结构性失败**（无 as-of 机制） | 原始价格 PASS；复权因子需冻结 |
| **Track C 用途** | **exploratory-only**（`ashare-fundamentals-source.md` §3） | **headline 输入**（§3 ① `cn_price_12`） |

**结论**：价格 ≠ 基本面；基本面拒 ≠ 价格拒。价格是交易所固定事实，PIT-safe。

---

## 实施路径（S0 数据构造）

### 阶段 1：首次拉取（快照冻结）
1. **登录**：`bs.login()`（用户注册 `https://baostock.com/register`）
2. **股票列表**：`query_all_stock()` → 历史全量 + 退市标记
3. **价格拉取**：按 CSI 300/500 PIT 成分（`index-constitution`），逐符号 `query_history_k_data_plus(fields="date,open,high,low,close,volume,tradestatus", adjustflag="3")`（raw price，避免前复权回改）
4. **复权因子**：同步拉取除权事件序列（`baostock` 未直接提供，可能用 `qlib` 的 adjust 模块或本地计算）
5. **快照落盘**：`data/cache/ashare_price_{start}_{end}.parquet` + `data/cache/ashare_adjustment_factors_{snapshot_date}.parquet`
6. **sha256 记录**：入 `runs/ledger.jsonl`（新行，S0 数据构造标记）

### 阶段 2：复用
- rerun 从 `data/cache/` 读，零 HTTP（与美股 `market.py` 一致）
- 如复权因子修订 → **新 ledger 行**（不覆盖历史）

### 与美股侧对称性
- **美股**：Tiingo（首选）+ Alpaca（备选），`adjClose` 前复权 + 快照冻结
- **A 股**：baostock 单源，raw price + 本地复权因子快照
- **架构复用**：`src/aionis/ingest/ashare_price.py` 镜像 `market.py` 结构

---

## 待 owner 裁断（冻结前）

1. **G3 复权因子策略**：方案 A（raw + 本地因子） vs B（前复权快照） vs C（完全本地化）
2. **历史深度**：baostock 可用范围（1990+？）决定 A 股 headline 窗起点
3. **A 股交易日历**：`pandas-market-calendars` XSHG/XSHE 验证 + 与美股 NYSE 并行对齐
4. **CSI 300/500 PIT 成分**：`index-constitution` MIT 包的 7-gate（见 `track-c-preregistration.md` §2）

---

## 不越界声明

- **PROPOSED 评估**；未触任何冻结面（`docs/track-c-preregistration.md`、`runs/ledger.jsonl`、`decisions/*`、`config/`）
- **未连 baostock.com**；未拉真实数据；未跑 `scripts/track_c_amend1.py`
- **7-gate 评估**：复用 [`data-intake-rubric.md`](data-intake-rubric.md)、[`data-license-allowlist.md`](data-license-allowlist.md)、[`qlib-dualregion-poc.md`](../reports/2026-08-03-qlib-dualregion-poc.md) 证据
- **实施前**：须 owner 批准 G3 缓解策略 + 历史深度 + CSI 300/500 PIT 成分 intake

---

## 快照记录（2026-08-04 首次真实拉取）

Owner 授权后首次 S0 真实拉取。`baostock==0.9.3`（PyPI MIT），lazy-import（**非 core dep**：`uv add` 临时激活 → 拉取 → `uv remove` 复原；pyproject/uv.lock 净零）。脚本 `scripts/ashare_price_fetch_csi300.py`（单 login、逐 ticker try/except 隔离、≥2s 礼貌、停牌 NaN）。

- **产物**：`data/cache/ashare_prices_csi300.parquet`（gitignored；37.5 MB；2,578,783 行）
- **sha256**：`a461487604b27aaa20be4400a445ccb20ba598e64573c4308618044b3ecb2562`（记于本 doc；**不入 ledger**——S0 数据快照非 `config_committed`，按 Track C 冻结后 S0 规则不写新 ledger 行）
- **覆盖**：2014-01-02 .. 2026-08-03（2yr 回看，供 252d 特征）；929 tickers 有数据
- **survivorship + 覆盖核验**：949 CSI300 历史成分中 20 个返回空（`sh.600001/2/3`、`sz.000406` 等 = **2016 前-only 成员**，Track C 2016+ 窗口 **0 覆盖缺口**）→ 2016-2026 全部 CSI300 成员均有价格数据 ✅
- **G6 停牌**：68,201 个停牌日 OHLCV 正确置 NaN（`tradestatus != "1"`）
- **G3**：`adjustflag="3"` raw（方案 A，冻结本地快照）；0 失败；≥2s 间距
- **复现**：`uv add baostock && uv run python scripts/ashare_price_fetch_csi300.py` → 同源应重算得同一 sha256（H6；raw 价交易所固定，低回改风险）

> 注：上方「阶段 1 §sha256 入 ledger」「待 owner 裁断」「不越界声明（未拉真实数据）」为本快照前的 PROPOSED 状态；本快照以实际拉取结果为准（owner 已授权；G3=raw 已冻结为默认）。

---

## 引用

- 内部：[`track-c-preregistration.md`](track-c-preregistration.md)、[`data-intake-rubric.md`](data-intake-rubric.md)、[`data-license-allowlist.md`](data-license-allowlist.md)、[`reports/2026-08-03-qlib-dualregion-poc.md`](../reports/2026-08-03-qlib-dualregion-poc.md)、[`reports/design/2026-08-03-ashare-fundamentals-source.md`](../reports/design/2026-08-03-ashare-fundamentals-source.md)
- 外部：`baostock` PyPI MIT、`index-constitution` PyPI MIT、pandas-market-calendars
- 架构：`src/aionis/ingest/market.py`（Tiingo/Alpaca 模板）
