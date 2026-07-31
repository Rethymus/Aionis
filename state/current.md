# state/current.md — read first each session

- **version:** 0.1.0 (pyproject)
- **milestone:** 4 confirmatory nulls PUBLISHED (B/C/D/E1); horizon-robust at h∈{10,42} for all 4. E3 Slice 1/2/3 done (forward track).
- **TASK-STRAT verdict (ADR-008, 2026-07-30):** launch **E3 forward-live** (commit-then-reveal, the
  only zero-leakage powered path) AND **broaden the null family** in parallel. **E2-as-confirmatory
  rejected** (futile per program §6). E2-as-exploratory remains available to de-risk E3.
- **E3 causal-layer design (ADR-009, 2026-07-31):** hybrid — `arm_e13 = arm_base + E1 event propagation
  (propagate_panel, FF-12, zero-LLM) + E2-macro (frozen sign-only β, CPI+NFP, zero-LLM) + E2-event (13D/8-K
  minimal closed-enum LLM edge)`. Heavy LLM causal-chain rejected as 收支不平衡 (zero-cost vibe-coded project).
- **done:** B/C/D/E1 nulls; horizon-robust all 4 phases; strategy-return lens; dashboard v2;
  TASK-STRAT brief + verdict (ADR-008); E3 causal-layer design (ADR-009); unified workflow scaffold
  (TASK-WF01); PR #1 merged to main; E3 Slices 1–3 (forward-ledger keystone + forward PIT ingest +
  forward-commit plumbing + hybrid causal layer).
- **now / next:**
  - **E3 launch** — primary workstream. **Slice 1 + Slice 2 + Slice 3 DONE** on `feat/e3-forward-ledger`
    (uncommitted; ahead 1 = the Slice-2 commit). Slice 3 = forward-commit plumbing + **ADR-009 hybrid
    causal layer** (zero-LLM frozen-β macro + minimal closed-enum LLM event edge; FF-12 unified taxonomy).
    Verifier PASS (pytest 479, 0 skip) + Reviewer REQUEST-CHANGES resolved (HIGH I8 silent-mutation guard
    closed via `FROZEN_BETA_SHA256` content hash + gating test; all MEDIUM/LOW fixed; token logging landed).
    Next: Slice 4 (forward scoring + accumulation) → 5 (dashboard) / 6 (scheduler). See
    `docs/phase-e3-implementation-plan.md` + `tasks/active/TASK-E3-launch.md` + `decisions/ADR-009-e3-hybrid-causal-layer.md`.
  - **Null-broadening** — ongoing backlog (SIC vintage, more universes); low-risk, publishable.
  - **A1 (Phase B OOS panel)** — still blocked (benign `uv.lock` stranding; DROP recommended).
- **known issues:** Phase B OOS panel blocked by benign `uv.lock` stranding (see `blockers.md`); SIC
  current-snapshot (mild lookahead); **E3 launch is multi-year + irreversible once the headline
  ignites** (shadow 1–2 mo first); GLM 5h quota can throttle agent throughput.
- **last verification:** `uv run pytest -q` green (479, 0 skip); `uv run ruff check` clean; E3 Slice 3
  Verifier-PASS (independent) + Reviewer REQUEST-CHANGES resolved (HIGH I8 + MEDIUM/LOW; I5/I1 CRITICAL
  airtight); real `runs/ledger.jsonl` still 39 lines; latest confirmatory sig `ef321e9e` (E1).
- **updated:** 2026-07-31.
