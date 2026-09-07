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

Three trigger layers around one idempotent lane (guard + marker decide, never
the trigger):

1. **SessionStart hook (PRIMARY, "update the moment ZCode connects")** —
   `.zcode/config.json` (workspace scope, committed) fires
   `scripts/ops_evening_hook.py` on every session `startup|resume`. The hook
   makes the guard decision in ~1s and, only when it says RUN, spawns
   `ops_local_refresh.py --run` as a DETACHED process (survives the session;
   hooks run inline, so the launcher itself must return immediately; stdout
   stays empty and exit code 0 always — a launcher failure never blocks a
   session start). Zero LLM tokens. Requires `uv` on PATH.
2. **ZCode cron automation (BACKSTOP + REPORTER)** — recurring
   `*/30 18-23 * * 1-5` host-local. Catches the hook's blind spots (ZCode
   opened before 18:00 and kept open past it; a failed first attempt while
   the session stays open; hook misconfiguration) and produces the nightly
   human-readable one-line report. On 2026-10-06 it also carries the
   once-per-month review (see below).
3. **Weekly GitHub tripwire (`staleness-check.yml`)** — Mondays 02:00 UTC,
   ~30s of Actions time (~2 min/month). Reads the COMMITTED data_health
   snapshot; if older than 5 days, opens a deduplicated Issue. This is the
   only layer that notices "the machine never opened in the evening for days"
   even when the local machine is fully offline.

```
SessionStart hook OR cron automation (whichever hits first after 18:00)
  └─ guard: uv run scripts/ops_local_refresh.py --guard
       ├─ SKIP:<reason>  → done (hook: silent; cron: one-line reply)
       └─ RUN            → ops_local_refresh.py --run (detached, 20-60 min)
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
  triggers after a success `SKIP:already-done`; a crash locks after 3 attempts
  (`SKIP:attempt-cap`) until the next evening or human review; a stale
  `running` marker (>90min) is treated as a crashed run and retried.
- **Missed fires are lost, not delayed** (host asleep at fire time — round-54
  lesson): the hook makes this near-moot (any session start in the window
  counts), and the 30-min cron covers "opened before 18:00, still open later".
- First scheduled run: **Monday 2026-09-07 evening** (note: US Labor Day —
  most EOD fetchers will honestly no-op; the lane still exercises end-to-end
  and commits whatever did change, e.g. GDELT/FRED).

## Month-duration facilities (the ≥1-month commitment)

- The cron automation is recurring (no expiry); the hook is workspace config
  committed to the repo. Both persist across ZCode restarts.
- **2026-10-06 one-shot review** rides the nightly automation (step 0): a
  read-only monthly report (execution rate, reliability, soft-fail hotspots,
  publish-chain health, Actions-minute estimate) written to
  `reports/audits/2026-10-06-evening-lane-monthly-review.md` + a single-file
  commit, with continue/adjust recommendations for the owner.
- The staleness tripwire keeps watching throughout.

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
uv run python scripts/ops_local_refresh.py --guard         # what triggers would do
uv run python scripts/ops_local_refresh.py --run --force   # bypass guard (human)
uv run python scripts/ops_evening_hook.py                  # simulate the hook (silent)
uv run pytest -q tests/test_ops_local_refresh.py           # lane logic tests
```

In-chat: the workspace command **/refresh-data** runs the guard and (on RUN, or
SKIP + an explicit "force" from the owner) executes the lane — same red lines.

