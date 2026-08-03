# state/current.md — read first each session

- **version:** 0.1.0 (pyproject)
- **milestone:** B/C/D/E1 ledger results and h={10,42} sensitivity exist; E3 Slices 1–5 and the
  near-final dashboard are implemented. The 2026-07-31 quant+LLM audit reclassifies the historical
  evidence as **purged cross-fitted/CV-proxy**, not chronological/live OOS.
- **research verdict:** no B/C/D/E1 treatment arm shows reliable positive incremental rank-IC under
  the frozen nine-column baseline. Phase B has no recorded paired differential CI; Phase C is not
  strictly equivalent within post-hoc ±0.015; none of the four headline arms uses LLM features.
- **active:** `TASK-AUD-00` remediation program. AUD-01 and AUD-03 are COMPLETE after independent Verifier PASS
  and Reviewer APPROVE. AUD-04 is also COMPLETE after repair re-Verifier PASS and Reviewer APPROVE. AUD-02
  documentation reconciliation and AUD-05A are COMPLETE after independent Verifier PASS and Reviewer APPROVE.
  AUD-05B is COMPLETE after re-Verifier PASS and authorized re-Reviewer APPROVE. AUD-05C disposition
  is recorded. C1, C2 and C3 are COMPLETE after owner authorization, Engineer evidence, independent
  Verifier PASS and Reviewer APPROVE. C5 remains owner-gated. The dashboard view extraction and
  owner-authorized C4 standalone cleanup passed review and are committed in `7dede9b`.
- **E3:** engineering may continue, but headline is **NO-GO**. No scheduler, real E2E, or forward result
  exists; shadow/headline must not observe outcome-bearing metrics before AUD-07 and owner approval.
- **agents:** supervisor+worker protocol codified in `docs/orchestration-protocol.md` (ADR-012): opus
  Orchestrator + low-freq opus Supervisor (gates only) + sonnet `executor`/haiku workers (serialized,
  ≤2 concurrent) + independent `verifier`/`code-reviewer`/`qa-tester` lanes; dispatch via
  `scripts/orchestrate_dispatch.py`. One writer per file boundary still binds. Multi-agent inference
  is not part of the stock-selection signal.
- **known issues:** protected historical claims may retain superseded wording; non-chronological historical CV;
  blocked market-source fallbacks and sub-2s fetch paths; Phase B A1 lock stranding; current SIC snapshot;
  ADR-010 TOST p-value direction/sequential-equivalence construction CONFIRMED BROKEN by AUD-07B (2 CRITICAL, double-opus review); E3 verdict/headline HOLD pending owner-authorized ADR-010 + prereg §7 amendment.
- **last verification (2026-08-01):** Wave-A complete. The full hermetic pytest suite passes (zero skips;
  only the existing forward-score warnings), `uv run --offline ruff check` is clean, `git diff --check` is
  clean, and the frozen prereg/ADR/config/ledger/results/data/forward diff is empty. C1/C2/C3 and
  RD-04/05/06/07/09/10/12 each have independent Verifier PASS + Reviewer APPROVE; committed as `6085e92`
  (Group A), `2653907` (Group B), `5f884a3` (Group C). No frozen config, preregistration, ledger/result
  artifact, or forward outcome changed; no real network/LLM/research/forward script ran.
- **planning (2026-08-01):** a planning-only low-reasoning development program was frozen as
  `reports/milestone/2026-08-01-low-reasoning-development-roadmap.md`, the Wave-A launch brief,
  `TASK-RD-00..17` and strong-only `TASK-AUD-07B`. **Wave-A has executed under the owner-provided Goal
  prompt: C1/C2/C3 + RD-04/05/06/07/09/10/12 are all COMPLETE** (independent Verifier PASS + Reviewer
  APPROVE each; RD-07 byte-stability, RD-10 window/std, and RD-12 manifest-oracle findings were fixed
  and re-gated). RD-01/02/03/08/11/13..17 remain PLANNED for future waves. No real
  network/LLM/data/trial ran; no frozen surface, ledger, result, or E3 outcome changed.
