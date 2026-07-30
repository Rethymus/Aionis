# TASK-STRAT Decision Brief — E2 (build) vs E3 (launch) vs other

> **决策摘要（中文 TL;DR）—— 先读这段，再看下方英文详证**
>
> **要决策什么**：B/C/D/E1 四个 null 已发表，因果预测（event→sector）愿景下一步走哪条路？
>
> **决定性算术**：
> - **E2 当回测 = 欠功率**。cutoff 门把 125 个月 OOS 压到 ~15 个月 → `ci_half≈0.025`，是发表门槛 `0.015` 的 **1.7×**；几乎检不出任何信号。
> - **E2-as-confirmatory 无论功率都是白费**：项目 §6 硬约束——E2 的任何正向必须经 E3 前向复现才可信。**没有 E3，E2 的"成功"不能成 headline。**
> - **E3 = 唯一零泄漏 + 有功率路径**；但需 **~42–62 个月**才到发表精度、**~7–16 年**才能检出中等效应；**一旦启动不可逆**（中途放弃清零累计月份）。
>
> **真正的三选一**：
>
> | 选项 | 一句话 | 泄漏 | 可逆性 |
> |---|---|---|---|
> | **(d) HOLD + 扩展 null** | 零新增泄漏，现在就可发表。**默认推荐。** | 无 | 高 |
> | **(c) E2 仅作假设生成器** | 便宜，给 E3 探路，不作 headline。 | 可缓解 / 不可识别 | 高 |
> | **(b) 立即启动 E3** | 唯一通向可信**正向**的路；日年级不可逆投入。 | 零（构造性） | **低 / 不可逆** |
> | (a) E2-as-confirmatory | **几乎从不可取**（§6 使其无意义）。 | 可缓解 | 高 |
>
> **决策框架（三档拨盘）**：泄漏容忍度（低 / 中）× 时间线（短 <1年 / 长 3–7+年）× 发表目标（null-publishable / positive-claim）。
> **唯一值得现在就投入日历的组合**：低泄漏 + 长时间线 + positive-claim → **E3**；其余基本都指向 **HOLD**。
>
> **Architect 建议：HOLD** —— 除非你明确要为一个 *positive-claim* 押注多年日历。详细证据见下方英文部分（§2 证据表、§3 功率算术、§4 泄漏分析、§7 决策框架）。

> **Type:** decision-support brief — **NOT an ADR** (no verdict recorded yet). Feeds the `tasks/active/TASK-STRAT-e2-vs-e3-decision.md` owner gate.
> **Status:** awaits owner verdict. **Default = HOLD.** Produced by the Architect role (read-only), 2026-07-30.
> **Relationship:** extends `decisions/ADR-005-e2-underpowered-e3-forward-live.md` with a decision *framework*. It does **not** re-litigate ADR-005 or any inviolable anti-leakage anchor.
> **Filing rule:** do NOT treat this as a record-once decision. A numbered ADR (`decisions/ADR-008-…`) should be written **only once the owner renders a GO / PIVOT / HOLD verdict** with its re-evaluation trigger.

---

## 1. Framing — the exact decision

**The decision:** Given that Phases B/C/D/E1 are all null and publishable (`docs/RESULTS.md`, ledger `confirmatory:first` rows), what does the owner do *next* with the remaining causal-prediction vision (the "see-through-to-essence" event→sector thesis, `decisions/ADR-005`)? Specifically: **(a)** build E2 now as a confirmatory rank-IC backtest, **(b)** launch E3 as a forward-live commit-then-reveal process, **(c)** build E2 only as a hypothesis-generator (exploratory, no confirmatory claim), or **(d)** hold and broaden the 4-null family.

