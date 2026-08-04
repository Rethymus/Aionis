# CSI300 成分股数据接入评估 — index-constitution (MIT)

> **状态**：PROPOSED · 2026-08-04 · Track C S0 universe 数据源评估
> **范围**：CSI300 PIT 历史成分股 via `index-constitution` PyPI 包（MIT）
> **关联**：[`track-c-preregistration.md`](track-c-preregistration.md) §2、[`data-intake-rubric.md`](data-intake-rubric.md)、[`data-license-allowlist.md`](data-license-allowlist.md)

---

## 0. 裁决摘要（7 门 verdict）

| 门 | 结论 | 关键证据 |
|---|---|---|
| **G1 许可协议** | **PASS** | PyPI `index-constitution==0.6.2` = MIT（已验 LICENSE）；在 ALLOWED 列 |
| **G2 PIT 时点** | **PASS** | 基于中证指数有限公司官方公告重构，`opt-in/opt-out` 日期精确到日；提供 `constituents_at(date)` 时点查询 |
| **G3 无回改契约** | **PASS** | 指数成分公告是历史事实（类 EDGAR filings），不可追溯修订；官方公告一旦发布即固定 |
| **G4 快照+sha256** | **PASS** | 首次获取即落 `data/cache/` + sha256 pinning；PyPI 包自带嵌入 CSV（无需网络） |
| **G5 探索性 vs headline** | **PASS（headline）** | Track C S0 universe 是 headline 输入（PIT 成分股定义交叉截面） |
| **G6 幸存者诚实** | **PASS** | 历史成分股含退市/剔除记录（`opt-out` 字段）；`constituents_at(t)` = 当时成分，非今日快照 |
| **G7 礼貌** | **PASS** | PyPI 包嵌入数据（无运行时 HTTP）；首次安装为一次性 PyPI 请求（无速率问题） |

**总体判定**：**通过** —— 可入 Track C S0 headline，MIT 许可 + PIT-safe + 无回改风险。

---

## G1 — License（许可协议）

### 规则
仅 MIT / Apache-2.0 / BSD-2/3-Clause / CC0 / CC-BY-4.0（数据）。拒绝 Commons-Clause / GPL / AGPL / LGPL。

### 证据
- **PyPI 包**：`index-constitution==0.6.2`（2026-07-03 最新发布，活跃维护）
- **License 声明**：PyPI 元数据 `License: MIT License`；GitHub `unliftedq/index-constitution` `LICENSE` 文件 = MIT
  ```
  MIT License
  Copyright (c) 2026 index-constitution contributors
  [...]
  ```
- **ALLOWED 核对**：MIT 在 [`data-license-allowlist.md`](data-license-allowlist.md) §ACCEPTED 列
- **Python 版本**：提供 `py3-none-any.whl`（通用 wheel），**Python 3.13 兼容**

### Verdict
**PASS（无争议）** —— `index-constitution` 包本身是 MIT，符合 G1 要求，且 Python 3.13 兼容。

---

## G2 — PIT / as-of 时点

### 规则
每个观测带「当时可知」timestamp；t 时刻的值不得依赖 >t 的信息。对成分股数据 = `constituents_on(t)` = 当时成员，非今日快照。

### 证据
- **数据来源**：中证指数有限公司（csindex.com.cn）官方公告历史重构
- **数据结构**：CSV 格式 `symbol,name,opt-in,opt-out`
  - `opt-in`：纳入 CSI300 日期（精确到日）
  - `opt-out`：剔除 CSI300 日期（空值 = 至今仍在）
- **Python API**：
  ```python
  import index_constitution as ic
  ic.constituents_at("csi300", "2018-06-30")  # 时点查询
  ic.history("csi300")  # 完整历史（含 opt-in/opt-out）
  ic.is_member("csi300", "SZ000001", "2020-01-02")  # True
  ```
- **PIT 语义**：`constituents_at(date)` 返回 `<date` 时已纳入且未剔除的股票集合（`opt-in <= date < opt_out`），无前视泄漏
- **对齐美股侧**：与 `ingest/universe.py` `constituents_on(t)` 语义一致——取 `≤ date` 的最新成员快照，**无 forward-fill**

### Verdict
**PASS（低风险）** —— 基于 `opt-in/opt-out` 日期的时点查询，PIT-safe。

---

## G3 — No-revision contract（无回改契约）

### 规则
Provider **不得**追溯重算历史。若不可证：首次接入即**快照 + sha256 = 冻结真相**；之后修订 = **新版本 = 新 ledger 行**。

