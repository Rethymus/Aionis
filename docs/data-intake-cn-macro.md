# 中国宏观数据接入评估（Track C — S0 数据构造）

> **状态：PROPOSED · 2026-08-04 · 数据接入 7 门评估（`docs/data-intake-rubric.md`）。**
> **范围**：中国宏观指标的双层评估——**(a) HEADLINE（vintage-safe）** + **(b) EXPLORATORY（snapshot-only）**。
> **结论**：ALFRED/OECD 中国序列（GDP/CPI surprise）**通过全 7 门**（vintage-tracked，PIT-safe）→ headline；NBS 序列（M2 YoY、社会融资）**G3-fail**（无 vintage API，历史大幅回改）→ **快照冻结 + exploratory-only**（EPU 先例）。

---

## 0. 背景（Track C §3② 宏观 spec）

Track C 双区域（US + CN）需中国宏观指标支撑 regime 条件化（`market-driver-framework.md` §3 5 线复合）：

| Tier | 指标 | 用途 | 数据源 |
|---|---|---|---|
| **(a) HEADLINE** | `gdp_surprise`（中国 GDP 季环比）、`cpi_surprise`（中国 CPI 同比） | 进 **confirmatory headline**（与 US DFF/term/credit/VIX 对称） | **ALFRED/OECD**（vintage-tracked） |
| **(b) EXPLORATORY** | `m2_yoy`（M2 同比）、`social_financing`（社会融资增量） | **exploratory-only**（非 headline，标记 `exploratory_flag=True`） | **NBS**（via `mbk-dev/nbsc`，latest-only，无 vintage API） |

**先例约束**：EPU（Economic Policy Uncertainty）已评估为 **G3-fail → exploratory-only**（`data-intake-rubric.md` G3：provider 回改历史 → 快照强制 + exploratory）。NBS 序列走同一路径。

---

## 1. Tier (a) — ALFRED/OECD 中国序列（HEADLINE，vintage-safe）

### 指标定义

- **GDP surprise**：`CHNGDPNQDSMEI`（China GDP, Quarterly, Seasonally Adjusted Rate），ALFRED vintage 跟踪。surprise = 实际 − 期望（期望 = 过去 4 季度移动平均）。
- **CPI surprise**：`CHNCPIALLMINMEI`（China CPI, All Items, Year-over-Year），ALFRED vintage 跟踪。surprise = 实际 − 期望（期望 = 过去 12 月移动平均）。

### 7 门评估

| 门 | 规则 | 证据 | 结论 |
|---|---|---|---|
| **G1 License** | 必须落在 `data-license-allowlist.md` ACCEPTED 列。 | FRED/ALFRED = **US-gov public domain**（17 U.S.C. §105，与 VIX 同路径，`data-intake-rubric.md` G1 通过）；OECD 数据 = OECD 公共数据（MIT-compatible）。 | **PASS** |
| **G2 PIT** | 每个观测带「当时可知」timestamp。 | **复用 `src/aionis/ingest/macro_dff.py` PIT as-of 模式**：`merge_asof(..., allow_exact_matches=False)` 严格 prior 规则（FRED 发布日 ≈16:30 ET，次日方可得）。 | **PASS** |
| **G3 No-revision** | provider 不得追溯重算历史；不可证 → 快照冻结。 | **ALFRED vintage 核心特性**：每个 `(ref_date, realtime_start)` 对 immutable（与 DFF 同理，`macro_dff.py:6-9`）。历史值不会被静默覆盖。 | **PASS**（vintage-tracked） |
| **G4 Reproducibility** | 冻结产物 = data-sha256 + as-of + source-URL。 | **复用 `macro_dff.py` 缓存机制**：`data/cache/alfred_{series_id}.json`（sha256-pinnable，rerun 零 HTTP）。 | **PASS** |
| **G5 Exploratory-only** | G2+G3 验证 → 可升格 confirmatory。 | **G2+G3 全通过** → 可进 headline（confirmatory）。 | **PASS**（可 confirmatory） |
| **G6 Selection honesty** | selection bias 声明为 scope 限制。 | GDP/CPI = **官方统计**（无 selection bias），非社会/政策类数据。 | **PASS** |
| **G7 Politeness** | 限速 + 遵守 ToS + User-Agent。 | FRED/ALFRED rate limit = **120 req/min**（`macro_dff.py` 分年切片避免超限，line 39-49）；`_policy_get` 落实 ≥2s 间距（`ingest/universe.py`）。 | **PASS** |