**What is NOT being decided:** (i) the four already-published nulls are final and untouched; (ii) the anti-leakage anchors (config-before-result, PurgedGroupKFold+embargo, H6 determinism, PIT data) are inviolable and not on the table; (iii) the program-level hard constraint from `docs/phase-e-preregistration.md` §6 — *"E2 的正向必须 E3 前向复现才可信"* (any E2 positive must be reproduced by E3's forward track record to be credible) — is **assumed binding**, not re-litigated.

---

## 2. Evidence table (Fact / Inference / Hypothesis — strictly separated)

| # | **Fact** (cited) | **Inference** (reasoned, with confidence) | **Hypothesis** (testable, not yet evidenced) |
|---|---|---|---|
| F1 | E1 `confirmatory:first` (sig `ef321e9e…`): differential `mean_diff = −0.0028`, `se_hac = 0.004420`, `ci_half = 0.0087`, `dm_p_mbb = 0.533`, `n_months = 125`; family `multiple_testing_family_n = 4`, `publish_ci_half = 0.015` (`runs/ledger.jsonl`, E1 rows). | **(High)** Realized per-month std of the rank-IC *differential* series ≈ se_hac × √n = 0.004420 × √125 = **0.0494**. NW-HAC inflation κ ≈ 1.0 (0.0494 ≈ raw implied σ), so the differential IC series is ~serially uncorrelated month-to-month. | E2's differential σ may be *higher* than 0.0494 because arm_causal (discrete sector-broadcast) is likely less correlated with arm_base than E1's propagation column was → σ_diff(E2) may approach the pre-reg's 0.06 estimate. |
| F2 | E2 pre-reg: cutoff gate collapses the 125-month OOS window to **~10–18 post-cutoff months** (`docs/phase-e2-preregistration.md` §7; `state/blockers.md`; `decisions/ADR-005`). | **(High)** At n=15 post-cutoff months, ci_half ≈ 1.96 × 0.0494 / √15 ≈ **0.025** — about **1.7× the 0.015 gate**. Underpowered for a publishable verdict by construction. | If an allowed-pool provider cutoff ≲ 2015 exists, the full 125-month window could survive and E2 becomes powered. |
| F3 | LLM parametric memorization of pre-cutoff realized outcomes is empirically demonstrated (Lopez-Lira, Tang, Zhu 2025, arXiv:2504.14765, cited `docs/phase-e2-preregistration.md`); non-identifiability (Lopez-Lira Prop 1) and leak-freedom undecidability (Fonseca) are cited there too. | **(High)** E2's leakage is *mitigated, not eliminated*, and is *non-identifiable* — no audit can prove the residual is zero. The cutoff gate addresses "did the model see the outcome" but the **causal-edge topology itself** may be memorized from pre-cutoff narrative. | **(Untestable by construction)** Whether E2's specific sector-broadcast edges carry hindsight. The LAP audit can *bound* it but cannot resolve the non-identifiability. |
| F4 | E3 is forward-only, commit-then-reveal: prediction sha256-committed before the t+21 outcome realizes; "no future to leak" (`docs/phase-e3-preregistration.md` §2; `decisions/ADR-005`). | **(High)** E3's leakage is **zero by construction** — the memorization channel is structurally dissolved (the predicted event hasn't occurred), not merely mitigated. The clean asymmetry vs E2. | None — architectural, not empirical. |
| F5 | ERL design deliberately removed `market_impact` from LLM extraction (an LLM-filled market_impact is an architectural look-ahead leak). E2/E3 both inherit structural-only extraction. | **(Medium-High)** Structural-only discipline is consistently applied ERL→E2→E3; necessary but not sufficient per the E2 pre-reg. | Whether the closed `mechanism_keyword` enumeration fully prevents narrative-embedding leakage under strict Structured Outputs. |
| F6 | All 4 confirmatory phases null with ci_half < 0.015 (E1 tightest at 0.0087). Strategy lens: no L-S Sharpe survives family deflation; Hansen-SPA p = 0.692. Horizon sweep: B/C/D nulls hold at h=10/42. | **(High)** Efficient-markets prior holds robustly at monthly frequency across 4 axes. Prior on "any new monthly rank-IC signal is ~0 or ≤0.005" is now very strong. | The true causal effect, if it exists, is small (|δ| ≲ 0.005–0.01) — in which case **neither** E2 (underpowered) **nor** E3 (needs 100–190+ months) can detect it in a reasonable calendar. |
| F7 | Program hard constraint: any E2 positive must be E3-forward-reproduced to be credible (`docs/phase-e-preregistration.md` §6). | **(High)** Building E2 *as confirmatory* (option a) is architecturally futile: even a positive E2 backtest cannot become a credible headline without E3 anyway. E2's only durable value is as a hypothesis-generator (option c). | None — follows directly from the constraint. |

---

## 3. Power math — why E2-as-backtest is underpowered, and what "powered" costs

**Anchor quantities (cited to F1):**
- Realized differential per-month σ_diff ≈ **0.0494** (from E1 `se_hac = 0.004420` × √125; NW inflation κ ≈ 1.0).
- Pre-reg conservative single-arm anchor σ(IC) ≈ **0.06**.
- Publishability gate: ci_half < **0.015** (family n=4).