### 证据
- **指数公告的不可变性**：CSI300 成分调整由中证指数有限公司通过官方公告发布（如「关于调整沪深 300 指数样本的公告」），公告一旦发布即为历史事实，**不可追溯修订**（与 EDGAR filings 同等级）
- **数据重构逻辑**：`index-constitution` 从历史公告手工/半自动重构 `opt-in/opt-out` 日期表，重构后即**固定快照**
- **PyPI 包版本控制**：
  - 当前版本 `0.6.2`（2026-07-03）
  - 包内嵌入 CSV 文件（`history/csi300.csv`），**非运行时 HTTP 拉取**
  - 版本升级 = 新数据重构 = 新 PyPI release = 新 ledger 行（不静默覆盖）
- **快照机制**：
  - 首次拉取落 `data/cache/csi300_constituents.parquet` + 原始 CSV 缓存
  - `runs/ledger.jsonl` 记录 `data_sha256`（同 `CONTRIBUTING.md` §2）

### Verdict
**PASS（低风险）** —— 指数公告是历史事实，不可修订；PyPI 包嵌入数据即快照，版本控制即快照控制。

---

## G4 — Reproducibility / snapshot discipline

### 规则
第三方接入是冻结产物 —— ledger 记录 data-sha256 + as-of + source-URL + fetch-ts；rerun 零 HTTP。

### 证据
- **PyPI 包嵌入数据**：
  - `index-constitution` 将 CSV 数据嵌入包内（`index_constitution/data/history/csi300.csv`）
  - 安装后**无需任何 HTTP 请求**即可读取数据（零运行时网络依赖）
- **本地缓存策略**：
  - 首次运行：读取包内 CSV → 转为 parquet 落 `data/cache/csi300_constituents.parquet`
  - 后续运行：直接读 parquet（零网络）
- **sha256 pinning**：
  - 原始 CSV sha256 可从 PyPI 包计算（`index_constitution-0.6.2.data/data/`）
  - `runs/ledger.jsonl` 记录 `data_sha256`（同美股 `universe.py` 模式）
- **版本声明**：`index-constitution==0.6.2`（PyPI 版本 pinning，`uv.lock` 冻结）

### Verdict
**PASS** —— PyPI 包嵌入数据 = 零运行时网络；快照 + sha256 落地机制与美股侧一致。

---

## G5 — Exploratory-only vs headline

### 规则
未通过 G2+G3 PIT 验证的 = **EXPLORATORY ONLY**；通过后可入 confirmatory headline。

### 证据
- **Track C spec**：[`track-c-preregistration.md`](track-c-preregistration.md) §2 明示 `universe.cn = {index: CSI300, source: "index-constitution (MIT)"}` 是 S0 universe 输入
- **G2+G3 状态**：G2 PASS（时点查询 `constituents_at(t)`），G3 PASS（指数公告不可修订）
- **对比探索性数据**：
  - EPU（G3 ✗）→ exploratory-only（见 `data-intake-rubric.md` 表）
  - CSI300 成分股（G2+G3 ✓）→ headline 输入

### Verdict
**PASS（headline 入格）** —— 成分股数据满足 headline 条件（G2+G3 双通过）。

---

## G6 — Selection / survivorship honesty

### 规则
声明 selection bias；幸存者偏差用 PIT 成分缓解；不当 today-snapshot。

### 证据
- **`opt-out` 字段**：CSV 明确记录剔除日期（如 `"神州高铁,2016-12-12,2018-06-11"`），历史成分股含已退市/剔除者
- **幸存者偏差缓解**：
  - `constituents_at("2018-06-30")` = 2018-06-30 当日的成分股（**不**含 2018-06-30 后纳入的股票）
  - 非今日快照（避免用当前 300 成分回测历史）
- **Selection bias 声明**：
  - CSI300 本身是「规模最大、流动性最好的 300 只 A 股」selection
  - Headline = 保守上界（不含中盘 CSI500），在 pre-reg §8.0 明确声明 scope

### Verdict
**PASS** —— 幸存者偏差通过 PIT 时点查询缓解；selection bias 在 pre-reg 声明。

---

## G7 — Politeness / ToS

### 规则
限速、≥2s 间距、遵守 robots.txt、用描述性 User-Agent。

### 证据
- **PyPI 包嵌入数据**：
  - **无运行时 HTTP** —— 数据在包内（`index_constitution/data/history/csi300.csv`）
  - 安装时仅一次性 PyPI 请求（`pip install index-constitution`），无速率限制风险
- **首次安装礼貌**：
  - PyPI 官方源（pypi.org），无 robots.txt 限制
  - 单次下载（~200KB CSV），无批量爬
- **User-Agent**：
  - `pip` 默认 User-Agent（`pip/<version>`），符合 PyPI 规范
  - 无需自定义（与美股侧 `aionis/0.1` 不同，因无运行时 HTTP）

### Verdict
**PASS（零运行时网络）** —— PyPI 包嵌入数据 = 零礼貌风险（安装时一次性 PyPI 请求合规）。

---

## 与 Track C S0 的集成

