# state/current.md — read first each session

- **version:** 0.1.0 (pyproject)
- **milestone:** 4 confirmatory nulls PUBLISHED (B/C/D/E1); horizon-robust at h∈{10,42} for all 4. E3 Slice 1/2/3/4 done (forward track).
- **TASK-STRAT verdict (ADR-008, 2026-07-30):** launch **E3 forward-live** (commit-then-reveal, the
  only zero-leakage powered path) AND **broaden the null family** in parallel. **E2-as-confirmatory
  rejected** (futile per program §6). E2-as-exploratory remains available to de-risk E3.
- **E3 causal-layer design (ADR-009, 2026-07-31):** hybrid — `arm_e13 = arm_base + E1 event propagation
  (propagate_panel, FF-12, zero-LLM) + E2-macro (frozen sign-only β, CPI+NFP, zero-LLM) + E2-event (13D/8-K
  minimal closed-enum LLM edge)`. Heavy LLM causal-chain rejected as 收支不平衡 (zero-cost vibe-coded project).
- **done:** B/C/D/E1 nulls; horizon-robust all 4 phases; strategy-return lens; dashboard v2;
  TASK-STRAT brief + verdict (ADR-008); E3 causal-layer design (ADR-009); unified workflow scaffold
  (TASK-WF01); PR #1 merged to main; E3 Slices 1–4 (forward-ledger keystone + forward PIT ingest +
  forward-commit plumbing + hybrid causal layer + forward scoring/accumulation).
- **now / next:**
  - **E3 launch** — primary workstream. **Slice 1 + Slice 2 + Slice 3 + Slice 4 DONE** on
    `feat/e3-forward-ledger` (uncommitted; ahead 2 = Slice-2 + Slice-3 commits). Slice 4 = forward scoring
    + accumulation (reveal → month rank-IC → forward differential IC + NW-HAC + MBB-DM + publishability;
    writes `runs/forward/<sig>/ic_forward.parquet` + `summary_forward.json`). Verifier PASS (pytest 506,
    0 skip) + Reviewer APPROVE (1 HIGH doc-only fixed; I1/accumulator/H6/PIT/I9 all verified correct).
    Next: Slice 5 (dashboard Forward-IC tab) → 6 (scheduler). See `docs/phase-e3-implementation-plan.md`
    + `tasks/active/TASK-E3-launch.md` + `decisions/ADR-009-e3-hybrid-causal-layer.md`.
  - **Null-broadening** — ongoing backlog (SIC vintage, more universes); low-risk, publishable.
  - **A1 (Phase B OOS panel)** — still blocked (benign `uv.lock` stranding; DROP recommended).
- **known issues:** Phase B OOS panel blocked by benign `uv.lock` stranding (see `blockers.md`); SIC
  current-snapshot (mild lookahead); **E3 launch is multi-year + irreversible once the headline
  ignites** (shadow 1–2 mo first); GLM 5h quota can throttle agent throughput.
- **last verification:** `uv run pytest -q` green (506, 0 skip); `uv run ruff check` clean; E3 Slice 4
  Verifier-PASS + Reviewer-APPROVE (I1 reveal-gate / accumulator + DM-sign / H6 vs overwrite / PIT fetcher /
  I9 separation all verified); real `runs/ledger.jsonl` still 39 lines; `runs/results/` untouched; latest confirmatory sig `ef321e9e` (E1).
- **updated:** 2026-07-31.