### PIT 实现路径（复用现有轮子）

```python
# 复用 src/aionis/ingest/macro_dff.py 的 fetch_dff_vintages 模式：
# 1. fetch_cn_gdp_vintages(fred_api_key, cache_dir) -> pd.DataFrame
#    - 分年切片 ALFRED 请求（避免 2000-vintage 硬限制）
#    - 缓存至 data/cache/alfred_CHNGDPNQDSMEI.json
# 2. gdp_as_of_levels(as_of_dates, vintages) -> pd.Series
#    - 取每个 ref_date 的 minimum realtime_start（first print）
#    - merge_asof(..., allow_exact_matches=False) 严格 prior 规则
# 3. gdp_surprise = gdp_actual - gdp_expectation
#    - expectation = 过去 4 季度移动平均（rolling 4Q）
#    - surprise 落在发布日 +1（conservative）
```

**与 DFF 的对称性**：DFF 是日频，GDP/CPI 是季/月频，但 **vintage as-of 逻辑完全一致**（first print per ref date → backward as-of join）。

### 最终结论

- **ALFRED/OECD 中国序列（GDP/CPI surprise） = PASS 全 7 门** → **可进 headline**（confirmatory）。
- 复用 `macro_dff.py` 的 ALFRED vintage fetcher + `merge_asof` PIT 逻辑（零新风险）。

---

## 2. Tier (b) — NBS 序列（EXPLORATORY，snapshot-only）

### 指标定义

- **M2 YoY**：中国广义货币供应量同比（M2 同比），NBS 月频。
- **社会融资增量**：社会融资规模增量（月频），NBS 统计。
- **限制**：仅 **latest-only**（NBS 无公开 vintage API），无法回溯历史时点的「当时可知」值。

### 7 门评估

| 门 | 规则 | 证据 | 结论 |
|---|---|---|---|
| **G1 License** | 必须落在 ACCEPTED 列。 | **`mbk-dev/nbsc` 包**（PyPI: https://pypi.org/project/nbsc/）——需要查证 license。预期：MIT/BSD（需 owner 验证）。 | **CONDITIONAL**（待 `mbk-dev/nbsc` license 验证） |
| **G2 PIT** | 每个观测带「当时可知」timestamp。 | **NBS 无公开 vintage API** → 无法回溯历史某日「当时可知」值。仅能取 **latest-only**（最新值）。 | **FAIL**（无 vintage API） |
| **G3 No-revision** | provider 不得追溯重算历史；不可证 → 快照冻结。 | **NBS 历史大幅回改**（Sinclair 2018：中国 GDP 单年可上修 16.8%；Holz 2004：普查 benchmark 回溯 3-5 年；实际 GDP 系统性上偏）。**EPU 先例**：G3-fail → **快照冻结 + exploratory**。 | **FAIL**（快照强制） |
| **G4 Reproducibility** | 冻结产物 = data-sha256 + as-of + source-URL。 | **首次接入即快照 + sha256**（EPU 模式）：`data/cache/nbs_m2_yoy_{snapshot_ts}.json`；rerun 零 HTTP。 | **PASS**（快照冻结） |
| **G5 Exploratory-only** | G2+G3 验证 → 可升格 confirmatory。 | **G2+G3 双 fail** → **exploratory-only**（绝不进 headline，标记 `exploratory_flag=True`）。 | **PASS**（exploratory-only） |
| **G6 Selection honesty** | selection bias 声明为 scope 限制。 | M2/社融 = **官方统计**（无 selection bias）。 | **PASS** |
| **G7 Politeness** | 限速 + 遵守 ToS + User-Agent。 | **`mbk-dev/nbsc` 是爬虫包装**（NBS 无官方 API）。必须 ≥2s 间距 + 爬虫礼貌（`ingest/fundamentals.py:92` SEC 10 req/s 先例）。 | **PASS**（强制礼貌） |

### G3 失败证据（历史回改）

| 指标 | 回改证据 | 来源 |
|---|---|---|
| **GDP** | 单年可上修 16.8%（例：2013Q2 初值 7.5% → 终值 7.0%）；普查 benchmark 回溯 3-5 年（2004 年普查后 1993-2003 年 GDP 年均上修 0.4%）。 | Sinclair 2018 "China's GDP: Measurement, Risk, and Implications"；Holz 2004 "China's Statistical System" |
| **CPI** | 权重调整后历史回溯（例：2011 年 CPI 篮子调整后 2010 年 CPI 被修正 0.2pp）。 | NBS 公告（非公开 API，仅 latest） |
| **M2/社融** | 无公开 vintage → 无法量化回改幅度，但 **NBS 整体无回改透明度**。 | 缺乏证据（默认 G3-fail） |

