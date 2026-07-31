# state/blockers.md — what is blocking and why

- **BLS CPI/NFP live transport is BLOCKED.** BLS is blocked per CLAUDE.md data-source constraints (“Blocked: yfinance/Yahoo, BLS, Stooq”). Resolution = C1: disable BLS live transport in `ingest/event_text.py:_fetch_text()` (CPI/NFP branch); cache miss → fail-closed; no BLS adapter allowed. See `TASK-AUD-05C-C1-disable-bls-transport.md`.
- **E3 headline is NO-GO pending live-input readiness.** Scheduler/E2E are incomplete and the current
  runner can drop the unlabeled current cross-section, fall back to the last labeled date, skip empty
  event text, omit the membership assertion, and record ambiguous provider cutoff metadata. Resolution
  path = AUD-04/AUD-05 source contracts → `TASK-AUD-06` → existing E3 Slice 6/7 → AUD-07 + owner GO.
- **E2 is underpowered as a backtest.** The cutoff gate collapses the 125-month OOS window to
  ~10-18 post-cutoff months → no statistical power. Resolution path = E3 forward-live (the only
  powered zero-leak route). This blocks the E-sequence's *primary confirmatory claim*; it does NOT
  block E2 as a design / hypothesis-generator. **Owner decision (TASK-STRAT) required.**
  See `../decisions/ADR-005-e2-underpowered-e3-forward-live.md`.
- **GLM 5-hour usage limit (429, recurring).** Provider quota; resets on a rolling window.
  Mitigation: model tiering (opus for high-stakes), bounded single retry, patience. Not a code
  blocker.
- **PRAW (Reddit) wrapper is OWNER-HELD pending 7-gate clearance.** PRAW wrapper integration requires 7-gate data-intake rubric clearance (`docs/data-intake-rubric.md`), particularly G6 (selection-honesty: retail-attention bias) and Reddit ToS/content license approval. Resolution = owner decision on G1-G7 → if APPROVE, C3 wrapper task proceeds; if REJECT, disable PRAW live transport. See `TASK-AUD-05C-C3-praw-wrapper-7gate.md`.
- **Kenneth French / Fama-French data intake is OWNER-HELD.** `features/selection_panel.py:fama_french_daily` uses `pandas_datareader.get_data_famafrench()` (SDK-owned HTTP, no shared policy). Resolution = owner data-intake review; until approved, cache miss BLOCKED or disable. See AUD-05C disposition table.
- **Model API transport (≥2s rule scope) is OWNER-HELD.** GLM/SiliconFlow/ModelScope model APIs (GLMEmbedder, GLMCausalEdgeClient, OpenAICompatClient, ProviderRouter) need owner clarification: does the ≥2s host-spacing rule apply to model APIs (SDK-exempt) or all HTTP calls? Resolution = owner decision on politeness rule scope; if ≥2s applies, implementation needed. See `TASK-AUD-05C-C5-model-api-transport-disposition.md`.
- **Phase B OOS panel blocked by `uv.lock` stranding (benign).** The A1 same-sig guard
  fired as designed: Phase B's frozen sig `17245a75…` was computed under the pre-Phase-C
  `uv.lock` (`e045a023…`), while C/D/E1 + the current tree use `ee985437…` (the lock was
  updated in commit `1e57335` for the Reddit/PRAW stack). The drift is **non-load-bearing** —
  only `praw` / `prawcore` / `websocket-client` / `update-checker` / `defusedxml` were added;
  `lightgbm`/`pandas`/`numpy`/`pyarrow`/`scikit-learn`/`purgedcv` versions are unchanged →
  **Phase B's IC series is still bit-identically reproducible**; only the sig string moved (the
  blanket `uv_lock_sha256` guard caught it). `phase_b_run.py` already carries the correct
  `PHASE_B_NO_LEDGER` gate + additive oos wiring (uncommitted, ruff/305-tests clean). Resolution
  is an **owner decision**: DROP (cosmetic; **recommended**) · restore `e045a023…` lock for one
  rerun · re-freeze B under current lock (2nd baseline → needs ADR) · narrow the config sig to
  load-bearing versions only (architectural, affects all phases). Not a blocker for the 4-null headline.
