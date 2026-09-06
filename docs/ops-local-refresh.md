# Ops: local evening refresh lane (the "temporary server")

> Since 2026-09-06. Owner decision: no paid server — the developer machine, woken
> on Beijing trading-day evenings via a ZCode workspace automation, IS the cron
> server for the terminal's daily data refresh. Target: run unattended ≥1 month.

## Why this exists (the cost math)

- Repo is **private** → Actions minutes are billed against the included
  **2,000 min/month** (GitHub Free; Linux runners $0.002/min beyond).
- The retired `refresh-terminal-data.yml` cron lane consumed **1,300–1,700
  min/month** by itself (≈2h per evening, cold caches) — one billing hiccup away
  from a frozen account (the 2026-08-20→09-01 billing freeze was exactly this).
- The local lane runs the same (superset) pipeline on warm local caches for
  **0 Actions minutes**. Residual CI per evening: `ci.yml` (tests, on push) +
  `publish-site.yml` (build + gh-pages publish, fired by our PAT push) ≈
  **300–600 min/month** total — comfortably inside the free quota.
- GitHub cron pitfalls no longer apply to the daily refresh (scheduled workflows
  get delayed at high load and are auto-disabled after 60 days of repo
  inactivity); scheduling now lives in the ZCode workspace, host-local clock.

## Architecture

```
ZCode automation (*/20 18-23 * * 1-5, host-local = Beijing evening)
  └─ agent runs: uv run python scripts/ops_local_refresh.py --guard
       ├─ SKIP:<reason>  → reply one line, done for this fire (~1 tool call)
       └─ RUN            → ops_local_refresh.py --run (background, 20–60 min)
            ├─ fetchers (CI lane order + local superset; all bounded + polite)
            ├─ export_terminal_data + evidence chain (canonical order)
            ├─ JSON validity + display contract gate (pytest)
            ├─ discard display-only ledger appends (reddit/news data_ingest;
            │   exactly what the CI ephemeral runner did implicitly)
            ├─ git add web/src/data/aionis + reports/evidence → commit
            ├─ pull --rebase --autostash → push origin main
            └─ marker data/ops/local_refresh_state.json (once-per-evening)
  push (owner PAT, NOT GITHUB_TOKEN) fires publish-site.yml on GitHub
  └─ pnpm build (mirrors panels → public/api/v1) → rsync → gh-pages → Pages
```

- **Marker**: `data/ops/local_refresh_state.json` (gitignored). Same-evening
  fires after a success `SKIP:already-done`; a crash locks after 3 attempts
  (`SKIP:attempt-cap`) until the next evening or human review.
- **Missed fires are lost, not delayed** (host asleep at fire time — round-54
  lesson): hence every 20 min across the whole 18:00–23:59 window, and the guard
  makes extra fires nearly free.
- First scheduled run: **Monday 2026-09-07 evening** (note: US Labor Day —
  most EOD fetchers will honestly no-op; the lane still exercises end-to-end and
  commits whatever did change, e.g. GDELT/FRED).

## What the deployed site needs (freshness inventory)

From the live data-health panel (verified 2026-09-06, visually + payload):

- **25 daily panels** — themes, theme_signals, market_context, macro_drivers,
  taco, form4, form8k, news_feed, executives, ipo, form_d, def14a,
  def14a_persons, filing_stream, politician_trades(+tx), reddit(+trending),
  stakes_13g, ark, theme_etfs, lineage_graph, party_index, ledger_audit,
  headline_provenance.
- **11 cadence panels** — cot (CFTC weekly), smart_money (13D), form13f×3
  (quarterly), freight_taco (BTS ~2-month lag), korea_proxy (weekly), 
  companies_dir, knowledge_shelf, evidence_matrix, provider_vintage.
- **20 frozen panels** — NEVER advance in this lane by design (recomputing them
  from newer data would be rerun-to-significance; the only legal path forward is
  E3 forward-live accumulation or a new pre-registered phase).

Freshness semantics at Beijing evening: the latest completed US session closed
~04:00 Beijing that morning, so evening runs publish previous-close EOD +
same-day filings/macro/news. Intraday prices stay live via the Cloudflare
Worker (display-only), unchanged.

## Failure modes & recovery

| Symptom | Behavior | Recovery |
|---|---|---|
| fetcher error/timeout | soft-fail, keep going (CI semantics) | next evening incremental |
| export/gate hard-fail | no commit, marker `failed`, exit 1 | auto-retry next fire; ≤3/evening |
| push rejected (remote ahead) | `pull --rebase --autostash` first; conflict → fail loudly | human resolves; never force |
| PAT/credential expiry | push fails → attempt-cap locks | refresh Windows credential; `--run --force` |
| machine off all evening | fires lost | next evening catches up (increments are idempotent) |
| multi-day outage | — | Actions tab → "Refresh terminal data" → Run workflow (workflow_dispatch kept) |

## Manual operations

```bash
uv run python scripts/ops_local_refresh.py --status        # marker state
uv run python scripts/ops_local_refresh.py --guard         # what cron would do
uv run python scripts/ops_local_refresh.py --run --force   # bypass guard (human)
uv run pytest -q tests/test_ops_local_refresh.py           # lane logic tests
```

Logs: `runs/ops_local_refresh/<date>/run.log` (gitignored). Re-enable the CI
cron by restoring the `schedule:` trigger in `refresh-terminal-data.yml`
(kept verbatim in git history of this file's 2026-09-06 change).

## Boundaries (inherited anti-leakage contract)

- Display-only lane: commits exactly `web/src/data/aionis/` + `reports/evidence/`;
  never `runs/ledger.jsonl`, configs, or research surfaces.
- Ledger: display-lane `data_ingest` appends (reddit/news_feed) are discarded
  pre-commit (classifier only discards those two datasets; anything foreign is
  left untouched and reported). Formal ledger accounting stays an interactive
  owner action per protocol.
- No live/current prices into the research pipeline; the Worker stays
  display-only.
