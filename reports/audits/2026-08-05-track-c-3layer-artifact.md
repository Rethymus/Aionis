# Track C 3-layer conditional-IC 沉积 — 结构化 artifact

> **日期**：2026-08-05 · **类型**：evidence-integrity 缺口补算（audit MEDIUM #3 关闭）
> **触发**：[`reports/audits/2026-08-04-evidence-integrity-audit.md`](2026-audits/2026-08-04-evidence-integrity-audit.md) MEDIUM #3 — handoff § culmination 的 3-layer conditional-IC β_US/β_CN "handoff prose only, no artifact"。
> **产物**：[`runs/track_c_3layer_conditional_ic.json`](../../runs/track_c_3layer_conditional_ic.json)（gitignored）。

---

## 结论

Track C 联合折叠 IC × 3-layer regime 的 conditional rank-IC（IC_t ~ regime_t, HAC）：

| 臂 | α (p) | **β (p)** | R² | n | maxlag |
|---|---|---|---:|---:|---:|
| **combined** | −0.0081 (0.507) | **−0.0148 (0.212)** | 0.017 | 71 | 3 |
| us | −0.0021 (0.894) | −0.0287 (0.129) | 0.021 | 65 | 3 |
| cn | −0.0139 (0.427) | +0.0042 (0.802) | 0.001 | 66 | 3 |

**判读**：combined 条件化 β=−0.0148（p=0.21），**null**（无 regime 交互）；与 joint-fold 2-layer cond_beta=−0.015（p=0.20）方向一致、量级相同 → **meso 层加入对 combined 影响微小**。per-region：US β=−0.0287（p=0.13，边际）、CN β=+0.0042（p=0.80，null）。全 null-favored 一致。

3-layer composite（macro+global+meso-US-SIC）valid_n=2592 日（2016-08-25..2026-08-04），TACO as-of σ 归一化，PIT 安全。

---

## 方法

1. 重建 3-layer composite：读 `data/cache/regime_{macro,global_dy,meso}.parquet`（列名：`macro_regime`/`total_spillover`/`meso_regime`），调 `aionis.features.regime_composite.regime_composite({"macro":..., "global":..., "meso":...})`（每层 past-only z-score + TACO expanding-σ）。**未覆盖** `data/cache/regime_composite.parquet`（仍是 2-layer）。
2. IC 系列：`runs/track_c_joint_ic_series.parquet`（71 月，cols `us`/`cn`/`combined`，chronological joint-fold OOS，10 共享 price 特征，region-month groups）。
3. PIT as-of join：`regime_3layer.reindex(ic.index, method="ffill")`（regime 只用 ≤ 月末数据；与 `track_c_conditional_ic.py:45` 一致）。
4. 回归：`statsmodels OLS IC_t ~ const + regime_t`，`cov_type='HAC'`，maxlag=Newey-West rule（n=71→maxlag=3）。

**未运行** LightGBM/joint-fold fit；IC 系列是已持久化的 exploratory OOS；纯回归 + composite 重建。

---

## 与 handoff § culmination 数字的差异（诚实分级）

handoff §2026-08-04 culmination 表的 "3-layer β_US=−0.001 (p=0.95) / β_CN=+0.015 (p=0.36)" 用的是 **Track B fitter on 单区 IC**（US 单区 + CN 单区独立 IC 系列）× 3-layer regime。本 artifact 用的是 **joint-fold per-region IC**（联合拟合后 per-region IC 分量）。**IC series 不同 → β 不同**，两份都是探索性 sensitivity：

- 本 artifact（joint-fold × 3-layer）：confirmatory 估计量的直接探索性证据（combined null）。
- handoff culmination（Track-B-fitter × 3-layer）：单区 sensitivity（per-region null，meso 稀释 CN 边际信号）。

handoff culmination 的 Track-B-fitter per-region 数字仍只在 prose（非联合折叠，次要 sensitivity）；如需完整 sediment，需额外跑 `track_c_a_run.py` 的 US 单区版本 + 同回归（本 audit 未做）。

---

## 反退化核验

| 检查 | 结果 |
|---|---|
| all beta finite | ✓ |
| all p ∈ [0,1] | ✓ |
| n_equal_across_arms | ✗（combined=71, us=65, cn=66）— **预期**：joint-fold per-region IC 有 NaN（us 6 个、cn 5 个），combined 列用两区至少一区有效月（skipna）；回归各自 dropna → n 不同。诚实标注，非 bug。 |
| r² ≥ 0 | ✓ |

---

## 独立性局限（披露）

Agent B（sonnet `general-purpose`）**交付了产物**（json + 反退化自检），opus Orchestrator 核验数字自洽（combined β 与 2-layer ref 一致、方向同、anti-degeneracy 通过）。非真正独立 subagent pass（agent 单一交付，无独立 verifier lane）；proxy 恢复后可补独立验证。

---

## 边界

- `[F]` 未写 ledger；未改 `data/cache/regime_composite.parquet`（仍 2-layer；3-layer composite 仅存 json 元数据 + agent 内部重建）；无 frozen surface / prereg / ADR / config 改动。
- `[F]` 纯回归 + composite 重建；无 LightGBM/refit；无真实网络/LLM/forward；未观察 E3。
- `[I]` 3-layer composite 作为 **confirmatory regime** 需修 #48 + 新 ledger 行（见 [`reports/design/2026-08-05-track-c-confirmatory-go-brief.md`](../design/2026-08-05-track-c-confirmatory-go-brief.md) D5）；本 artifact 是 exploratory sediment。