- **evidence:** `reports/audits/2026-07-31-quant-llm-research-audit.md` and `tasks/active/TASK-AUD-00-remediation-coordination.md`.
- **strategic review (2026-08-02):** deep-dive on "是否跑偏 + 七主题低成本覆盖" → `reports/2026-08-02-strategic-review-coverage-and-alignment.md`. Verdict: direction sound; two失调 (目标叙事双轨未裁断; 治理复杂度>研究产出). Produced 6 design artifacts under `reports/design/` (Track A/B slice plans, slice review, qlib-fork-vs-library POC, wheel-mount design pack, reuse-catalog v2) + `src/aionis/eval/ff5_residual.py` (挂接③ FF5 residual + Amihud, 18 tests green, ruff clean; exploratory utility, **not wired to pipeline, writes no ledger**). **Owner decision (2026-08-02):** Track B (seven-theme platform) adopted + new prereg/frozen config → `decisions/ADR-011-track-b-seven-theme-platform.md` + `docs/track-b-preregistration.md` (PROPOSED). First slice 挂接③ (FF5 residual) done. **Pending:** owner freezes Track B config sha256 before any real-data result. B/C/D/E1 frozen surfaces untouched; no real network/LLM/trial ran.
- **Wave-B (2026-08-01):** owner `/goal` authorized the priority offline RD program ("启用更多 agents 根据优先
  等级…各自推进"). 8 sonnet-tier tasks COMPLETE, each Engineer → independent Verifier PASS → independent
  Reviewer APPROVE → atomic commit: RD-01/02/03/11/13/14/16/17 (commits `97e5688`…`f397383`). Full hermetic
  pytest GREEN (only pre-existing forward-score warnings); `ruff check` clean; ledger 0 diff; no frozen
  surface touched; no real network/LLM/trial ran; E3 outcome unobserved. Writers serialized (parallel-writer
  race; see memory aionis-parallel-writer-race). `opus`/`fable` aliases blocked by `[1M]` resolver values →
  AUD-07B + RD-15 deferred; RD-08 HOLD (needs frozen rule table). Safe RD queue exhausted for sonnet tier.
  Not pushed. Detail: `state/handoff.md` § Wave-B FINAL.
- **updated:** 2026-08-03. **Orchestration protocol + reuse-first batch all committed & pushed; full hermetic
  suite back to 1352 passed / 0 failed.** **Track B 首个 rank-IC（2026-08-02, treatment 臂, config #41）**: mean_ic 0.0055, CI (-0.021, 0.033), p=0.689 null; DM -1.78/p=0.079 边际（vs 等权）。**差分（#41 treatment - #42 price-only, headline）**: mean_diff 0.0076, CI (-0.004, 0.020) 跨零, p=0.219 → 未显著优于 price-only（null，符合 null-favored）；CI 上界 0.020 > SESOI 0.010 → 不构成严格等价（需更多样本）。
- **orchestration (2026-08-03):** `ADR-012` + `docs/orchestration-protocol.md` + `scripts/orchestrate_dispatch.py`
  (11/11 tests green, ruff clean) + dispatch-contract template landed — owner chose **local task files = issues**
  (zero GitHub surface). Lane model = opus Orchestrator + low-freq opus Supervisor (监工) + sonnet/haiku workers
  (serialized) + independent verifier/reviewer/e2e lanes; 6-layer denoised dispatch; anti-leakage guardrails binding.
  Committed `daa92e8`. **Wave validation**: ORCH-01 macro cumulative-preserve test (COMMITTED `8d19b28`) — first
  dispatch wave: executor succeeded, reviewer lane hit an idle-without-verdict harness gap → protocol §8 hardened
  (`83d9d61`); ORCH-02 REJECTED (`3ad4710`) — premise was a grep-suffix miss (8-K already covered); also found a
  `[1210]`-failed agent can leave partial work in the tree → §8 hardened again. **`/goal` reuse-first batch**:
  `f6e0536` DRY the 3 forward collectors' persist tail into `_common.persist_snapshot` (byte-identical ledger
  output); `e6c71ec` static-site tests aligned to the Track B page (was 12 failing) + hermetic `--out-dir` so
  tests never touch `site/` WIP. **Full hermetic suite: 1352 passed / 0 failed; ruff clean.** Track-B uncommitted
  WIP untouched throughout; no frozen surface / ledger / data touched; no real network/LLM/trial ran.
