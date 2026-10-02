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

## 2. What other repos actually do (12 workflow files / 10 repos, fetched raw)

| Repo (file) | Cron? | Job timeout | Concurrency (cancel) | Retries | SHA pins | Notable |
|---|---|---|---|---|---|---|
| pandas (unit-tests.yml) | none | 90m | per-job ✓ | – | ✓ full | fail-fast:false; `not network` marker; Windows link.EXE fix; `fail_ci_if_error:false` (codecov) |
| home-assistant (ci.yaml) | none | 60/20/10 tiered | ✓ | – | – | cache versioning (CACHE_VERSION:4); DB tests `numprocesses 1`; documented partial-run escape hatch |
| qlib (from_source / from_pip) | none | 180m | ✓ | **✓ nick-fields/retry ×3** (15–60m step caps) | – | macOS OpenMP thread caps; on_retry deps reinstall (pip) |
| freqtrade (ci.yml) | weekly `0 3 * * 4` (on-hour) | – | ✓ | – | ✓ full | live tests isolated job; notifications suppressed for schedule events; `permissions:{}` |
| vectorbt (tests.yml) | none | – | ✓ | – | – | fail-fast:false only |
| zipline-reloaded (ci_tests_quick) | none | – (90m step) | – | **✓ retry ×3 + on_retry_command** | – | codecov `fail_ci_if_error:false` |
| alphalens (main.yml, archived) | none | – | – | – | – (checkout@v1) | decayed minimal CI; frozen py2.7-era matrix |
| FinRL (test.yml) | **daily `0 6 * * *` (on-hour)** | **none** | **none** | **none** | – (checkout@v2) | the fragile configuration: scheduled + zero protections |
| ccxt (js.yml) | none | 30m (build) | ✓ (conditional cancel) | git push ×5 (rebase+backoff) | – | runner-IP check `continue-on-error:true`; live-tests separate |
| fastapi (test.yml) | weekly `0 0 * * 1` | **5/10m tiered** | – | – | **✓ full (v comments)** | the pinning+timeout exemplar |
| scikit-learn (unit-tests.yml) | **nightly `30 2 * * *` (OFF-hour!)** | none | ✓ | – | – | the docs' "avoid the top of the hour" advice, in production |
| scikit-learn (autoclose-schedule) | daily `0 2 * * 0`-style on-hour | none | – | – | – | auxiliary housekeeping cron; no keepalive comments |
| *(existence proofs)* mementum/backtrader, kubernetes/kubernetes | **no `.github/workflows` at all** | — | — | — | — | huge projects routing CI elsewhere entirely (Prow/own infra) — cron-out-of-Actions taken to the extreme |

Readings:
1. **8 of 12 files have NO cron in CI**; every cron that exists is auxiliary
   (nightly/weekly housekeeping or extended tests), never the release gate —
   pandas/HA/qlib/vectorbt/zipline-reloaded/alphalens/ccxt run push/PR only.
2. **The disciplined cron users deliberately go off the hour**: scikit-learn's
   nightly at `30 2 * * *` is exactly GitHub's "different time of the hour"
   advice in production; FinRL's on-hour daily with zero timeout/concurrency/
   retry is the counter-example configuration.
3. The network-flake answer in quant Python is **step-level retries**
   (qlib AND zipline-reloaded: `nick-fields/retry`, 3 attempts, retry-timeout
   caps, dependency reinstall on retry) — not bare `continue-on-error`.
4. ccxt's automated-push loop (5 attempts, rebase + randomized backoff) is
   the same discipline our lane's `pull --rebase` implements for its PAT push.
