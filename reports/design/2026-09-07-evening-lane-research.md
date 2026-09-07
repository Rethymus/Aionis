# Research memo: the local evening refresh lane ("temporary server" on ZCode)

> 2026-09-07 · owner decision context: no budget for a server; the developer
> machine + ZCode workspace automations act as the cron/fetch server for the
> terminal's daily data. Companion runbook: `docs/ops-local-refresh.md`.
> Sources verified via WebFetch on 2026-09-06/07 unless marked UNVERIFIED.

## 1. Constraints (from the owner's brief, quantified)

| Constraint | Number |
|---|---|
| Actions included minutes (private repo, GitHub Free) | **2,000 min/month** (docs: about-billing-for-github-actions); Linux $0.002/min beyond |
| Old scheduled refresh lane burn | 1,300–1,700 min/month (run history, state round 83) |
| Token budget | coding-plan peak before 18:00 Beijing costs ~2×; evenings chosen |
| Availability | machine/ZCode open time unfixed — "connected ⇒ refresh" semantics |
| Duration | ≥ 1 month unattended (2026-09-07 → 2026-10-06+), with a monthly review |

## 2. Platform rules that shaped the design (verified)

- **GitHub Actions billing** — private repos draw from the included 2,000
  minutes/month; our residual (ci.yml on push + publish-site per data push)
  measures ≈ 130–200 min/month (1m45s publish × ~21 + ~4m tests × ~30 pushes).
- **`schedule` event is best-effort** — "can be delayed during periods of high
  loads"; auto-disabled after 60 days of repo inactivity (docs:
  events-that-trigger-workflows). Irrelevant to the daily lane now (local
  clock), relevant only to the weekly staleness tripwire (repo is active).
- **PAT for unattended pushes** — fine-grained PAT scoped to the repo with
  `contents: write` is the recommended shape; "we highly recommend adding an
  expiration"; GitHub suggests GitHub Apps for automation at scale — one user,
  one repo does not need one (docs: creating-a-personal-access-token). Our push
  uses the owner's Windows credential; expiry fails closed at `push`, the
  attempt-cap locks, one interactive push heals it.
- **Pages limits** — published site ≤ 1 GB, soft 100 GB/month bandwidth, ≤ 10
  builds/hour (docs: about-github-pages; anchor moved during the 2026 docs
  restructure — figures are the long-standing published limits, UNVERIFIED
  against live docs on 2026-09-06 because the usage-limits page 404'd via our
  fetcher). Our load: ≤ 2 builds/day, ~200 MB site — far inside.

## 3. Alternatives considered (the design space)

| # | Option | Verdict | Evidence-based reason |
|---|---|---|---|
| 1 | GitHub scheduled workflow doing everything (the retired lane) | ✗ | burns ≈ the whole free quota; `schedule` delays + 60-day disable |
| 2 | `repository_dispatch`: local pokes CI, CI fetches | ✗ | the expensive part is the CI run itself — same minutes; useful only when the local box can't build (not our case) |
| 3 | Cloudflare Worker cron → tunnel to home machine | ✗ | needs the tunnel UP 24/7 — reintroduces the server we don't have (Workers already serve display-only live prices; kept out of the data path per AGENTS.md) |
| 4 | Self-hosted runner on the dev machine | deferred (Plan B) | free CI minutes ("Free with GitHub Actions"), jobs run on our hardware; but the runner app must be up when jobs fire, adds a persistent service + attack surface, and the job queue semantics fit "always-on" machines better than an evening-only laptop. Becomes attractive if a heavy CI lane (multi-hour full refresh) is ever needed at zero minute cost. Security note for public repos (docs: about-self-hosted-runners — "only use with private repositories" class guidance) is moot here (private repo) but reinforces care. |
| 5 | ZCode cron automation only | partial | fixed-instant fires; a session opened at 19:47 waits to 20:00; short open windows slip |
| 6 | **SessionStart hook + cron backstop + weekly GitHub tripwire (adopted)** | ✓ | literal "connected ⇒ refresh", zero LLM tokens for triggering; retry/report layer; offline alarm |

## 4. Adopted architecture (see runbook for the full diagram)

Three trigger layers around one idempotent lane (`scripts/ops_local_refresh.py`,
guard + marker): SessionStart hook (primary, `.zcode/config.json` +
`scripts/ops_evening_hook.py`), `*/30 18-23 * * 1-5` cron automation
(backstop + nightly report + the 2026-10-06 monthly review), weekly
`staleness-check.yml` (Issue when the committed data_health snapshot > 5 days).
Manual surface: `/refresh-data` workspace command. Energy refinement (2026-09-07):
US-holiday evenings skip **only when no catch-up work is pending** (last run's
`soft_fails` empty) — NYSE calendar via the project's canonical
`nyse_sessions` wrapper, fail-open to freshness.

## 5. Token / energy model

- Trigger tokens: hook = 0; cron backstop ≈ 1 command + 1 line per fire
  (≤ 12 fires/evening, only while ZCode is open; one executing fire babysits a
  detached process and reports its SUMMARY).
- The heavy work (fetch/export/commit/push) is pure shell — 0 LLM tokens by
  construction.
- Energy: warm caches make the lane incremental (~90 min worst observed,
  88 min on the 2026-09-06 validation run); holiday-with-no-catchup evenings
  skip entirely; per-step timeout caps tree-kill stragglers.
- Actions minutes: ~130–200/month residual vs 1,300–1,700 before.

## 6. Month plan & verification

- 2026-09-07 (Labor Day): first autonomous evening — runs because pct-parse
  catch-up is pending (holiday-skip correctly superseded by catch-up work).
- Nightly: guard marker prevents repeats; attempt-cap 3/evening; stale-running
  recovery 90 min.
- Weekly: staleness tripwire.
- 2026-10-06: monthly review (rides the cron automation step 0) — execution
  rate, reliability, soft-fail hotspots, publish-chain health, cost estimate,
  continue/adjust recommendation to the owner.

## 7. Sources

- docs.github.com — about-billing-for-github-actions; events-that-trigger-workflows;
  creating-a-personal-access-token; about-github-pages; about-self-hosted-runners
  (all fetched 2026-09-06/07; the Pages usage-limits anchor 404'd — figures
  marked UNVERIFIED above).
- ZCode platform — CronCreate/CronUpdate semantics (workspace automations,
  host-local cron) and the hooks system (seven events, inline execution,
  strict output schema) per the zcode-guide configuration + diagnosing skills.
- Project-internal evidence — state/current.md rounds 83–91 (minutes bomb,
  billing freeze, missed-fire round 54, validation run artifacts in
  runs/ops_local_refresh/2026-09-06/run.log).
