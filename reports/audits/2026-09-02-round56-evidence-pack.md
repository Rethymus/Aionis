# Membership extension + E3 readiness chain — round-56 evidence pack (2026-09-02)

Owner-takeover continuation round. Two structural blockers of the E3 forward-live
path were resolved with full evidence chains; the month-end smoke on
**2026-08-31** then reached **READINESS PASS end-to-end on real data** for the
first time (shadow mode, zero ledger writes).

## B1 — Wikipedia membership extension (`scripts/extend_membership_wikipedia.py`)

- **Gate report**: `2026-09-02-membership-gate-report.json` — 124 overlap
  months rebuilt from the first snapshot + the parsed Wikipedia change log;
  **0 unexplained mismatches**; 281 divergences all classified by the VERIFIED
  closed list `_KNOWN_UPSTREAM_DEVIATIONS` (each root-caused against raw table
  rows + upstream parquet labels: upstream current-ticker labelling WTW/EG/IQV/
  CPAY/DAY vs historical-ticker addition rows WLTW/RE/Q/FLT/CDAY; same-ticker
  successor rows FOX/FOXA; upstream last-file lag CASY/HOLX in 2026-04).
- **Append-only proof**: pre-extension copy `runs/pre_extend_copy.parquet`
  (62,655 rows) — after the write, the first 62,655 rows are bit-identical
  (`assert_frame_equal check_exact=True`).
- **Result**: +5 monthly snapshots 2026-05..2026-09 (503 constituents each;
  monthly diffs match real events, e.g. 2026-05 −HOLX/CTRA +CASY/VEEV).
  Membership max 2026-09-01 → ~20 sessions to 09-30 < the 22-session contract.
  **The round-54 structural membership blocker is resolved.**

## E3 forward-path latent defects (each found by iterated real smoke runs)

1. `predict_session_not_in_panel` was STRUCTURAL: `_clean_panel` drops
   unrealized-label rows, so the predict session could never be in the panel.
   Fix: `retain_unlabeled_from` (training semantics unchanged; default None is
   bit-for-bit historical behavior — H6).
2. Manifest writes crashed on string `filed`/`event_ts` columns
   (first reached once step 1 passed). Fix: `pd.Timestamp(...)` wraps.
3. `stakes_13d_empty` treated a legitimate no-13D month as a data failure
   (August 2026 had zero universe 13D filings). Fix: empty window = info log;
   future-dating still fails.

## Coverage gap (12 current constituents outside the frozen 585-ticker panel)

`scripts/e3_extend_prices.py` — forward-only `phase_b_prices_e3.parquet`
(585+12=597 columns) + `phase_d_sic_map_e3.parquet` (12 new SIC rows); the
frozen files are untouched (H6). Three entities required title-verified CIK
overrides (documented in the script): BK→BNY Mellon 1390777, EQR→Vivmark
Residential 906107 ("formerly: EQUITY RESIDENTIAL, filings through
2026-08-12" — renamed 2026, hence absent from the SEC ticker snapshot),
SATS→EchoStar 1415404.

## End-to-end smoke (the round's centerpiece evidence)

`2026-09-02-e3-smoke-2026-08-31-readiness-pass.log` —
`PHASE_E3_NO_LEDGER=1 e3_forward_trigger --run-date 2026-08-31`:

- month-end detected → frozen contracts loaded → freeze I_t (window 07-31..08-31)
- **223/223 events carry real EDGAR primary-document text** (as-released,
  declared-UA fetches, idempotent disk cache; AAPL/MSFT probe evidence in
  round-55-56 logs)
- panels (949,294 × 13/22) including the predict cross-section
- **READINESS PASS — all 13 gate checks** → frozen LightGBM fit → scores
  computed (config_sha256 1f4ca1b6…, scores_sha256 f29d0496…)
- `committed=False` — shadow semantics; ledger sha `91bc7640…` unchanged
  (57 rows) across ALL smoke runs v1–v5.

Operational finding for the 9-30 runbook: fresh-month GLM Pass A bursts hit
provider 429s on the tail events; per-event disk caches make reruns
incremental (self-healing). Pre-warming the text/edge caches across the month
is recommended.

## Visual + regression gates

- Full `uv run pytest -q` exit 0; `uv run ruff check` repo-wide clean.
- Streamlit dashboard (real `runs/` data): Overview + Forward IC tabs
  screenshotted and vision-verified — 4/4 NULL confirmatory differentials
  bit-match the README headline (−0.0028/−0.0065/−0.0030/−0.0008), Track C
  forward IC series renders; no DEMO labels (real result dirs).
