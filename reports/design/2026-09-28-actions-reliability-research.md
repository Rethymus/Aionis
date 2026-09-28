# Research: why GitHub Actions keep erroring and scheduled workflows never run stably

> 2026-09-28 · owner-raised /goal. Method: our own 3-week incident board as the
> empirical core, cross-checked against four high-traffic open-source repos'
> actual workflow files (fetched raw, not summaries) and GitHub's own docs.
> Sources at the end; every claim is either quoted or drawn from a fetched file.

## 1. Our own incident board (2026-09-03 → 09-28) — the empirical core

| # | Dates | Incident | Class |
|---|---|---|---|
| 1 | 09-03/04 | legacy scheduled refresh lane red ×3 (macro_drivers/DFF silent fetch loss, 2h runs, `continue-on-error` masking partial output) | long scheduled job + silent partial failure |
| 2 | 08-20→09-01 | ALL workflows dead: account billing freeze | billing gate (platform) |
| 3 | 09-05 | deploy-pages mode incompatible with legacy Pages config | config drift |
| 4 | 09-06 | stale shelf/matrix sha pins vs re-rendered artifacts (×2 reds) | derived-artifact coupling |
| 5 | 09-08 | tests passed locally (UTC+8 evening) failed on UTC runner | environment-dependent tests |
| 6 | 09-10/11 | GBK locale crashes (bare `read_text`/`write_text`/`print ✓`) | locale-dependent I/O |
| 7 | 09-11 | bare `NaN` shipped in panel JSON — Python lenient, Turbopack strict (+2 follow-on reds: TS type, schema pin) | language-spec mismatch |
| 8 | 09-15→18 | three-evening self-lock: exact-value pins vs rolling windows (def14a cluster aged out; IPO window outgrew the 1200 cap) | time bombs on moving data |
| 9 | 09-07 | staleness-check fired 07:03 for a 02:00 schedule (5h late) | platform schedule delay (documented) |
| 10 | ongoing | Tiingo/GDELT/EDGAR 429 soft-fails (recover nightly) | third-party rate limits |
| 11 | 09-20/21 | cross-midnight run re-dated the marker → Monday batch skipped a day | date-boundary logic |
| 12 | 09-28 | news_feed test fake-rows hardcoded 2026-08-25, aged out of the 30-day window (~09-24) → 2 reds tonight | time bombs (same class as #8) |

Reading: **not one incident was "GitHub Actions itself broke"** — the platform
delivered every queued job. The failures are (a) unattended long jobs
multiplying exposure to every ordinary flake, (b) test/environment assumptions
that rot with time, and (c) third-party I/O. The platform's genuine
contribution is structural: *scheduled* workflows are best-effort.

## 2. What the big repos actually do (fetched workflow files)

**None of them run cron in their core CI.**

- **pandas** (`unit-tests.yml`): push/PR only — **no schedule**. Job
  `timeout-minutes: 90`; per-job concurrency groups with
  `cancel-in-progress: true`; matrices `fail-fast: false`; actions pinned to
  commit SHAs (`checkout # v7.0.1`); flaky isolation via
  `not network`/`single_cpu` markers, parallel vs serial splits; explicit
  Windows quirks handled ("Remove link.EXE for Windows"); non-critical steps
  can't fail CI (`fail_ci_if_error: false` on codecov).
- **Home Assistant** (`ci.yaml`): push/PR only — **no schedule**.
  `timeout-minutes: 60/20/10` tiered per job; single top-level concurrency
  group with cancel; cache keys versioned (`CACHE_VERSION: 4`) and
  content-addressed ("identical content reuses the same entry"); DB-matrix
  tests run with `numprocesses 1` + long per-test timeouts; a documented
  escape hatch for partial runs; scheduled-adjacent jobs deliberately
  isolated to dev pushes.
- **qlib** (`test_qlib_from_source.yml` + `test_qlib_from_pip.yml`): push/PR
  only — **no schedule**. `timeout-minutes: 180` job + **step-level retries**
  via `nick-fields/retry` (`max_attempts: 3`, `retry_wait_seconds: 10`,
  per-step `timeout_minutes: 15–60`) — their answer to network flake;
  concurrency with cancel; macOS OpenMP thread caps to dodge segfaults.
- **freqtrade** (`ci.yml`): the ONLY cron user among the four — one auxiliary
  weekly job at `cron: '0 3 * * 4'`, with **notifications suppressed for
  schedule events** ("Discord notification can't handle schedule events") —
  i.e. they run a scheduled job but treat its unreliability as expected.
  Otherwise: concurrency+cancel, SHA-pinned actions, `permissions: {}`,
  uv-cache keyed to lockfiles, live-network tests isolated in a separate
  job, an `alls-green` gate aggregating legs.

## 3. The platform side (GitHub's own docs, quoted)

- `schedule` is best-effort: it "can be delayed during periods of high loads
  of GitHub Actions workflow runs"; "High load times include the start of
  every hour" and "some queued jobs may be dropped"; advice: "schedule your
  workflow to run at a different time of the hour" (troubleshooting-workflows
  + events-that-trigger-workflows).
