# Interim execution-coverage ledger (evening lane, 2026-09-07 → 09-28)

> Round-103 audit: the dry run of the 2026-10-06 monthly review. Sources:
> `git log -- web/src/data/aionis` (14 lane commits) + every
> `runs/ops_local_refresh/*/run.log` SUMMARY line + marker state. Compiled
> 2026-09-28 evening; board green; live data_health snapshot = 2026-09-28.

## Per-evening ledger (16 trading evenings, Mon–Fri Beijing)

| Evening | Result | Wall | Notes |
|---|---|---|---|
| 09-07 Mon | ✅ ok | 25m | first autonomous night (Labor Day: ran for pending catch-up, as designed) |
| 09-08 Tue | ✅ ok | 33m | |
| 09-09 Wed | ✅ ok | 67m | |
| 09-10 Thu | ❌ lost | — | run died mid-flight (stale running; GBK era) — data recovered by 09-11's incremental fetch |
| 09-11 Thu | ✅ ok (attempt 4) | 27m | GBK outage fixed mid-evening by the UTF-8 patch; hourly retry carried it |
| 09-14 Mon | ✅ ok | 63m | |
| 09-15 Tue | ✅ ok | 54m | |
| 09-16 Wed | ❌ self-lock | — | contract-pin outage begins |
| 09-17 Thu | ❌ self-lock | — | " |
| 09-18 Fri | ❌ self-lock | — | " — recovered 09-20 by an authorized forced run (78 files) |
| 09-21 Mon | ⚠️ morning-only | 63m | 00:56 recovery re-dated the marker; evening lane skipped → the round-102 rule now prevents this class |
| 09-22 Tue | ✅ ok | 61m | |
| 09-23 Wed | ✅ ok | 81m | |
| 09-24 Thu | ✅ ok | 58m | |
| 09-25 Fri | ✅ ok (retry) | 37m | run1 committed but `git push` hit a transient RPC/HTTP2 disconnect at 18:57 → failed marker → 19:05 retry committed + pushed both commits. Correct failure semantics, observed in the wild. Known inefficiency: the retry re-runs the full pipeline instead of push-only (documented, accepted — the gate re-verifies) |
| 09-28 Mon | ✅ ok | 59m | |
| weekends 09-12/13, 19/20, 26/27 | correctly skipped (zero cost) | — | incl. the holiday-skip rule where clean |

## Coverage summary

- **12 successful lane executions**; primary-path evening success **11/16**;
  every missed evening's data eventually landed via the next incremental run
  (worst staleness: the 3-evening contract-pin outage).
- **All four miss classes now carry a structural fix, each battle-tested**:
  1. process death mid-run (09-10) → hourly Task-Scheduler retry + stale-running recovery (round 99)
  2. locale crashes (09-11) → PYTHONUTF8=1 + explicit encodings (round 97)
  3. stale exact-value pins (09-16..18) → drift-immune contracts (rounds 99/101)
  4. cross-midnight marker re-dating (09-21) → evening-completion rule (round 102)
- Soft-fail rate trending down: 4 (09-06) → 2 → 1 → mostly 1–2 per run
  (form_ipo/def14a/Tiingo transients; all self-healing).
- Wall time ~25–80 min (median ≈ 60m); all inside caps; Actions residual
  minutes on plan (~130–200/month projected).
- System layers verified this audit: Task Scheduler registered (next fire
  2026-09-28 21:05), evening-report automation + 10-01 shadow-runbook
  automation armed, live site data_health snapshot = today, 56 panels.

## For the 10-06 review to add

- 09-29..10-05 evenings + the 10-01 shadow-runbook interaction check
- publish-site / Tests success-rate over the full month
- Actions minutes actuals vs the 130–200/month projection
- continue/adjust recommendation
