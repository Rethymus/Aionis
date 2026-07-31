# state/handoff.md — current-pass handoff

- **round:** Dashboard → near-final-product analysis interface (5 axes), 2026-07-31.
- **this pass did:**
  - **Task pivot (owner sharpened)**: the "github page 展示方案" was a misread — the owner wants the
    EXISTING streamlit dashboard (`dashboard/app.py`) taken to a near-final-product form on 5 axes
    (**拟合质量 / 波动结构 / 曲线演化 / 事件前后差异 / 不确定性**), data = method/interaction DEMO only
    (NOT research conclusions). The GitHub Pages plan (`c2b5908`/`9575cfd`) is **PAUSED** (DRAFT留档).
  - 2 Researcher (sonnet) → quant-viz canon (pyfolio/QuantStats/López de Prado) + the existing 11-tab
    maturity map (FULL/DEMO/STUB) + open-source refs (`quantstats` Apache-2.0, `ffn` MIT — DESIGN refs
    only, NOT deps). → Planner (sonnet) 7 sub-slice plan.
  - 2 Engineer passes (sonnet) TDD:
    - **Pass A (6a-6d)**: `dashboard/theme.py` (palette + `AIONIS_TEMPLATE` + `apply_theme`); Fit Quality
      (+R² KPI, regression-line scatter, IC-by-regime box); Volatility (+Sharpe/Calmar/downside/vol-of-vol
      KPIs, return-distribution histogram); Curve Evolution (+monthly heatmap, top-drawdowns table).
    - **Pass B (6e-6g)**: Event Study **STUB REPLACED** with a demo CAR view (`_car_curve`/`_car_ci`/
      `_demo_event_windows`; CAR(−t_pre)=0 baseline; 95% CI = mean ± 1.96·std/√n across events);
      Uncertainty (+CV-fold stability box); consolidated demo-discipline test.
  - Verifier (sonnet) **PASS** (0 blockers; 576 green); Reviewer (opus) **APPROVE** (0 CRITICAL/HIGH;
    2 MEDIUM follow-ups: `app.py`=1629 lines → extract a `dashboard/views/` submodule; apply `apply_theme`
    to pre-existing chart builders for style consistency).
- **decisions**: NO new deps (metrics inline: R²/Sharpe/Calmar/downside/CAR — all simple formulas);
  demo data `np.random.default_rng(7)` + `st.warning("DEMO ... not a research conclusion.")` on every
  demo view; real-path view logic UNCHANGED (new plots are additions/demo fallbacks).
- **files**: NEW `dashboard/theme.py` + `dashboard/__init__.py` + 7 test files; MODIFIED `dashboard/app.py`
  (+~1000 lines). +59 tests (517→576, 0 skip).
- **verified**: `uv run pytest -q` **576 passed** (0 skip); `uv run ruff check` clean; `runs/ledger.jsonl`
  still **39**; 5 axes each gated by tests; demo-discipline enforced (warnings + rng=7 reproducibility +
  in-memory); formulas verified; no new deps; no fake completion.
- **next precise action**:
  - **(optional follow-up, MEDIUM)** refactor `dashboard/app.py` (1629 lines → extract `dashboard/views/`
    submodule) — not blocking.
  - **(optional follow-up, LOW)** apply `apply_theme` to pre-existing chart builders (style consistency).
  - **E3 Slice 6** (forward scheduler: NYSE month-end trigger, `scripts/forward_tick.py`) + **Slice 7**
    (E2E smoke + full I1–I9 gate suite) remain.
  - **GitHub Pages** paused (DRAFT `docs/github-pages-plan.md`); revisit if owner wants.
  - Watch the GLM 5h quota. Do NOT push without owner OK; do NOT ignite the headline until the 1–2 mo
    shadow validates GLM.
- **do NOT repeat**: do NOT confuse dashboard DEMO data with research output (clearly labeled DEMO);
  do NOT add quantstats/ffn as deps (inline formulas); do NOT touch the 4 published nulls / frozen
  pre-reg / `forward_ledger.py` / `save_run` / real-path view logic.
- **uncommitted**: dashboard-maturation changes in the working tree on `feat/e3-forward-ledger`
  (ahead 3 from the last push: Slice 5 + Pages DRAFT v0.1/v0.2); commit on owner OK.
