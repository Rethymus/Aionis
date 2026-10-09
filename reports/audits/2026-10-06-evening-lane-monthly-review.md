# Monthly review: evening data lane (2026-09-07 → 2026-10-06, first full month)

> Generated 2026-10-06 23:36 by the scheduled monthly-review session
> (automation-fcf3003a, per the round-105 preset scope). Base draft:
> reports/audits/2026-09-28-interim-coverage-ledger.md (09-07..09-28, reused
> per protocol — not re-derived). This file completes it with 09-29..10-06.
> Verdict asked of the owner: renewal (A/B/C/D below).

## 1. Execution rate (the promise: "every trading-day evening, once")

| Window | Trading evenings | ok_committed | Missed | Recovered how |
|---|---|---|---|---|
| 09-07..09-28 (from interim ledger) | 16 | 12 | 4 (09-10, 09-16/17/18, 09-21 evening skip) | next-evening increments; forced run 09-20; rule fix 09-28 |
| 09-29..10-06 (this review adds) | 6 | 6 (09-29/30, 10-01/02/05/06) | 0 | — |
| **Full month** | **22** | **18 ok_committed evenings** | **4** | all misses' data landed via increments; worst staleness 3 evenings |

Improvement trend is the story: 4 misses in the first 12 evenings, **0 in the
last 6** — every miss class has a battle-tested structural fix (rounds
99/101/102/104).

## 2. Reliability

- **Soft fails**: trending down — 09-06 had 4; the last two weeks average
  ~1/evening, all known transients (build_ticker_metadata baostock,
  news_feed/Tiingo 429s), all self-healing next run. Zero turned into data
  gaps.
- **The four outage classes** (process death / GBK locale / stale pins /
  cross-midnight re-dating) each carry a structural fix, each re-verified in
  production (rounds 97/99/102/104).
- **own-commit CI verification** (round 107) live since 10-02: every SUMMARY
  now carries the pushed commit's publish-site+Tests conclusions — first
  production exercise green on night one (`ci: success/success` in
  0b3a9a98's SUMMARY).

## 3. Publish chain & full-suite health

> **Correction (2026-10-09, owner-authorized post-publication edit; original
> defect flagged by the round-212 five-step verification):** the original
> table was sampled at `--limit 60`, missing the month's early runs. Full
> re-query since 09-07 (round-212 evidence):

| Workflow | success | failure | Notes |
|---|---|---|---|
| Publish site (gh-pages) | 75 | 2 | the 2 reds are 09-11/09-12 — the bare-NaN shipping incident that BECAME the strict-JSON gate (structural fix in place since); zero deploy-leg reds after 09-13 |
| Tests | 98 | 2 (in last-100 window) | the window's 2 reds are 10-05 (api_catalog→dossier cascade, fixed same hour, evidence-chain DoD hardened); the 09-28 fake-date pair sits just outside this window and is real history too — 4 total known reds across the month, each with a same-day structural fix |

The original "zero deploy reds / 09-28 pair" claims reflected the sampling
window, not the month; the health conclusion (all reds have structural,
battle-tested fixes) survives the correction.

## 4. Actions minutes vs budget

- Actual estimate: publish-site ~1m10s × ~40 runs ≈ 47 min; Tests ~4m ×
  ~65 runs ≈ 260 min → **≈ 310 min/month** total.
- vs the 130–200 projection: the projection under-counted this multi-session
  repo's push volume (other sessions land code/docs commits daily, each
  firing a 4-minute Tests run). vs the retired lane's 1,300–1,700: still
  **~80% below**. Verdict: budget exceedance is real but benign — the
  pre-adopted levers (drop the nightly report session; batch code pushes)
  exist if the owner wants the number lower.

## 5. The 10-01 shadow-runbook node (honest chapter)

- One-shot automation lost: host asleep at the single 04:05 fire instant
  (runCount=0, lifecycle completed) — round-54 pathology on a research node.
- **Recovered 2026-10-02 by authorized manual run**: ⓪a/⓪b/①/② all EXIT 0;
  ③ fail-closed on `predict_session_not_in_panel` (an honest, qualified
  conclusion — the September sessions were not yet in the panel grid; the
  runbook forbids re-running to pass); **ledger byte-identical before/after
  (0924ce2b…, 58 rows)** — NO-LEDGER discipline held.
- Consequence, stated plainly: the September shadow month has NO readiness
  PASS; the 10-31 evidence pack will present this fact honestly.
- Protection adopted: the 10-31 node now runs hourly 04:05-23:05 gated by a
  completion marker (`data/ops/shadow_1031.done`) — the data lane's mature
  pattern replicated for research nodes.

## 6. New capabilities shipped during the month (rounds 104–111)

push-only recovery (09-25-class push failures now cost minutes, not an hour)
· weekly Tests-health + publish-chain tripwires · own-commit CI conclusions
in SUMMARY+marker · `--doctor` six-layer preflight (6/6 at generation time) ·
one-shot missed-fire protection · all-repo runner+SHA pinning · drift-immune
contracts (three time bombs defused) · strict-JSON gate · failure-mode table
synced.

## 7. Renewal options (owner decides)

| Option | Effect |
|---|---|
| **A. Continue as-is (recommended)** | nightly report keeps the human-readable trail + doctor trend; everything else stays zero-token |
| B. Drop the nightly report session | fully zero-token; pipeline unaffected; weekly tripwire keeps the honest-failure signal; no nightly one-liner |
| C. Batch code pushes to cut Tests minutes | ~-150 min/month; costs multi-session immediacy |
| D. Re-enable any retired CI step | e.g. old refresh lane — NOT recommended (1,300–1,700 min/month returns) |

**Recommendation: A**, with the note that option B remains a documented
one-command walk-away whenever the nightly one-liner stops earning its keep.
