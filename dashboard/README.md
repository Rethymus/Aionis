# Aionis Phase B Dashboard

A research dashboard for Aionis's Phase B results: the filed-date (`arm_state`) vs
period-end+lag (`arm_base`) cross-sectional rank-IC differential, the
publishability gate, universe coverage, and the control / robustness gates.
Built **by reusing OSS**, not reinventing.

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

The dashboard runs on **synthetic demo data** when no result dir exists yet
(`runs/results/<config_sig>/`), so it is demoable now; it switches to real data
the moment the run script calls `aionis.reporting.results.save_run(...)`.

## Views

1. **Run history** — table of `runs/ledger.jsonl` rows (ts, config_sig, event,
   verdict). Phase A rows are DA-lift evals; Phase B rows are freeze / reframe /
   universe / coverage annotations (the durable registry, pre-reg §9).
2. **Selected run** — monthly rank-IC for `arm_state` vs `arm_base`, plus the
   differential with a 95% CI band. Horizontal lines at `±0.015` (the §7
   publishability gate) and at `0`.
3. **Coverage** — OOS-resolvable universe `588/705`, hanshof-vs-pierrebrunelle
   Jaccard (~`0.93`), and the dropped wrong-entity reuses `{POM, SE, STI}`,
   pulled live from the ledger when present.
4. **Robustness** — the H6 determinism flag, the `lag_shift` and `placebo`
   control differentials (pre-reg §5), and a Harvey-Liu haircut sensitivity
   over `n_trials` (pre-reg §6).

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
| `stefan-jansen/pyfolio-reloaded` | Apache-2.0 | the IC / tear-sheet time-series plot shape (View 2) |
| `ranaroussi/quantstats` | Apache-2.0 (GitHub SPDX; the historical Commons-Clause overlay is gone on the current default branch) | the "headline metric + gate" framing — rejected for runtime to avoid any residual license ambiguity |
| `mlflow/mlflow` | Apache-2.0 | the **run-artifact layout** (one dir per run keyed by a config signature, holding param/meta JSON + binary artifacts) — `results.py` mirrors this; the ledger plays the tracking store |
| `YannickKae/Evaluating-Investment-Strategies` | CC0-1.0 | already ported into `eval.multiple_testing.harvey_liu_haircut`, reused as-is for View 4 |

The Harvey-Liu haircut sensitivity (View 4) calls the existing
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

## Wiring a real run (parent todo)

One call in `scripts/phase_b_run.py`, after the OOS rank-IC is computed:

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