**CI half-width scaling** (κ ≈ 1, iid-like differential series — justified by F1):
> ci_half(n) ≈ 1.96 · σ_diff / √n = 0.0968 / √n

**E2 backtest, post-cutoff window (the collapse):**

| Post-cutoff months n | ci_half (realized σ) | × the 0.015 gate | Min detectable \|δ\| (5% two-sided) |
|---|---|---|---|
| 10 | 0.0306 | 2.04× | > 0.031 |
| **15 (central E2 estimate)** | **0.0250** | **1.67×** | **> 0.025** |
| 18 | 0.0228 | 1.52× | > 0.023 |

At n=15 with NW maxlag=4 the effective df are reduced, so the real CI is likely slightly *wider* than 0.025 — the underpowered verdict is conservative. **Diagnosis:** E2-as-backtest cannot reach the 0.015 gate; to reject zero it would need a differential ≥ ~0.025, i.e. **~5–8× larger** than any observed in B/C/D/E1 (|δ| = 0.0008–0.0065). Near-certainly inconclusive.

**Months for E3 to reach publishability parity (ci_half < 0.015):**

| Anchor σ | n for ci_half = 0.015 | Calendar |
|---|---|---|
| Realized σ_diff = 0.0494 | n ≈ **42 months** | ~3.5 years |
| Pre-reg conservative σ = 0.06 | n ≈ **62 months** | ~5 years |
| Pre-reg stated range | "60–120+ months" | — |

**Publishability ≠ detection power.** For 80% power to detect δ at α=0.05 (two-sided), n ≈ (2.80 · σ_diff / δ)²:

| Target δ | n required | Calendar | Verdict |
|---|---|---|---|
| 0.030 (large) | ~21 mo | ~2 yr | detectable in a reasonable window |
| 0.020 (large) | ~48 mo | ~4 yr | marginal |
| 0.015 (medium) | ~85 mo | ~7 yr | long |
| 0.010 (small, ~sanity-anchor Mkt-RF magnitude) | ~191 mo | ~16 yr | impractical |
| 0.003 (observed B/C/D/E1 magnitude) | ~2123 mo | ~177 yr | impossible |

**Honest synthesis:** E3 reaches *publishability parity* (tight CI) at ~42–62 months, but that only buys a tight null-or-large-effect verdict. E3 can realistically **detect** only a *large* effect (δ ≥ ~0.015–0.02). If the true causal signal is as small as every prior phase's differential (|δ| ≈ 0.003–0.0065, F6), E3 will also return a null even after 5+ years — a legitimate, publishable null, but not a vision-confirming positive.

---

## 4. Leakage analysis — E2 (mitigated) vs E3 (zero by construction)

**E2 residual leakage — four mitigations, one irreducible residual** (`docs/phase-e2-preregistration.md` §2):
1. **Cutoff gate** (§2.1): OOS window strictly after the frozen provider's declared cutoff. Kills the "memorized realized outcome" channel for post-cutoff events.
2. **Structural-only extraction** (§2.2, isomorphic to ERL): causal edges `(event → sic_sector, direction, mechanism_keyword, horizon_bucket)` only — **never** `market_impact`/`expected_return`/`historical_similarity`.
3. **Scheduled-event triggers** (§2.3): CPI/NFP fired by ALFRED release calendar, not post-hoc significance.
4. **LAP memory audit** (§2.4): date-only recall query, pre/post-cutoff interaction.

**Irreducible residual** (§2.5): memorization is *non-identifiable* (Lopez-Lira Prop 1 — "true predictive power" and "memorization" are observationally equivalent when the model has seen realized values) and leak-freedom is *undecidable* (Fonseca). The deepest residual: the **causal-edge topology itself** (e.g., COVID→pharma, AI→power) is plausibly memorized from pre-cutoff narrative; the cutoff gate does not address memorized *structure*, only memorized *outcomes*. E2's leakage can be bounded and audited, **never proven eliminated**.

**E3 zero-leak by construction** (`docs/phase-e3-preregistration.md` §2): the predicted forward event hasn't occurred at prediction time, so the LLM has no realized outcome to memorize — the channel is **structurally dissolved**, not mitigated. The cutoff gate is *moot* in E3. Commit-then-reveal pushes the project's "sha256-before-result" anchor to per-prediction granularity.