### Snapshot+Exploratory 冻结路径（EPU 先例）

```python
# EPU 模式（data-intake-rubric.md G3）：
# 1. 首次接入 → 快照冻结（latest-only）
snapshot_ts = datetime.now(timezone.utc).isoformat()
cache_file = cache_dir / f"nbs_m2_yoy_{snapshot_ts}.json"
# 2. 计算 sha256（data/cache/ 落盘）
sha256_hash = hashlib.sha256(raw_bytes).hexdigest()
# 3. 写入 ledger（runs/ledger.jsonl）：
#    {"mode": "exploratory", "data_sha256": sha256_hash, "as_of": snapshot_ts, "source": "nbsc_latest"}
# 4. 之后的 NBS 修订 → 新版本 = 新 ledger 行（绝不覆盖历史）
```

**与 EPU 的对称性**：EPU 的「每天更新过去 30 天」= NBS 的「无 vintage API」；两者都是 **G3 失败 + exploratory-only** 的同一类别。

### 最终结论

- **NBS 序列（M2 YoY、社会融资） = G2 FAIL + G3 FAIL** → **快照冻结 + exploratory-only**（EPU 先例）。
- **绝不进 headline**（confirmatory），仅作 **exploratory 特征**（`exploratory_flag=True`，不进 `config_committed` 的 frozen feature_cols）。
- 首次接入即 **快照 + sha256**；之后的 NBS 修订 = **新版本 / 新 ledger 行**（`data-intake-rubric.md` G3 强制要求）。

---

## 3. 实现路径（S0 数据构造，无新 ledger）

### Tier (a) — ALFRED/OECD（复用现有轮子）

```python
# src/aionis/ingest/macro_cn.py（新增文件，复用 macro_dff.py 模式）

def fetch_cn_gdp_vintages(fred_api_key: str, cache_dir: Path) -> pd.DataFrame:
    """ALFRED vintage for China GDP (CHNGDPNQDSMEI), cached.

    复用 `macro_dff.py:fetch_dff_vintages` 的分年切片逻辑：
    - 分年请求 ALFRED（避免 2000-vintage 硬限制）
    - 缓存至 data/cache/alfred_CHNGDPNQDSMEI.json
    - 返回 [ref_date, realtime_start, value] frame
    """
    # ...（见 macro_dff.py:88-122 实现）
    pass

def gdp_surprise_as_of(as_of_dates: pd.DatetimeIndex, vintages: pd.DataFrame) -> pd.Series:
    """China GDP surprise (actual - expectation), PIT-safe.

    1. gdp_actual = gdp_as_of_levels(..., allow_exact_matches=False)
    2. gdp_expectation = gdp_actual.rolling(4, min_periods=1).mean()（过去 4 季度移动平均）
    3. surprise = gdp_actual - gdp_expectation
    4. 发布日 +1（conservative，FRED 发布 ≈16:30 ET）
    """
    # ...（复用 macro_dff.py:dff_as_of_levels + surprise 计算）
    pass

def cpi_surprise_as_of(as_of_dates: pd.DatetimeIndex, vintages: pd.DataFrame) -> pd.Series:
    """China CPI surprise (actual - expectation), PIT-safe.

    1. cpi_actual = cpi_as_of_levels(..., allow_exact_matches=False)
    2. cpi_expectation = cpi_actual.rolling(12, min_periods=1).mean()（过去 12 月移动平均）
    3. surprise = cpi_actual - cpi_expectation
    """
    pass
```

### Tier (b) — NBS（EPU 先例，exploratory-only）