- Scheduled workflows auto-disable after 60 days of repo inactivity and only
  ever run from the default branch.
- Billing/storage failures can block workflows outright (our freeze, class #2).
- GitHub-hosted runner IPs are dynamic and get flagged by third-party
  scanners — an unattended failure source for fetch-style jobs.

## 4. Synthesis — why "scheduled tasks never run stably"

1. The platform never promised stability: schedule = best-effort queue,
   dropped jobs at load peaks, hour-top congestion, inactivity kills,
   billing gates. Popular repos respond by **keeping cron out of the critical
   path** (auxiliary weekly jobs at most, with degraded expectations).
2. A scheduled job is *unattended by definition*: no human watches it fail,
   so every ordinary flake (network 429, runner hiccup, cache miss) becomes a
   silent stale-data incident unless the job self-verifies and self-reports.
3. Time-dependent code rots: locale/timezone assumptions, wall-clock pins,
   exact-value assertions on rolling data. In an unattended lane each rot
   event repeats nightly until a human intervenes — our 09-15→18 three-evening
   lock is the canonical example.
4. The stable pattern across all evidence: **event-driven CI (push/PR) +
   idempotent external scheduler + per-job timeouts + concurrency cancellation
   + retries on network steps + drift-immune assertions + an external
   tripwire**. That is precisely the architecture this project converged on
   (local hook + OS scheduler + guard/marker + push-triggered publish-site +
   weekly staleness tripwire) — the convergence is now externally validated.

## 5. Remaining adoption gaps for this repo

| Gap | Evidence pattern | Status |
|---|---|---|
| Action tags float (`@v4`) | pandas/freqtrade pin full SHAs; our logs already show forced Node 20→24 bumps from upstream action changes | open (low risk, private repo) |
| CI fallback lane masks fetch failures with bare `continue-on-error` | qlib uses `nick-fields/retry` (`max_attempts: 3`) on network steps — retry THEN degrade | open (CI fallback only; the local lane already retries hourly) |
| news_feed fake-date time bombs (tonight's red ×2) | pandas isolates `network` marker tests; our fake rows must be relative-dated like the 09-20 fix | **prescribed, awaiting authorization** (night-session red line) |
| Non-critical steps able to fail CI | `fail_ci_if_error: false` (pandas codecov) | partially adopted (our publish checks no-site-change exit 0) |

## 6. Sources (all fetched 2026-09-28 unless noted)

- raw workflow files: pandas-dev/pandas `unit-tests.yml` (main);
  home-assistant/core `ci.yaml` (dev); microsoft/qlib
  `test_qlib_from_source.yml` + `test_qlib_from_pip.yml` (main);
  freqtrade/freqtrade `ci.yml` (develop)
- docs.github.com: monitoring-and-troubleshooting-workflows/troubleshooting-workflows;
  using-workflows/events-that-trigger-a-workflow (schedule section, fetched
  2026-09-06); billing/managing-billing-for-github-actions/about-billing…
  (2026-09-06)
- our own runs: gh run history + runs/ops_local_refresh/*/run.log (12 incidents
  above; every one has a cited run id or log line in state/current.md rounds
  83–99)
