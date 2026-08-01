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
- **agents:** wave-based supervisor pattern active: one writer per file boundary, read-only preflights in
  parallel, then independent Verifier and Reviewer. Multi-agent inference is not part of the stock-selection signal.
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
- **Wave-B (2026-08-01):** owner `/goal` authorized the priority offline RD program ("启用更多 agents 根据优先
  等级…各自推进"). 8 sonnet-tier tasks COMPLETE, each Engineer → independent Verifier PASS → independent
  Reviewer APPROVE → atomic commit: RD-01/02/03/11/13/14/16/17 (commits `97e5688`…`f397383`). Full hermetic
  pytest GREEN (only pre-existing forward-score warnings); `ruff check` clean; ledger 0 diff; no frozen
  surface touched; no real network/LLM/trial ran; E3 outcome unobserved. Writers serialized (parallel-writer
  race; see memory aionis-parallel-writer-race). `opus`/`fable` aliases blocked by `[1M]` resolver values →
  AUD-07B + RD-15 deferred; RD-08 HOLD (needs frozen rule table). Safe RD queue exhausted for sonnet tier.
  Not pushed. Detail: `state/handoff.md` § Wave-B FINAL.
- **updated:** 2026-08-01.
