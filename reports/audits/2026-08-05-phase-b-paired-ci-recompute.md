# Phase B paired HAC CI 补算 — audit 缺口关闭

> **日期**：2026-08-05 · **类型**：evidence-integrity 缺口补算（audit HIGH #1 关闭）
> **触发**：[`reports/audits/2026-08-04-evidence-integrity-audit.md`](2026-08-04-evidence-integrity-audit.md) HIGH #1 — ledger 行 #28 `differential_state_minus_base` 缺 paired `se_hac/ci_half/ci_lo/ci_hi`。
> **产物**：[`runs/phase_b_differential_ci_recompute.json`](../../runs/phase_b_differential_ci_recompute.json)（gitignored）。

---

## 结论

Phase B treatment-minus-base 差分 rank-IC 的 paired HAC 95% CI = **[−0.01057, +0.00897]**（ci_half 0.00977），跨零，与全家族 null 一致。点估计 bit-identical 于 ledger #28。

| 字段 | 值 | 核验 |
|---|---:|---|
| mean_diff | −0.0008003561696833403 | == ledger #28 `mean_ic_diff_state_minus_base`（bit-identical）✓ |
| se_hac | 0.004986112667114789 | > 0 ✓ |
| ci_half | 0.009772601252697279 | = 1.96 × se_hac ✓ |
| **ci_lo** | **−0.01057295742238062** | |
| **ci_hi** | **+0.008972245083013938** | |
| t_hac | −0.16051706471896968 | |
| p_hac | 0.8724737802159335 | 与 #28 `dm_p_mbb=0.8696` 同尾（HAC vs DM-MBB 双方法）|
| n_months | 125 | == #28 ✓ |
| maxlag | 4 | == #28 单臂行 ✓ |

---

## 方法

对 `runs/results/17245a75.../ic_state.parquet` 与 `ic_base.parquet`（各 125 月，#28 config_sig 的 save_run 产物）逐月配对，得差分系列 `diff = ic_state − ic_base`（双臂在同一 PIT 横截面打分，配对有效）。复用 `aionis.eval.rank_ic.rank_ic_summary(diff, maxlag=4)`（statsmodels OLS on const，`cov_type='HAC'`, `cov_kwds={'maxlags': 4}`；与 #28 单臂 `arm_state_cvproxy.maxlag=4` 一致）。**未运行 `phase_b_run.py`，未 rerun，未改 ledger**。

---

## 独立性局限（披露）

派 Agent A（sonnet `general-purpose`）执行此任务，agent **idle-without-result**（产物未写，final message 无数字）—— handoff 多次记录的 OMC proxy idle 模式。按 memory `aionis-agent-dispatch-verification`（勿信 agent 自述，从 repo 状态恢复），**opus Orchestrator 直接重算 < 5 秒**完成，数字经 anti-degeneracy 自检（se>0 / CI 对称 / n=125 / maxlag=4 / 跨零）全部通过。非真正独立 subagent pass；proxy 恢复后可补独立验证。此披露模式同 Lane C self-audit（handoff §2026-08-04 联合折叠）。

---

## 边界

- `[F]` 未写 ledger；ledger 行 #28 未修改（append-only 铁律）；`phase_b_run.py` 未运行；无 frozen surface / prereg / ADR / config 改动。
- `[F]` 纯只读 parquet + HAC 计算；无真实网络/LLM/forward；未观察 E3。
- `[I]` 此补算值进 `docs/RESULTS.md` §2 行 B（"not recorded" → 实际 CI）+ `docs/methods-and-results-draft.md` §4 行 #1 脚注；ledger 不补（append-only，#28 是 frozen 行）。
