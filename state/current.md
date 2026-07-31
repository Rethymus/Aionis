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
  ADR-010 TOST p-value direction/sequential-equivalence construction requires AUD-07B strong review.
- **last verification (2026-08-01):** the full hermetic pytest suite passed with only existing
  forward-score warnings, `uv run --offline ruff check` is clean, `git diff --check` is clean, and
  the frozen prereg/ADR/config/ledger/results/data/forward diff is empty. C1/C2/C3 now have
  independent Verifier PASS and Reviewer APPROVE. No frozen config, preregistration,
  ledger/result artifact, or forward outcome changed.
- **planning (2026-08-01):** a planning-only low-reasoning development program was frozen as
  `reports/milestone/2026-08-01-low-reasoning-development-roadmap.md`, the Wave-A launch brief,
  `TASK-RD-00..17` and strong-only `TASK-AUD-07B`. The first offline wave is estimated at
  10.75–16 Engineer hours. The final unattended prompt narrows execution to C1/C2/C3 plus
  RD-04/05/06/07/09/10/12, includes context/token controls, and passed independent planning Review.
  Wave-A execution is in progress under the owner-provided Goal prompt; Group A transport closures
  are ready for commit.
- **evidence:** `reports/audits/2026-07-31-quant-llm-research-audit.md` and `tasks/active/TASK-AUD-00-remediation-coordination.md`.
- **updated:** 2026-08-01.