**The asymmetry that matters:** E2's leakage is *non-identifiable* (unprovable-absence); E3's is *architecturally zero*. A headline on E2 carries an irreducible "is this just memorized?" asterisk no audit can fully remove. A headline on E3 does not.

---

## 5. Cost & calendar

| Path | Engineering cost | Calendar to a *credible* verdict | Reversibility |
|---|---|---|---|
| **(a) E2-now-as-confirmatory** | Medium | **Never credible on its own** — §6 (F7) requires E3 reproduction of any positive; backtest ~inconclusive regardless (§3). | High (code reversible; no data committed). |
| **(b) E3-launch-now** | High (forward scheduler + forward ledger + commit-then-reveal + monthly scoring loop + 8-K earnings ingest + dashboard forward-IC tab). | **~42–62 mo** to publishability; **~7–16 yr** to detect a medium/small effect (§3). | **Low / irreversible once launched** — dropping mid-way zeros accumulated months. A sunk calendar commitment. |
| **(c) E2-as-hypothesis-generator-only** | Medium (same as (a), no confirmatory freeze). | N/A — feeds E3, no standalone verdict. | High. |
| **(d) HOLD-and-broaden-the-null** | Low (robustness extensions; Phase-B OOS-panel backlog). | Already publishable now. | High. |

**What "powered" concretely requires:** ~42–62 accumulated forward months at the realized σ_diff for a *tight* verdict; a *large* effect (δ ≥ ~0.015–0.02) for *detection*. No engineering shortcut changes the calendar — only a lower-σ anchor, higher-frequency rebalance, or an earlier-cutoff provider (E2) would move the numbers.

---

## 6. Option set

| Option | Pros | Cons | Reversibility | Leakage | Publishability |
|---|---|---|---|---|---|
| **(a) E2-now-as-confirmatory** | Implementable now; exercises the LLM causal-edge pipeline. | Near-certainly inconclusive (ci_half ~0.025); any positive non-credible without E3 (F7). | High | Mitigated, non-identifiable | Null publishable *only if* post-cutoff CI tightens (unlikely at n≈15); positive NOT publishable (blocked by §6). |
| **(b) E3-launch-now** | The **only** path to a credible positive; **zero leakage by construction**; accumulates without power cap. | Calendar years; high cost; **irreversible** sunk commitment; may still return null if the effect is small (F6). | Low (once launched) | Zero by construction | Null-or-large-effect publishable after ~42–62 mo; small-effect detection infeasible. |
| **(c) E2-as-hypothesis-generator-only** | Cheap; de-risks E3; honest framing (F7); no headline risk. | No verdict; must be clearly labeled exploratory (no `confirmatory:first` row). | High | Mitigated, non-identifiable (no claim rests on it) | N/A (exploratory feeds E3). |
| **(d) HOLD-and-broaden-the-null** | Zero new leakage; already publishable; buys time to set the dials; clears the Phase-B OOS backlog. | Does not advance the causal-prediction vision. | High | None added | **Already publishable now.** |

---

## 7. Decision framework (the rule — NOT the decision)

Three dials. **Default = HOLD (option d)** unless a dial-setting explicitly maps to another option.

- **Dial 1 — Residual-leakage tolerance:** *Low* (headline must carry zero lookahead asterisk) vs *Moderate* (a mitigated, audited, non-identifiable residual is acceptable for a *non-headline* artifact).
- **Dial 2 — Timeline horizon:** *Short* (<1 yr) vs *Long* (3–7+ yr willing to wait).
- **Dial 3 — Publishability goal:** *Null-publishable* (a rigorous null is satisfactory) vs *Positive-claim* (the goal is a credible causal-prediction positive).

| Dial setting | Recommended option | Why |
|---|---|---|
| Leakage **Low** + Timeline **Long** + goal **Positive-claim** | **(b) E3-launch-now** | Only zero-leak, powered path to a credible positive (F4, §4). |
| Leakage **Low** + Timeline **Short** + goal **Null-publishable** | **(d) HOLD-and-broaden** | No new leakage; already publishable (F6). |
| Leakage **Low** + Timeline **Short** + goal **Positive-claim** | **Conflict — no option satisfies.** E3 is the only credible-positive path but needs years. Honest answer: lower the goal to null-publishable (→ d) or extend the timeline (→ b). | Surfacing this conflict is itself the deliverable. |
| Leakage **Moderate** + Timeline **Short/Med** + goal **Hypothesis-generation** | **(c) E2-exploratory** | E2's only durable role (F7); de-risks E3 cheaply. |
| Leakage **Moderate** + goal **Positive-claim** via E2-as-confirmatory | **(a) is almost never recommended.** F7: even an E2 positive is non-credible without E3. | The only variant of (a) worth doing is (c). |