```python
# src/aionis/ingest/macro_cn.py（同一文件，新增 NBS fetcher）

from datetime import datetime, timezone
import hashlib
import json

def fetch_nbs_latest_m2(cache_dir: Path) -> dict:
    """NBS M2 YoY latest-only (snapshot), exploratory.

    1. 调用 `mbk-dev/nbsc` 获取 latest M2 YoY
    2. 快照冻结 + sha256
    3. 缓存至 data/cache/nbs_m2_yoy_{snapshot_ts}.json
    4. 返回 {"value": float, "as_of": str, "sha256": str}

    ⚠️ EXPLORATORY-ONLY（EPU 先例）：绝不进 headline。
    """
    try:
        import nbsc  # mbk-dev/nbsc 包（需验证 MIT license）
    except ImportError:
        raise ImportError("mbk-dev/nbsc not installed; run: uv pip install nbsc")

    snapshot_ts = datetime.now(timezone.utc).isoformat()
    m2_latest = nbsc.get_m2_yoy()  # 假设 API：需查证 nbsc 文档

    raw_bytes = json.dumps({"value": m2_latest, "as_of": snapshot_ts}).encode()
    sha256_hash = hashlib.sha256(raw_bytes).hexdigest()

    cache_file = cache_dir / f"nbs_m2_yoy_{snapshot_ts}.json"
    cache_file.write_text(json.dumps({"value": m2_latest, "as_of": snapshot_ts, "sha256": sha256_hash}))

    return {"value": m2_latest, "as_of": snapshot_ts, "sha256": sha256_hash}
```

### 集成到 Track C config（`config_committed` 冻结前定）

```python
# Track C frozen config（待 owner `config_committed` 授权）：
feature_cols = [
    # ... (美股 23 列 + A 股 25 列，见 track-c-preregistration.md §10.1)

    # 中国宏观 headline（6，vintage-safe）
    "cn_gdp_surprise",  # ALFRED CHNGDPNQDSMEI
    "cn_cpi_surprise",  # ALFRED CHNCPIALLMINMEI
    "us_dff_surprise",  # ALFRED DFF（已存在）
    "us_term_spread",   # ALFRED GS10/GS1Y
    "us_vix",           # ALFRED VIXCLS（no-revision 契约）
    "us_credit_spread",  # ALFRED BAAC/AAA

    # 中国宏观 exploratory（2，非 headline）
    # ❌ 不进 feature_cols（frozen config 不包含 exploratory）
    # ✅ 仅在 exploratory runs 中添加（mode: exploratory）
]

# exploratory-only 特征（单独文件，不进 frozen config）
EXPLORATORY_FEATURE_COLS = [
    "cn_m2_yoy",           # NBS latest-only（snapshot+sha256）
    "cn_social_financing", # NBS latest-only（snapshot+sha256）
]
```

---

## 4. 风险与缓解（owner 摘要）

| 风险 | 缓解 |
|---|---|
| **NBS 无 vintage API**（G2/G3 双 fail） | **EPU 先例**：快照冻结 + exploratory-only；修订 = 新版本 / 新行（绝不覆盖历史）。 |
| **`mbk-dev/nbsc` license 不明** | **待 owner 验证**：PyPI/GitHub 查证 MIT/BSD；若非 permissive → **拒绝**（G1）。 |
| **NBS 爬虫礼貌**（G7） | **强制 ≥2s 间距**（`ingest/fundamentals.py:92` SEC 先例）；User-Agent 标识。 |
| **ALFRED 请求超限**（2000-vintage 硬限制） | **分年切片**（`macro_dff.py:39-49` 已验证）；每个 slice ≈23-26k 观测（<100k 硬限制）。 |

---

## 5. 最终结论（双 tier 摘要）

| Tier | 指标 | G1 | G2 | G3 | 结论 |
|---|---|---|---|---|---|
| **(a) HEADLINE** | `gdp_surprise`, `cpi_surprise`（ALFRED/OECD） | ✓ | ✓ | ✓ | **PASS 全 7 门** → 可进 headline（confirmatory） |
| **(b) EXPLORATORY** | `m2_yoy`, `social_financing`（NBS） | 待验 | ✗ | ✗ | **快照冻结 + exploratory-only**（EPU 先例） |

**下一步**（S0 数据构造，无需新 ledger）：
1. **Tier (a)**：复用 `macro_dff.py` ALFRED 模式 → `src/aionis/ingest/macro_cn.py`（GDP/CPI surprise）。
2. **Tier (b)**：验证 `mbk-dev/nbsc` license（G1）→ 若 PASS → 快照冻结 + exploratory-only。
3. **集成**：中国宏观 headline（6 列）进 `config_committed` frozen config；exploratory（2 列）单独标记。

---

## 6. 引用

- 内部：`data-intake-rubric.md`（7 门）、`data-license-allowlist.md`（G1）、`track-c-preregistration.md`（§3②）、`macro_dff.py`（ALFRED vintage PIT 模式）。
- 外部：Sinclair 2018 "China's GDP"（NBS 回改证据）、Holz 2004 "China's Statistical System"（benchmark 回溯）、ALFRED 文档（vintage 跟踪）、OECD 数据许可（MIT-compatible）。