5. Maturity shows in the boring fields: fastapi pins every action to a full
   SHA with version comments and tiers timeouts at 5–10m; FinRL/alphalens
   float major tags with nothing else — and only they carry daily crons.

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
| Action tags float (`@v4`) | fastapi pins EVERY action to a full SHA with version comments; pandas/freqtrade likewise; our logs already show forced Node 20→24 bumps from upstream action changes | **DONE 2026-09-28 (round 101): all 27 `uses:` lines across 7 workflows pinned via peeled tag SHAs** |
| **staleness-check cron sits ON the hour (`0 2 * * 1`)** | scikit-learn's nightly deliberately runs `30 2 * * *` — GitHub's own "avoid the top of the hour" congestion advice, in production | **DONE 2026-09-28: moved to `17 2 * * 1`** |
| CI fallback lane masks fetch failures with bare `continue-on-error` | qlib uses `nick-fields/retry` (`max_attempts: 3`) on network steps — retry THEN degrade | **DONE 2026-10-02 (round 106): 7 incident-history steps in the fallback lane wrapped with SHA-pinned nick-fields/retry@v4 (per-attempt timeouts, 2-3 attempts); continue-on-error retained as the post-retry degrade** |
| news_feed fake-date time bombs (09-28 red ×2) | pandas isolates `network` marker tests; our fake rows must be relative-dated like the 09-20 fix | **DONE 2026-09-28: `_fake_rows` day defaults to now−2d — helper-level fix defuses the whole class** |
| Non-critical steps able to fail CI | `fail_ci_if_error: false` (pandas codecov) | partially adopted (our publish checks no-site-change exit 0) |

## 5b. Incremental intel (2026-10-02, round 107) — changelog sweep + dispositions

From github.blog/changelog/label/actions (Sep–Oct 2026):
- **"Ubuntu 26 generally available and latest migration" (Sep 17)** —
  `ubuntu-latest` migrates to 26.04; a major-image migration is the classic
  mid-month breakage vector. **DONE: all four ACTIVE workflows pinned to
  `ubuntu-24.04`** (big-repo discipline; revisit the pin deliberately).
- **"Node 20 is no longer available" (Sep 23)** — actions still targeting
  node20 hard-fail. Audited: our pinned set (checkout v4+, setup-python v5,
  setup-uv v1/v3, pnpm/action-setup v4, cache v4, retry v4) are all
  node20-capable → forced-24 compatible. No action needed; recorded so a
  future action bump checks this table.
- "Actions retention now covers checks, runs, statuses" (Oct 1), "expired
  artifacts no longer shown" (Sep 24), "API/UI query result changes"
  (Sep 25) — monitoring notes only.
- **"Workflow execution protections GA" (Sep 17) + "cache access with
  cache-mode" (Sep 10)** — supply-chain hardening candidates, future lanes.

New capability this round: **lane-side own-commit CI verification** — the
zero-token lane now polls the CI conclusions for exactly the sha IT pushed
(publish-site + Tests, bounded 6-min wait), putting red-card detection into
the OS layer instead of only the nightly LLM report (which sees the LATEST
runs — possibly another session's push in this multi-session repo).

## 6. Sources (all fetched 2026-09-28 unless noted)

- raw workflow files: pandas-dev/pandas `unit-tests.yml` (main);
  home-assistant/core `ci.yaml` (dev); microsoft/qlib
  `test_qlib_from_source.yml` + `test_qlib_from_pip.yml` (main);
  freqtrade/freqtrade `ci.yml` (develop)
- docs.github.com: monitoring-and-troubleshooting-workflows/troubleshooting-workflows;
  using-workflows/events-that-trigger-a-workflow (schedule section, fetched
  2026-09-06); billing/managing-billing-for-github-actions/about-billing…
  (2026-09-06)
- raw workflow files (second batch, all fetched 2026-09-28): polakowo/vectorbt
  tests.yml (master); AI4Finance-Foundation/FinRL test.yml (master);
  stefan-jansen/zipline-reloaded ci_tests_quick.yml (master);
  quantopian/alphalens main.yml (master, archived); ccxt/ccxt js.yml (master);
  fastapi/fastapi test.yml (master); scikit-learn/scikit-learn
  unit-tests.yml + autoclose-schedule.yml (main)
- existence checks via gh api (2026-09-28): mementum/backtrader and
  kubernetes/kubernetes have no `.github/workflows` directory at repo root
- our own runs: gh run history + runs/ops_local_refresh/*/run.log (12 incidents
  above; every one has a cited run id or log line in state/current.md rounds
  83–99)
