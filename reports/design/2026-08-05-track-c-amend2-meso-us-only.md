# Track C amendment #48 — confirmatory GO 起草（owner D1=A 2026-08-05）

> 状态：**PROPOSED · 2026-08-05 · 业主授权起草（D1=A）· 待业主授权 `config_committed` 入 ledger**。
> 本文档记录 amendment #48 的具体改动 + dry-run 证据；**未 apply 到 frozen prereg 本体、未入 ledger、未跑 confirmatory OOS**——这些都是业主 `--commit` 授权后的动作。
>
> 关联：[`2026-08-05-track-c-confirmatory-go-brief.md`](2026-08-05-track-c-confirmatory-go-brief.md)（P0 决策包，D1-D6）、[`2026-08-04-track-c-joint-fold-spec.md`](2026-08-04-track-c-joint-fold-spec.md)（D1-D5 spec）、prereg v1.0 [`docs/track-c-preregistration.md`](../../docs/track-c-preregistration.md)（FROZEN #46 + amend #47）、[`2026-08-04-shenwan-meso-7gate.md`](2026-08-04-shenwan-meso-7gate.md)（Lane A meso 裁定）。

---

## 摘要

业主 2026-08-05 签注 **D1=A**（保留联合折叠 machinery）。amendment #48 把它落到 frozen config 层：
- **meso 收窄**：US SIC-peer momentum ONLY（confirmatory）；CN 申万 EXPLORATORY-ONLY（G3-fail per Lane A）
- **confirmatory feature_cols = 41**（US 23 fundamentals+price + CN 12 price-only + macro 6；cn_fundamentals exploratory per #47）
- **Q1/Q2/Q3/Q5 冻结**：group=region-month、joint IC=区域内 IC 等权、feature_cols 41 不对称、baostock G3 raw

累积在 #46（原始）+ #47（cninfo exploratory）之上；#46/#47 行不变（append-only）。

---

## §1 改动清单（相对 #46+#47）

| 字段 | #46/#47 值 | #48 值 |
|---|---|---|
| `claim` | dual-region rank-IC（#47 收窄为 US-confirmatory + A-share exploratory） | 加 "JOINT chronological walk-forward" + "feature_cols = 41" + group/IC 聚合显式化 |
| `regime_state.meso` | "US SIC-peer + CN shenwan, equal-weight" | **"US SIC-peer ONLY (confirmatory); CN shenwan EXPLORATORY-ONLY (G3-fail)"** |
| `confirmatory_go`（新） | — | 9 个子字段：owner_authorization / d1_estimator / d2_group / d3_joint_ic / d4_feature_cols (count=41) / d5_meso / d6_go / baostock_g3_strategy / estimator_artifact |

`confirmatory_go.d4_feature_cols` 明确：
- `us_confirmatory_23` = us_fundamentals_13 + us_price_10
- `cn_confirmatory_12` = cn_price_12（baostock raw）
- `macro_confirmatory_6` = macro_headline_6
- `cn_fundamentals_exploratory` = NOT in confirmatory headline（per #47）
- `regime_interaction_1` = regime_state 3-layer composite × score（multiplicity 预算 1）
- `asymmetry_note` = US 23 vs CN 12，LightGBM 默认处理 missing

---

## §2 dry-run 证据

```
$ uv run python scripts/track_c_amend2.py
[track_c-amend2] config_sig=e14b9d445411e74cc3418af3bde1148163725875b01ab75175bdde002225e738
[track_c-amend2] amends=#46/#47 -> #48 confirmatory GO (owner D1=A 2026-08-05): ...
[track_c-amend2] feature_cols count: 41
[track_c-amend2] DRY-RUN (no append). Re-run with --commit to append ledger #48.
```

- **sig 自洽**：`build_amendment()` 重算 sig == dry-run 输出（MATCH=True）。
- **ruff clean**：`All checks passed!`（scripts/track_c_amend2.py）。
- **ledger 仍 47 行**（dry-run，未 append）。
- **cn_fundamentals_13 carry #47**：`"EXPLORATORY-ONLY (amendment #47): mirror us_fundamentals_13 via cninfo..."`（累积正确）。

---

## §3 apply 流程（待业主授权）

1. **业主授权 `--commit`**（= 业主动作：写 frozen config 的 `config_committed` ledger 行 #48）。
   ```
   uv run python scripts/track_c_amend2.py --commit
   ```
   → ledger 47 → 48 行；row 含 `amends` note + 新 config（sig `e14b9d44...`）；sha256 自洽。
2. **业主授权首次 confirmatory OOS 跑**（= 业主动作：观察 confirmatory OOS rank-IC）。
   - 我执行 `scripts/track_c_joint_run.py` 在全 41 特征上（解除 exploratory 的 10 列限制）+ J-T 门（`eval/sesoi_gate.py`）作用在 `score × regime_state` 交互项 rank-IC 差分系列。H6 双跑 bit-identical assert。
3. **沉积**：confirmatory 结果进 ledger `confirmatory:first` 行 + `docs/methods-and-results-draft.md` §5 占位升格 + RESULTS.md。draft v0.1 → **v1.0 含首条 confirmatory**。
4. **prereg 本体更新**（apply amendment #48 文本到 `docs/track-c-preregistration.md` §1.1/§10/§13，同 #47 模式；可选地由 `scripts/track_c_amend2_apply.py` 自动化，待业主定）。

---

## §4 与 P0 brief 的关系

P0 brief（`2026-08-05-track-c-confirmatory-go-brief.md`）是**决策包**（D1-D6 + 推荐一揽子 + 风险/边界）。本文档是 **amendment #48 的技术起草**（具体 config 字段 + sig + apply 脚本）。两者互补：brief 答"做什么"，amend2 答"config 层怎么落"。

---

## §5 边界（PROPOSED）

- `[F]` 未 apply 到 frozen prereg 本体（`docs/track-c-preregistration.md` 未改）；未入 ledger（dry-run only）；未跑 confirmatory OOS；未观察 E3。
- `[F]` `scripts/track_c_amend2.py` 是新文件（复用 `track_c_commit`/`track_c_amend1` 机制）；0 改动 frozen surface / src/ / tests/。
- `[I]` 业主 `--commit` 授权后，ledger 行 #48 = frozen；之后改 config = 新 ledger 行（非静默覆盖）。
- `[I]` confirmatory OOS 跑是**第二个业主动作**（d6_go：run execution still a separate owner GO）；写 ledger #48 不等于授权跑 OOS。
