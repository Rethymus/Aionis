# state/blockers.md — what is blocking and why

- **【2026-08-21 新增·需业主动作】GitHub Actions 计费失败，全部 workflow 停摆。**
  官方注解原文："The job was not started because recent account payments have failed or
  your spending limit needs to be increased. Please check the 'Billing & plans' section
  in your settings"。实证：08-20 09:00 后所有 run 5 秒内失败（deploy 32351688853、
  scheduled refresh 32423519918、本轮 deploy 32504053179）——**日更数据刷新与 Pages
  自动部署双双中断**。代码侧无恙（本轮 c83dd00 已推 origin/main，本地 pytest 0 失败 +
  tsc/build 全绿）；业主在 GitHub Settings → Billing & plans 修复付款/额度后，手动
  re-run `Deploy Static Site to GitHub Pages` 与 `Refresh terminal data` 即恢复。
- **BLS CPI/NFP live transport remains BLOCKED by policy; C1 code is implemented but not yet accepted.**
  Cache miss now fails closed in the local diff, but independent Verifier/Reviewer are still required before
  commit. No BLS adapter is allowed. See `TASK-AUD-05C-C1-disable-bls-transport.md`.
- **E3 headline is NO-GO pending live-input readiness.** Scheduler/E2E are incomplete and the current
  runner can drop the unlabeled current cross-section, fall back to the last labeled date, skip empty
  event text, omit the membership assertion, and record ambiguous provider cutoff metadata. Resolution
  path = AUD-04/AUD-05 source contracts → `TASK-AUD-06` → existing E3 Slice 6/7 → AUD-07 + owner GO.
- **E3 inferential verdict is HOLD pending AUD-07B statistical correction audit.** ADR-010 currently
  says both TOST p-values must exceed the look-specific alpha, which appears directionally reversed;
  the fixed 90% CI plus O'Brien-Fleming spending construction also needs a strong proof of sequential
  equivalence error control. No low-reasoning implementation is allowed before resolution.
- **E2 is underpowered as a backtest.** The cutoff gate collapses the 125-month OOS window to
  ~10-18 post-cutoff months → no statistical power. Resolution path = E3 forward-live (the only
  powered zero-leak route). This blocks the E-sequence's *primary confirmatory claim*; it does NOT
  block E2 as a design / hypothesis-generator. **Owner decision (TASK-STRAT) required.**
  See `../decisions/ADR-005-e2-underpowered-e3-forward-live.md`.
- **GLM 5-hour usage limit (429, recurring).** Provider quota; resets on a rolling window.
  Mitigation: model tiering (opus for high-stakes), bounded single retry, patience. Not a code
  blocker.
- **PRAW (Reddit) wrapper is authorized but not implemented.** Owner accepted the 7-gate conditions:
  internal research only, no redistribution, permanent `mode: exploratory`, and declared selection
  bias. Resolution = bounded C3 Engineer → independent Verifier → Reviewer; no live pull or research
  run is authorized by that decision. See `TASK-AUD-05C-C3-praw-wrapper-7gate.md`.
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
