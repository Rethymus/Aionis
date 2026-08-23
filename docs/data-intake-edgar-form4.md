# 数据接入 7 门 — EDGAR Form 4（内幕交易申报）

> **状态**：**v0.1 · 2026-08-06** · exploratory-only display module。
> **范围**：EDGAR Form 4 内幕交易数据通过 7 门强制清单，所有第三方数据集进 Aionis 前 **必须** 全部过关。
> **引用**：主 rubric 见 `docs/data-intake-rubric.md`。本文档为 Form 4 专用准入评估。

---

## 数据源概述

**EDGAR Form 4**（Statement of Changes in Beneficial Ownership）是美国 SEC 要求的公司内幕人（officers、directors、10% shareholders）在证券交易后 **2 个工作日内** 必须提交的申报。Form 4 记录买入/卖出（acquisition/disposition）、股数、成交价，是 PIT-safe 的内幕交易行为数据源。

---

## G1 — License allowlist（许可协议白名单）

### 结论：✓ **PASS**

- **规则**：仅 MIT / Apache-2.0 / BSD-2/3-Clause / CC0 / CC-BY-4.0（数据）。
- **来源**：SEC EDGAR 数据为 **US Government public domain**（17 U.S.C. §105），无版权限制，可自由使用、修改、分发。
- **通过**：Form 4 = US federal government data → public domain ✓（最宽松的许可，无需 attribution）。

---

## G2 — PIT / as-of 时点（point-in-time）

### 结论：✓ **PASS**

- **规则**：每条观测必须有「当时可知」的 timestamp；t 时刻的值不得依赖 >t 的信息。
- **机制**：
  - EDGAR 提供的 `file_date` 字段为申报日期（filing date），即市场实际可得的时点。
  - Form 4 的 `transaction_date` 为交易发生日，但该信息仅在 `file_date` 后才为市场所知。
  - 本模块使用 `file_date` 作为 PIT anchor（与 fundamentals 同一纪律）。
- **通过**：每个 Form 4 filing 都有 `file_date`（EDGAR submissions endpoint + EFTS search 均提供），且该字段不可回改 ✓。
- **实现**：
  - `form4_efts.py:fetch_form4_filings()` 返回 `filing_date` 作为 PIT anchor。
  - 消费者应使用 `filing_date` 进行 backward-as-of 对齐（mirroring `fundamentals.py:pit_align`）。

---

## G3 — No-revision contract（无回改契约）

### 结论：✓ **PASS**

- **规则**：provider **不得**追溯重算历史。若不可证：首次接入即**快照 + sha256 = 冻结真相**。
- **机制**：
  - EDGAR Form 4 申报 **不可回改** — 一旦提交，即成为永久记录。
  - 修正（Form 4/A）为 **新 accession number** 的新 filing，绝不静默覆盖原记录。
  - 本模块 cache 机制（`data/cache/form4_<cik>_<window>.json`）记录 raw hit list，sha256 可重现。
- **通过**：Form 4 immutable by design（SEC EDGAR 核心特性）✓；strictly cleaner than ALFRED/EPU。
- **实现**：
  - `form4_efts.py:_efts_cache_path()` 按 (issuer_cik, start, end) 缓存 raw JSON。
  - `form4_efts.py:_fetch_efts_hits()` 先读缓存，缓存命中时零 HTTP 调用。
  - `universe.py:_sha256()`（future work）可对 cache 文件做 sha256 指纹记录。

---

## G4 — Reproducibility / snapshot discipline（可复现）

### 结论：✓ **PASS**

- **规则**：第三方接入本身是冻结产物 — 在 ledger 记录 data-sha256 + as-of + source-URL + fetch-ts。
- **机制**：
  - 本模块 **不执行** 真实 EDGAR 网络请求（owner-gated；仅 exploratory）。
  - EFTS 响应缓存至 `data/cache/`（gitignored），rerun 时直接读取。
  - CIK 列表可从 `data/cache/cik_names_*.json` 读取（如果存在）。