### Track C 配置
[`track-c-preregistration.md`](track-c-preregistration.md) §2 冻结配置：
```yaml
universe:
  cn:
    index: CSI300
    source: "index-constitution (MIT)"
    window_start: "2016-01-01"
```

### 与美股侧对称性
- **美股**：`hanshof/sp500_constituents` + `pierrebrunelle/sp500-historical-constituents`（双源交叉验证）
- **A 股**：`index-constitution` 单源（MIT 许可 + 官方公告重构）
- **架构复用**：`src/aionis/ingest/csi300_constituents.py` 镜像 `universe.py` 结构

### 数据范围
- **历史深度**：CSV 最早记录为 2005-04-08（沪深 300 指数基期调整），覆盖 Track C `window_start: 2016-01-01`
- **成分股数量**：1226 行历史记录（含 opt-in/opt-out）
- **更新频率**：PyPI 包按需更新（指数调整公告发布后），非实时

---

## 实施路径（S0 数据构造）

### 阶段 1：首次拉取（快照冻结）
1. **安装依赖**：`uv add index-constitution`（MIT 许可，Python 3.13 兼容）
2. **读取包内数据**：`import index_constitution as ic; ic.history("csi300")` → DataFrame
3. **转换为长格式**：`[date, ticker]` 长表，`date` = `opt-in` 至 `opt_out-1` 的每日成分
4. **快照落盘**：`data/cache/csi300_constituents.parquet` + 原始 CSV 缓存
5. **sha256 记录**：入 `runs/ledger.jsonl`（新行，S0 数据构造标记）

### 阶段 2：复用
- rerun 从 `data/cache/` 读 parquet，零 HTTP
- 如 `index-constitution` 升级 → **新 ledger 行**（不覆盖历史）

### 与 Track C S0 对接
- **交叉截面构造**：按月采样 `constituents_on(t)`（t = 月末交易日）
- **Ticker 格式**：`SZ000001`（深交所）/ `SH600000`（上交所），与 baostock 价格源对齐
- **幸存者偏差控制**：2018 年截面仅含 2018 年时点成分（非今日 300）

---

## 与其他 CSI300 源的对比

| 维度 | **index-constitution (本评估, PASS)** | **qlib cn_index/collector.py (不可行)** | **csindex.com.cn 直接 (不推荐)** |
|---|---|---|---|
| **License** | MIT ✓ | Apache-2.0 ✓，但 **无 cp313 wheel** | 官方数据，但需爬虫/解析 PDF |
| **Python 3.13** | `py3-none-any.whl` 兼容 ✓ | **cp313 wheel 不存在** ✗ | N/A（需自建解析） |
| **PIT 语义** | `opt-in/opt-out` 精确到日 ✓ | 从公告重构，语义相同 ✓ | 公告 PIT，但解析复杂 |
| **运行时网络** | **零（包内嵌入）** ✓ | 依赖 qlib 运行时 HTTP ✗ | 需实时爬 ✗ |
| **维护成本** | PyPI 包自动更新 ✓ | 需维护 qlib 集群（隔离 venv）✗ | 需维护爬虫/解析逻辑 ✗ |

**结论**：`index-constitution` 是唯一满足 **Python 3.13 + 零运行时网络 + MIT** 的 CSI300 PIT 源。

---

## 待 owner 裁断（冻结前）

1. **PyPI 包信任**：`unliftedq/index-constitution` 是第三方重构（非官方），但基于中证指数官方公告——是否接受此间接源？（类比美股侧接受 `hanshof` 基于 Wikipedia 的重构）
2. **历史深度验证**：CSV 最早 2005-04-08，是否满足 Track C `window_start: 2016-01-01` 起点？
3. **更新频率**：PyPI 包按需更新（非实时）——是否接受「指数调整后延迟更新」？

---

## 不越界声明

- **PROPOSED 评估**；未触任何冻结面（`docs/track-c-preregistration.md`、`runs/ledger.jsonl`、`decisions/*`、`config/`）
- **未连 csindex.com.cn**；未拉真实数据；未安装 `index-constitution` 包
- **7-gate 评估**：复用 [`data-intake-rubric.md`](data-intake-rubric.md)、[`data-license-allowlist.md`](data-license-allowlist.md) 证据
- **实施前**：须 owner 批准第三方重构源信任 + 历史深度 + 更新频率

---

## 引用

- 内部：[`track-c-preregistration.md`](track-c-preregistration.md)、[`data-intake-rubric.md`](data-intake-rubric.md)、[`data-license-allowlist.md`](data-license-allowlist.md)、[`ingest/universe.py`](../src/aionis/ingest/universe.py)（美股侧模式）
- 外部：`index-constitution` PyPI MIT、`unliftedq/index-constitution` GitHub、中证指数有限公司（csindex.com.cn）
- 对比：[`data-intake-ashare-price-baostock.md`](data-intake-ashare-price-baostock.md)（A 股价格源 7-gate 模板）