**The architectural insight to weigh:** options (a) and (b) are not peers. Because of the program §6 hard constraint (F7), **building E2-as-confirmatory cannot produce a credible positive without E3 anyway**. The real fork is between *E3-now* (commit years for a zero-leak shot at a large effect), *E2-as-exploratory* (cheap hypothesis generation feeding a future E3), and *HOLD* (publish the nulls, defer the vision). E2-as-confirmatory is largely wasted effort.

---

## 8. Evidence that would flip the call

1. **An allowed-pool provider with cutoff ≲ 2015** (GLM/SiliconFlow/ModelScope only) — the cutoff gate stops destroying power, the full 125-month window survives, **(a) E2-as-confirmatory becomes viable** (ADR-005's named re-evaluation trigger).
2. **LAP audit showing ~zero post-cutoff recall** for the pinned provider — reduces (not eliminates) the leakage concern, making E2's output more trustworthy as a hypothesis source.
3. **A positive E2 exploratory result** surviving the no-edge placebo AND cutoff-era stratification — raises the prior that a *detectable* (large) effect exists, justifying launching E3 sooner.
4. **A lower-σ IC anchor** (different target/horizon/universe yielding σ_diff ≪ 0.0494) — shrinks months-to-power for both E2 and E3.
5. **A higher-frequency forward anchor** (e.g., weekly rebalance, if PIT-safe) — accelerates E3 accumulation.

---

## Summary

Phases B/C/D/E1 are four publishable nulls; the causal-prediction vision now rests on E2/E3. The arithmetic is decisive on two points: **(i)** E2-as-backtest is underpowered — the cutoff gate collapses 125 months to ~15, yielding ci_half ≈ 0.025 (1.7× the 0.015 gate); and **(ii)** the program §6 constraint makes E2-as-confirmatory architecturally futile regardless, since any positive needs E3 reproduction to be credible. The only zero-leak, powered path to a credible *positive* is E3, and even E3 can realistically detect only a *large* effect (δ ≥ ~0.015–0.02) after ~42–62 months (publishability) to ~7–16 years (detection of a medium effect). If the true signal is as small as the four observed differentials (|δ| ≈ 0.003–0.0065), no option delivers a positive in a reasonable calendar — and a rigorous null remains the honest, publishable outcome. **Default = HOLD (option d)** until the owner sets the three dials; the only dial combination that justifies committing calendar now is *Leakage-Low + Timeline-Long + Positive-claim → E3*.

---

## References

- `state/current.md` — TASK-STRAT gate is the next decision; E2-underpowered listed as known issue; E1 sig `ef321e9e`.
- `state/blockers.md` — E2 underpowered blocks the primary confirmatory claim; owner decision required.
- `decisions/ADR-005-e2-underpowered-e3-forward-live.md` — accepted choice (E2 = hypothesis-generator, E3 = powered zero-leak); cutoff destroys power; re-eval trigger.
- `docs/phase-e2-preregistration.md` §2 (four-layer leakage control + honest §2.5 non-identifiability), §5 (reuse two_arm, pin single provider), §7 (power: 125→10-18 months, σ(IC)≈0.06).
- `docs/phase-e3-preregistration.md` §2 (zero backtest leakage, commit-then-reveal), §7 (calendar-time slowness), §8 (irreversible sunk cost).
- `docs/phase-e-preregistration.md` §6 — program hard constraint: E2 positive must be E3-forward-reproduced to be credible.
- `docs/RESULTS.md` — 3+1 nulls publishable; n=125 months; strategy-return lens no survivor (Hansen-SPA 0.692).
- `runs/ledger.jsonl` — E1 `config_committed` (`publish_ci_half:0.015`, `multiple_testing_family_n:4`); E1 `confirmatory:first`; `strategy_return`/`sensitivity_horizon` rows labeled `exploratory`.
- `memory/aionis-erl-leakage-design.md` — structural-only discipline (market_impact deliberately removed as architectural lookahead leak).
