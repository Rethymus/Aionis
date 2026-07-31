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
  is recorded, while C1--C3/C5 remain owner-gated. The dashboard view extraction and owner-authorized
  C4 standalone cleanup passed review and are committed in `05ec7af`.
- **E3:** engineering may continue, but headline is **NO-GO**. No scheduler, real E2E, or forward result
  exists; shadow/headline must not observe outcome-bearing metrics before AUD-07 and owner approval.
- **agents:** wave-based supervisor pattern active: one writer per file boundary, read-only preflights in
  parallel, then independent Verifier and Reviewer. Multi-agent inference is not part of the stock-selection signal.
- **known issues:** protected historical claims may retain superseded wording; non-chronological historical CV;
  blocked market-source fallbacks and sub-2s fetch paths; Phase B A1 lock stranding; current SIC snapshot.
- **last verification (2026-07-31):** the full hermetic pytest suite passed with only existing
  forward-score warnings. Dashboard extraction repair now passes all dashboard tests, full pytest,
  repository ruff and `git diff --check`; it still needs independent verification/review before
  acceptance. Health-check cleanup retains `EastMoney` in a script comment, so it does not yet meet
  C4's strict no-reference criterion now has hermetic coverage and passes. AUD-05B re-Reviewer is
  APPROVE; dashboard import/compatibility checks and all scoped tests pass.
  AUD-01/AUD-02/AUD-03/AUD-04/AUD-05A Reviewer APPROVE. No frozen config,
  preregistration, ledger/result artifact, or forward outcome changed.
- **evidence:** `reports/audits/2026-07-31-quant-llm-research-audit.md` and `tasks/active/TASK-AUD-00-remediation-coordination.md`.
- **updated:** 2026-07-31.
