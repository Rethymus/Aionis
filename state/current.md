# state/current.md — read first each session

- **version:** 0.1.0 (pyproject)
- **milestone:** 4 confirmatory nulls PUBLISHED (B/C/D/E1); horizon-robust at h∈{10,42} for all 4. E3 Slice 1/2/3/4/5 done (forward track); dashboard matured to near-final-product on 5 axes.
- **TASK-STRAT verdict (ADR-008, 2026-07-30):** launch **E3 forward-live** (commit-then-reveal, the
  only zero-leakage powered path) AND **broaden the null family** in parallel. **E2-as-confirmatory
  rejected** (futile per program §6). E2-as-exploratory remains available to de-risk E3.
- **E3 causal-layer design (ADR-009, 2026-07-31):** hybrid — `arm_e13 = arm_base + E1 event propagation
  (propagate_panel, FF-12, zero-LLM) + E2-macro (frozen sign-only β, CPI+NFP, zero-LLM) + E2-event (13D/8-K
  minimal closed-enum LLM edge)`. Heavy LLM causal-chain rejected as 收支不平衡 (zero-cost vibe-coded project).
- **done:** B/C/D/E1 nulls; horizon-robust all 4 phases; strategy-return lens; dashboard v2;
  TASK-STRAT brief + verdict (ADR-008); E3 causal-layer design (ADR-009); unified workflow scaffold
  (TASK-WF01); PR #1 merged to main; E3 Slices 1–4 (forward-ledger keystone + forward PIT ingest +
  forward-commit plumbing + hybrid causal layer + forward scoring/accumulation + dashboard Forward-IC tab
  + dashboard matured to near-final-product on 5 axes: 拟合质量/波动结构/曲线演化/事件前后差异/不确定性).
- **now / next:**
  - **E3 launch** — primary workstream. **Slice 1 + Slice 2 + Slice 3 + Slice 4 + Slice 5 DONE** on
    `feat/e3-forward-ledger` (uncommitted; origin synced through Slice 4). Slice 5 = dashboard Forward-IC
    tab (read-only; EXPLORATORY banner; cumulative differential IC + random-walk band; committed-vs-revealed;
    months-to-parity vs the 60–120 range). Verifier PASS (pytest 517, 0 skip) + Reviewer APPROVE (0 issues).
    Next: Slice 6 (scheduler: NYSE month-end trigger) → Slice 7 (E2E + full I1–I9 gate suite). See
    `docs/phase-e3-implementation-plan.md` + `tasks/active/TASK-E3-launch.md` + `decisions/ADR-009-e3-hybrid-causal-layer.md`.
  - **Dashboard maturation (near-final-product, 5 axes)** — DONE (uncommitted). Fit Quality (+R²,
    regression scatter, IC-by-regime), Volatility (+Sharpe/Calmar/downside/vol-of-vol, return-dist),
    Curve Evolution (+monthly heatmap, top-drawdowns), Event Study (STUB→demo CAR), Uncertainty
    (+CV-fold stability). Verifier PASS (pytest 576) + Reviewer APPROVE (0 CRITICAL/HIGH; 2 MEDIUM
    follow-ups: `app.py` 1629-line → `dashboard/views/` refactor; `apply_theme` consistency). DEMO data
    clearly labeled (rng=7 + `st.warning`); real-path logic unchanged; no new deps.
  - **GitHub Pages 展示方案** — PAUSED (owner pivoted to the existing dashboard; `docs/github-pages-plan.md` v0.2 DRAFT留档).
  - **Next**: E3 **Slice 6** (scheduler) → **Slice 7** (E2E + I1–I9 gate suite); optional dashboard
    `views/` refactor. See `docs/phase-e3-implementation-plan.md` + `tasks/active/TASK-E3-launch.md`.
  - **Null-broadening** — ongoing backlog (SIC vintage, more universes); low-risk, publishable.
  - **A1 (Phase B OOS panel)** — still blocked (benign `uv.lock` stranding; DROP recommended).
- **known issues:** Phase B OOS panel blocked by benign `uv.lock` stranding (see `blockers.md`); SIC
  current-snapshot (mild lookahead); **E3 launch is multi-year + irreversible once the headline
  ignites** (shadow 1–2 mo first); GLM 5h quota can throttle agent throughput.
- **last verification:** `uv run pytest -q` green (576, 0 skip); `uv run ruff check` clean; dashboard
  maturation Verifier-PASS + Reviewer-APPROVE (0 CRITICAL/HIGH; demo anti-leakage discipline + R²/Sharpe/
  Calmar/CAR-CI formulas all verified); real `runs/ledger.jsonl` still 39 lines; `runs/results/` untouched; latest confirmatory sig `ef321e9e` (E1).
- **updated:** 2026-07-31.