Energy refinement (2026-09-07): on US-holiday evenings (NYSE calendar via the
project's canonical `nyse_sessions`, fail-open) the guard SKIPs — but ONLY
while the last run left no catch-up work (`soft_fails` in the marker state);
holidays with pending pct-parse/price convergence still run. The calendar
check fails OPEN (treats unknown as a trading day): freshness outranks energy.

Logs: `runs/ops_local_refresh/<date>/run.log` (gitignored). Hook config
(`.zcode/config.json`) takes effect from the NEXT session start after edits.
The retired localhost:8935 preview server (round 70/75 leftover, PID killed
2026-09-06 per the no-lingering-processes rule): restartable anytime via
`npx serve` over the `web/out` junction — the live site is now the review
surface. Re-enable the CI refresh cron by restoring the `schedule:` trigger
in `refresh-terminal-data.yml` (git history of its 2026-09-06 change).

## Research appendix (2026-09-06/07): alternatives considered & platform rules

Full memo with sources, the six-way alternatives table (incl. the deferred
self-hosted-runner Plan B), token/energy model and month plan:
`reports/design/2026-09-07-evening-lane-research.md`. Summary:

Alternatives for "daily refresh without a paid server", evaluated against the
constraints (private-repo billing, token/energy budget, unattended reliability):

| Option | Verdict | Why |
|---|---|---|
| GitHub scheduled workflow (the retired lane) | ✗ | 1,300–1,700 min/month ≈ the whole 2,000 free minutes; `schedule` is best-effort: "can be delayed during periods of high loads" (top-of-hour worst) and auto-disables after 60 days of repo inactivity (docs: events-that-trigger-workflows). |
| `repository_dispatch` (local machine pokes CI, CI fetches) | ✗ | Documented pattern for external triggers (`gh api` → event_type + client_payload ≤10 props), but the expensive part is the CI RUN itself — the same minutes burn. Useful only if the local machine can fetch but not build — not our case. |
| Cloudflare Worker cron + tunnel to home machine | ✗ | The project already runs Workers (`workers/prices/`, display-only), but a tunnel must be UP for the cron to reach the machine — reintroduces a 24/7 availability requirement, i.e. the very server we don't have. |
| ZCode cron automation only (v1 of this lane) | partial | Reliable and cheap, but fires at fixed instants; a session opened at 19:47 waits until 20:00, and short open-windows can slip between fires. |
| **ZCode SessionStart hook + cron backstop (adopted)** | ✓ | "Connected ⇒ refresh": hook fires on every startup/resume in the window with zero LLM tokens; the 30-min cron covers keep-open/retry/reporting; the weekly GitHub tripwire covers total-machine-off. |

Credential notes for the unattended push (GitHub docs: creating a PAT):
fine-grained PAT scoped to this repo with `contents: write` is the
recommended shape ("we highly recommend adding an expiration"); GitHub
suggests GitHub Apps for scale — one user/one repo does not need one. The
push uses the owner's existing Windows credential; if it expires, the lane
fails on `push` and the attempt-cap locks cleanly (recover via
`git push` interactively once, then the lane self-resumes). A 90-day token
expiry straddles the month commitment with margin.

Token/energy budget of the adopted design (worst case, ZCode open
18:00–24:00): 1 hook fire (0 tokens) + ≤12 cron fires of which 1 executes
(~one agent session polling a detached process) and ≤11 skip (≈1 command +
1 line each). The heavy work — fetching, exporting, committing, pushing —
consumes zero LLM tokens by construction.

Site-level freshness audit (2026-09-06, pre-lane baseline): all 38 routes +
regime hash-tab variants + a dynamic `/stock/TSLA` sample swept on the live
deployment — zero `awaiting_fetch`, every page renders charts (36–141 SVGs)
with dates matching the panel freshness map (daily pages at 09-03/04,
frozen pages pinned by design, cadence pages on their sources' rhythms).
`/regime` is a 4-tab hub (market/positioning/taco/macro) whose tabs are
selected via URL hash — default tab is market by design. The audit also
surfaced three panels whose fetchers were wired into NO lane (13F star
managers, the 13F filer directory drifting since 08-21, and the pct_now
parse stage — live smart_money showed 120/120 null pct); all three were
added to the lane in round 91, with the A-share CSI300 builders and the
regime global/composite/meso layers documented as deliberate research-
surface exclusions.

## Boundaries (inherited anti-leakage contract)

- Display-only lane: commits exactly `web/src/data/aionis/` + `reports/evidence/`;
  never `runs/ledger.jsonl`, configs, or research surfaces.
- Ledger: display-lane `data_ingest` appends (reddit/news_feed) are discarded
  pre-commit (classifier only discards those two datasets; anything foreign is
  left untouched and reported). Formal ledger accounting stays an interactive
  owner action per protocol.
- No live/current prices into the research pipeline; the Worker stays
  display-only.
