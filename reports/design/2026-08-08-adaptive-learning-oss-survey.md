# Adaptive-learning OSS survey — wheels to reuse for a future live-adaptive display

> Context: Aionis ran an exploratory weekly-refit experiment (truly-frozen vs
> expanding-window LightGBM). Looking AHEAD to any leakage-safe live/adaptive
> deployment, this surveys OSS wheels to REUSE (owner mandate: reuse-first, no
> reinventing). Agent dispatch hit `[1210]` twice → this is a lean opus survey
> (2 web searches); licenses flagged VERIFIED / UNVERIFIED.
>
> Banned in Aionis (license — do NOT use): vectorbt (Commons Clause),
> backtrader (GPL), mlfinlab (paid), pypbo (AGPL), nautilus_trader (LGPL).

## Findings

| Wheel | URL | License | Maintained | Fit for Aionis | Why |
|---|---|---|---|---|---|
| **river** | [online-ml/river](https://github.com/online-ml/river), [riverml.xyz](https://riverml.xyz/) | **BSD-3-Clause** (VERIFIED) | yes (active) | **MED** | The canonical online/incremental ML lib (regression, classification, drift). Permissive. BUT designed for high-frequency streaming; Aionis is monthly/weekly cross-sectional (~280 OOS pts) — likely overkill. |
| **alibi-detect** | [SeldonIO/alibi-detect](https://github.com/SeldonIO/alibi-detect) | **"source-available"** ⚠ (UNVERIFIED — was Apache-2.0; "source-available" suggests a non-OSI license change → **likely FAILS Aionis's permissive-only gate**) | yes | LOW | Drift/outlier detection. License risk → exclude unless Apache-2.0 confirmed. **Aionis already has its own `src/aionis/eval/model_drift.py` (PSI, zero-dep)** → no need. |
| **menelaus** | (see [Frouros survey, arXiv 2208.06868](https://arxiv.org/pdf/2208.06868)) | UNVERIFIED | unknown | LOW | Concept + data drift. License/maintenance unclear. Aionis's own PSI drift covers the need. |
| **scikit-learn `CalibratedClassifierCV`** | [scikit-learn](https://scikit-learn.org/stable/modules/calibration.html) | BSD-3 (in deps) | yes | HIGH (already used) | Platt/isotonic calibration — Aionis's `score_calibration.py` already wraps this. **Already reused.** |
| **qlib** | [microsoft/qlib](https://github.com/microsoft/qlib) | MIT | yes | LOW (POC'd, G3-failed) | Walk-forward backtest harness. Aionis POC'd it (2026-08-03) — baostock G3 structural fail for CN; MIT but the dual-region mount needs heavy adaptation. Aionis's own runner suffices. |

## Aionis-fit verdict (honest)

Aionis's scale is **monthly/weekly cross-sectional, ~500 stocks, ~280 OOS points** —
NOT high-frequency streaming. The streaming-first libs (river, alibi-detect) are
**overkill** here:

- **Drift detection**: Aionis already ships `src/aionis/eval/model_drift.py`
  (Population Stability Index, zero-dependency, leakage-safe). **Reuse the
  in-house wheel** — alibi-detect/menelaus would add dependency weight + a license
  risk for no marginal benefit at this cadence.
- **Adaptive calibration**: Aionis's `score_calibration.py` already wraps
  sklearn's `CalibratedClassifierCV` (BSD-3, in deps). **Already reused.**
- **Online learning**: river (BSD-3) is the one genuinely-permissive option IF a
  future deployment wants true incremental updates. But for monthly/weekly
  batch-refit (the proven-reliable path — sequential LightGBM refit), the
  project's own runner is simpler + already H6-deterministic. Adopt river ONLY if
  the use-case shifts to true streaming (it hasn't).
- **Walk-forward harness**: the project's own sequential runner
  (`scripts/track_adaptive_run.py`) works reliably (threading LightGBM races, not
  a harness gap). qlib was POC'd + found G3-non-compliant for CN. **Keep the
  in-house harness.**

## Reuse recommendation

**Minimal new dependencies.** Aionis's own lightweight, leakage-safe wheels
(`model_drift.py`, `score_calibration.py`, the sequential refit runner, the
frozen LightGBM learner) already fit its monthly/weekly scale and are H6-
deterministic. The OSS streaming libs are overkill + (alibi-detect) license-risky.
**Adopt river (BSD-3) ONLY if a future phase moves to true online/streaming
inference** — otherwise the disciplined answer is: reuse what's built, don't add
dependency weight. This is the reuse-first verdict: the best wheel is often the
one you already have, correctly scoped to your problem's actual cadence.

### Sources (VERIFIED-flagged)
- [river — online-ml/river (BSD-3)](https://github.com/online-ml/river) · [riverml.xyz](https://riverml.xyz/)
- [alibi-detect — SeldonIO (license "source-available" ⚠)](https://github.com/SeldonIO/alibi-detect)
- [Frouros drift-lib survey (arXiv 2208.06868)](https://arxiv.org/pdf/2208.06868)
- [scikit-learn Probability Calibration (BSD-3)](https://scikit-learn.org/stable/modules/calibration.html)
