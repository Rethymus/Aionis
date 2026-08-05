# A2/A3 — macro_headline 6 fetch + broadcast join（confirmatory 41 spec）

> 状态：**PROPOSED · 2026-08-05 · 业主授权 A2/A3 完整 41 路径**。本 spec 是 A2（fetch）+ A3（broadcast）的实装依据。
> 关联：ledger #48（confirmatory feature_cols 41）、[`confirmatory-41-feature-readiness.md`](2026-08-05-confirmatory-41-feature-readiness.md)（Agent 1：US 23+CN 12 on disk，macro 6 = 0%）、`macro_dff.py`/`macro_surprise.py`（复用源）。

---

## 0. 目标

为 confirmatory 41 特征补齐 macro_headline 6（US 4 + CN 2），接 to `build_joint_panel` asymmetric（A1）的联合面板，使 `track_c_joint_run.py` 能跑 asymmetric41（confirmatory OOS）。

asymmetric35（commit `52a8d09`）已坐实 null（US fund 无 alpha）；macro 6 是 broadcast feature，signal 弱，confirmatory 41 大概率同 null —— 但 spec-faithful climax（J-T 门）需 41。

---

## 1. 复用图（reuse-first，禁造轮子）

| 复用 | 来源 | 用途 |
|---|---|---|
| `fetch_alfred_vintages(series_id, fred_api_key, cache_dir)` | `features/macro_surprise.py:98` | 通用 ALFRED vintage fetch + cache `alfred_{id}.json` |
| `surprise_time_series(changes)` | `features/macro_surprise.py:181` | trailing z-score surprise（trailing 24 raw surprises, min 12, clip ±5） |
| `macro_surprise_date_broadcast(...)` | `features/macro_surprise.py:310` | date-broadcast（merge_asof backward, PIT）— **A3 直接复用** |
| `fetch_dff_vintages` + as-of `merge_asof(allow_exact_matches=False)` | `ingest/macro_dff.py:88` | DFF as-of 模式（daily series 参考） |

**新建**：`src/aionis/features/macro_headline.py`（fetch + surprise for 6 series）+ `tests/test_macro_headline.py`。

---

## 2. A2a — US macro 4（GREEN，FRED public domain）

| feature | series | fetch | surprise |
|---|---|---|---|
| `term_spread_1y_10y` | GS10 − TB3MS | `fetch_alfred_vintages("GS10")` + `("TB3MS")` | daily spread as-of；surprise = Δ 或 z-score（**预指定**：z-score 复用 `surprise_time_series` 适配 daily） |
| `credit_spread` | BAA10Y − GS10（或 BAA − AAA） | `fetch_alfred_vintages("BAA10Y")` + GS10 复用 | 同上 |
| `vix_surprise` | VIXCLS（**cached** `alfred_VIXCLS.json`，no-revision 合同） | 已 cache | ΔVIX z-score |
| `dff_surprise` | DFF（**cached** `alfred_DFF.json`） | 已 cache（`macro_dff.py`） | 复用 `macro_dff` as-of + ΔDFF z-score |

**7-gate**：US FRED = public domain（G1✓）；ALFRED vintage PIT-safe（G2✓）；no-revision（G3✓）；snapshot+sha256（G4，cache 文件）；exploratory flag 不需（confirmatory-tier）。

---

## 3. A2b — CN macro 2（YELLOW，snapshot+exploratory）

| feature | series | source | verdict |
|---|---|---|---|
| `gdp_surprise` | CN GDP（`MKTGDPCNA646NWDB` OECD via FRED，或 ALFRED vintage） | OECD/ALFRED | **YELLOW**：OECD license 需核验；ALFRED CN vintage 覆盖有限 → 若无 vintage，snapshot+sha256+`exploratory_flag=True`（同 NBS/EPU 先例） |
| `cpi_surprise` | CN CPI（`CPALTT01CNM659N` 或 `CHNCPIALLMINMEI`） | OECD/ALFRED | 同上 |

**7-gate**：G1 OECD license 核验（若 restricted → 非 headline）；G2/G3 vintage 若无 → snapshot+exploratory（G5 flag）。

**headline 决策（待业主）**：CN macro 2 若 exploratory-only，confirmatory 41 = asymmetric35 (25) + US macro 4 headline + CN macro 2 exploratory-flagged。或收窄 headline macro = US 4 only（claim amend）。**默认**：CN 2 进 feature 但 `exploratory_flag=True`（与 #47 cninfo 模式一致）。

---

## 4. A3 — broadcast join to joint panel

复用 `macro_surprise_date_broadcast`（macro_surprise.py:310）模式：
- daily macro surprise → 月末 `merge_asof(direction="backward", allow_exact_matches=False)` → per-region broadcast
- US macro broadcast 到 US 行；CN macro broadcast 到 CN 行
- 新 helper：`join_macro_to_joint_panel(joint_panel, macro_us_daily, macro_cn_daily) -> joint_panel with macro cols`

**PIT**：macro 在月末 t 只用 ≤ t 数据（merge_asof backward，同 macro_surprise_date_broadcast）。

---

## 5. 测试（反退化 + PIT）

- `test_us_macro_surprise_finite_and_no_future_leakage`：surprise finite；as-of 严格 < d（突变未来 → 不变）
- `test_term_spread_and_credit_spread_cross_sectional_variation`：非 CONSTANT（RD-13）
- `test_cn_macro_exploratory_flag_set`：CN macro 行 `exploratory_flag=True`
- `test_broadcast_join_per_region`：US 行有 US macro、CN 行有 CN macro；月末 ffill PIT
- `test_vintage_cache_idempotent`：二次 fetch cache hit（不重下载）

---

## 6. runner 扩展（asymmetric41 模式）

`track_c_joint_run.py` 加第三模式 `TRACK_C_JOINT_MODE=asymmetric41`：
- `build_joint_panel` asymmetric（US 23 / CN 12）+ `join_macro_to_joint_panel`（US 4 + CN 2）
- feature_cols = UNION_35 + 6 macro = 41（confirmatory spec-faithful）
- 产物 `runs/track_c_joint_asym41_*`

---

## 7. 边界

- `[F]` network fetch OK（prereg #48 批准 macro headline 6 来源；FRED public domain；≥2s politeness）；不写 ledger；不改 frozen surface（#46/#47/#48 不变）。
- `[F]` A2a/A2b/A3 = 新文件（`macro_headline.py` + 测试 + runner 扩展）；0 改动 src frozen。
- `[I]` confirmatory OOS 跑 = 业主 d6_go（第二个 GO）；asymmetric41 exploratory 跑通 ≠ confirmatory 判读。
- `[I]` CN macro 2 headline vs exploratory 决策 = 业主（默认 exploratory_flag，同 #47）。