- **通过**：全 cache 路径，rerun 零 HTTP ✓（mirroring `stakes_13d_efts.py` 纪律）。
- **实现**：
  - `form4_efts.py:_get_json()` 先检查 `fp.exists()`，命中则返回缓存。
  - 调用方必须提供 `cache_dir` 参数（默认 `settings.data_dir / "cache"`）。

---

## G5 — Exploratory-only by default（默认探索性）

### 结论：✓ **ENFORCED**

- **规则**：未通过 G2 + G3 PIT 验证的数据 = **EXPLORATORY ONLY**。
- **判定**：
  - Form 4 **已通过** G2（PIT via `file_date`）+ G3（immutable by design）。
  - 但 owner 明确要求：**Form 4 为 exploratory display module，永不进 confirmatory / Phase-B**。
- **原因**：
  - Form 4 非项目核心 claim（Phase B/C/D/E 均不依赖内幕交易数据）。
  - 为 control scope + 避免数据膨胀，Form 4 仅作为 dashboard 可选 display 层。
- **含义**：
  - 本模块（`form4_efts.py` + `form4.py`）= exploratory-only。
  - **绝不**写入 `runs/ledger.jsonl`（除非未来升格，需 owner 明确批准）。
  - **绝不**进入 frozen config / confirmatory pipeline。
- **实现**：
  - 本文档明文标记 mode = exploratory。
  - 代码注释中声明 "exploratory — display module only"。
  - 禁止任何调用方将其用于 confirmatory 特征。

---

## G6 — Selection / survivorship honesty（选择 / 幸存者诚实）

### 结论：✓ **PASS**

- **规则**：社会/政策类数据有 selection bias — **声明为 scope 限制，绝不当 ground truth**。
- **判定**：
  - Form 4 为强制性法律申报（内幕人 2 日内必须报告），覆盖 **当前 S&P 500 成员** + 其他在 SEC 注册的发行人。
  - **Selection bias**：仅记录有 insider trading 的公司；无 insider trading 的公司无记录。
  - **Survivorship bias**：当前 EDGAR 数据包含退市公司（历史 filing 永久保留），故 survivorship risk 低。
- **含义**：
  - Form 4 可用于 exploratory display（如 "某公司近 6 月内幕交易趋势"）。
  - **绝不可**当作定价因子或 ground truth（仅辅助可视化）。
- **实现**：
  - 本模块输出 `DataFrame` 供 dashboard display（e.g. `streamlit` plot）。
  - 不建议将其用于任何 confirmatory 特征工程。
- **v2 宇宙扩展（2026-08-23，业主"彻底对齐颗粒度"指令）**：发行人 5→30（原 5 大盘种子 + 25 家
  mega/large caps，CIK 与 form8k v2/v3 宇宙同源、cik_resolver 快照实解+实体名核对）。**广度受
  有界窗口约束**：`--start 2026-01-01`（2026 YTD）；已提交面板的 2013-2025 聚合（5 发行人宇宙）
  由 `export_form4` 的 retain-merge **逐字保留**，宇宙差异在面板 methodology 披露（"universe
  widened from 5 to 30 in 2026"）——逐年宇宙混合如实可见，不静默改史。全历史深拉（30 发行人 ×
  2016→today）留给后续分次长跑。

---

## G7 — Politeness / ToS（礼貌 / 服务条款）

### 结论：✓ **PASS**

- **规则**：限速、遵守 robots.txt、不批量爬、用 descriptive User-Agent、尊重源 ToS。
- **机制**：
  - SEC EDGAR 要求 ≥2s 请求间隔（fair access policy）。
  - 本模块复用 `ingest.http_policy.HostSpacingPolicy`（min_interval=2.0s）。
  - User-Agent 为 `"Aionis research form4-efts contact@example.com"`（descriptive）。
