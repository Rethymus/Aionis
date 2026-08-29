# Aionis Research Dashboard (Streamlit)

The researcher-facing quant-evaluation tool over the **real frozen run artifacts**
in `runs/results/<config_sig>/` (B/C/D/E1 confirmatory + exploratory rows in
`runs/ledger.jsonl`). The web terminal (`web/`) is the public display layer; this
dashboard is the working bench for the same numbers — it never recomputes a
frozen result (no rerun-to-significance), it only renders what `save_run(...)`
persisted.

## Launch

```bash
uv run streamlit run dashboard/app.py
```

Requires the optional `dashboard` extra (`streamlit` + `plotly`), declared in
`pyproject.toml` under `[project.optional-dependencies]`. If you installed only
the core env:

```bash
uv sync --extra dashboard
```

The dashboard runs on **labeled synthetic demo data** when no result dir exists
(`runs/results/<config_sig>/`); it switches to real data the moment a run script
calls `aionis.reporting.results.save_run(...)`.

## Views (11 tabs)

1. **Overview** — headline table + differential forest plot (per-phase treatment −
   base rank-IC, 95% HAC CI; CI brackets 0 ⇒ NULL) + CI-precision bars against
   the null-precision gate (`ci_half < 0.015`; legacy field name
   `publishable_ci_half`).
2. **Fit Quality** — cumulative IC vs random-walk band, KPI (mean / NW-HAC t /
   IC-IR / hit-rate), score-vs-return scatter + decile spread when the OOS panel
   is persisted.
3. **Volatility** — IC histogram, return distribution, underwater curve; KPI row
   computed on the IC series (annualized IC-IR, Calmar, downside deviation,
   vol-of-vol).
4. **Curve Evolution** — monthly IC heatmap (year × month), top drawdowns,
   cumulative IC with random-walk CI band, rolling 12m IC + IC-vol.
5. **Event Study** — CAR around 13D / earnings (descriptive realized drift;
   forward returns by design, not a PIT feature).
6. **Uncertainty** — differential forest + CV-fold stability + haircut pointers.
7. **Horizon Robustness** — the 4 confirmatory nulls (B/C/D/E1) re-tested at
   h=10/42 from the `sensitivity_horizon` ledger row.
8. **Coverage** — OOS-resolvable universe and membership reconciliation, pulled
   from the ledger when present.
9. **Strategy Return** — secondary/exploratory L-S lens: per-strategy Sharpe +
   DSR grid over `n_trials`, Hansen SPA, gross-of-costs disclosure.
10. **Forward IC** — E3 forward-live progress (parity months, committed-vs-
    revealed counts, cumulative forward differential IC).
11. **Run history** — `runs/ledger.jsonl` rows (ts, config_sig, event, verdict):
    the durable registry, pre-reg §9.

## Reuse accounting (permissive licenses only)

Chosen runtime stack — both verified permissive (MIT / Apache-2.0); nothing
Common-Clause / GPL / AGPL / unlicensed is pulled.

| Library | Version | License | Role | Adapted from |
|---|---|---|---|---|
| **Streamlit** | `>=1.30` (resolved 1.59.1) | **Apache-2.0** (verified `streamlit/streamlit` SPDX) | App scaffold + layout | the canonical data-app framework |
| **plotly** | `>=5.18` (resolved 6.9.0) | **MIT** (verified `plotly/plotly.py` SPDX + classifier) | rank-IC / differential charts | native plotly.py figures (no wrapper) |
| pandas / pyarrow | core deps | BSD / Apache-2.0 | parquet round-trips of the IC series | already in the pipeline |

Evaluated for **patterns** (not installed — to keep the runtime dependency
footprint minimal, per KISS/YAGNI):

| OSS | License | What we adapted (concept only) |
|---|---|---|
| `stefan-jansen/pyfolio-reloaded` | Apache-2.0 | the IC / tear-sheet time-series plot shape (fit view) |
| `ranaroussi/quantstats` | Apache-2.0 (GitHub SPDX; the historical Commons-Clause overlay is gone on the current default branch) | the "headline metric + gate" framing — rejected for runtime to avoid any residual license ambiguity |
| `mlflow/mlflow` | Apache-2.0 | the **run-artifact layout** (one dir per run keyed by a config signature, holding param/meta JSON + binary artifacts) — `results.py` mirrors this; the ledger plays the tracking store |
| `YannickKae/Evaluating-Investment-Strategies` | CC0-1.0 | already ported into `eval.multiple_testing.harvey_liu_haircut`, reused as-is for the strategy lens |

The Harvey-Liu haircut sensitivity calls the existing
`aionis.eval.multiple_testing.harvey_liu_haircut` — no new wheel added.

## Result artifacts (read by this dashboard)

Written by `aionis.reporting.results.save_run(...)` to
`runs/results/<config_sig>/`:

```
ic_state.parquet   ic_base.parquet     # monthly rank-IC series per arm
summary_state.json summary_base.json   # rank_ic_summary dicts
differential.json  controls.json       # ΔIC + CI, lag_shift/placebo gates
config.json        meta.json           # frozen config + ts / H6 flag
```

## Wiring a real run

One call in the phase run scripts (e.g. `scripts/phase_b_run.py`), after the OOS
rank-IC is computed:

```python
from aionis.reporting import results
results.save_run(
    config_sig,
    ic_state=ic_state, ic_base=ic_base,
    summary_state=summary_state, summary_base=summary_base,
    differential=differential, controls=controls,
    config=config, h6_deterministic=h6_ok,
)
```

The dashboard then picks it up automatically (sidebar "result dir" selector).