- **通过**：≥2s spacing + descriptive UA + exp-backoff on 429/5xx ✓（mirroring `fundamentals.py` 纪律）。
- **v2 请求账**：30 发行人 = 30 EFTS 查询 + 每 filing 1 次 XML（礼貌 ≥2s 间距）。2026 YTD 有界窗
  冷拉估算数百至 ~2k 请求 ≈ 0.5-2 小时；逐发行人 checkpoint 落盘（超时保留已完成发行人，可续）；
  EFTS + XML cache 幂等（重跑近零请求）。
- **实现**：
  - `form4_efts.py` 使用 `_policy_get()`（来自 `universe.py`），该函数注入 `http_policy._HTTP_POLICY`。
  - `http_policy.py:HostSpacingPolicy.wait()` 强制 ≥2s 间隔。
  - `_get_json()` 内部 exp-backoff 重试（transient failures only）。

---

## 接入决策汇总

| 门 | 结果 | 说明 |
|---|---|---|
| **G1 — License** | ✓ **PASS** | SEC EDGAR public domain（17 U.S.C. §105）。 |
| **G2 — PIT** | ✓ **PASS** | `file_date` 为申报日期，PIT anchor 不可回改。 |
| **G3 — No-revision** | ✓ **PASS** | Form 4 申报 immutable；修正为新 accession number。 |
| **G4 — Reproducibility** | ✓ **PASS** | 全 cache 路径（`data/cache/`），rerun 零 HTTP。 |
| **G5 — Mode** | ✓ **ENFORCED** | **Exploratory-only**（owner 明确要求；永不进 confirmatory）。 |
| **G6 — Selection** | ✓ **PASS** | 明确声明 scope 限制（display only，非定价因子）。 |
| **G7 — Politeness** | ✓ **PASS** | ≥2s spacing + descriptive UA + exp-backoff。 |

**最终结论**：Form 4 **全部 7 门过关**。但受 owner scope 限制，本 module 为 **exploratory-only display 层**，不进 confirmatory pipeline。

---

## 使用限制与合规声明

1. **Scope 限制**：本模块仅用于 exploratory display（如 dashboard 展示 insider trading 趋势），**绝不**用于 confirmatory 特征或任何 headline claim。
2. **数据量控制**：Form 4 数据量庞大（S&P 500 年均 10k+ filing）。建议：
   - **Start small**：仅 top 20-50 CIK（按市值或活跃度）。
   - **Time window limit**：建议 6-12 month rolling window（非全历史）。
   - 如 EFTS volume 过大，可在 `form4_efts.py` 内添加 early-stop 逻辑。
3. **Cache 管理**：`data/cache/form4_*.json` 为 gitignored regenerable artifact，定期清理可释放磁盘空间。
4. **Compliance**：Form 4 为 public domain 数据，但二次分发应遵守 SEC ToS（non-commercial, attribution recommended）。

---

## 文件清单

- `src/aionis/ingest/form4_efts.py` — EFTS full-text-search client（Form 4 专用）。
- `src/aionis/ingest/form4.py` — Form 4 XML parser（extract filer/ticker/date/A-D/shares/price）。
- `docs/data-intake-edgar-form4.md` — 本文档（7 门评估）。
- `tests/test_form4.py` — Hermetic 单元测试（fixture-based，无真实网络请求）。

---

## 未来升格路径（如 owner 批准）

若未来需将 Form 4 升格为 confirmatory 特征，需：

1. **Pre-registration**：在 `docs/phase-*-preregistration.md` 新增 Form 4 相关 claim。
2. **Ledger entry**：写入 `runs/ledger.jsonl`，记录 `mode: confirmatory` + data-sha256。
3. **Scope validation**：通过 selection-bias 测试（e.g. 与 fundamentals 的 cross-section 稳定性）。
4. **Re-validation**：通过所有 7 门（G1-G7）+ anti-leakage review。

**当前状态**：exploratory-only（无升格计划）。
