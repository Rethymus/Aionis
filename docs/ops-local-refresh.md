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

1. **SessionStart hook (PRIMARY, "update the moment ZCode connects —
   evenings only")** — `.zcode/config.json` (workspace scope, committed) fires
   `scripts/ops_evening_hook.py` on every session `startup|resume`. The hook
   EXISTS only inside the 18:00–23:59 window: outside it the launcher returns
   immediately with zero work (no guard evaluation, no state reads, no log —
   restarting ZCode during the day is observably inert; owner correction
   2026-09-08). Inside the window it makes the guard decision in ~1s and, only
   on RUN, spawns `ops_local_refresh.py --run` as a DETACHED process (survives
   the session; hooks run inline, so the launcher returns immediately; stdout
   stays empty and exit code 0 always — a launcher failure never blocks a
   session start). An in-window restart after a completed run skips with one
   audit line (`hook skip: ...`) — the once-per-day semantics held on every
   day since 2026-09-07 (exactly one `evening lane start` per day's log).
   Zero LLM tokens. Requires `uv` on PATH.
2. **Windows Task Scheduler "Aionis evening data lane" (BACKSTOP, zero
   tokens, since 2026-09-09)** — daily triggers at 18:05/19:05/…/23:05
   (StartWhenAvailable catches up after boot) invoke the same
   `ops_local_refresh.py --run`; the marker's guard makes every extra
   invocation a no-op process, and failed evenings retry automatically on
   the next hourly fire (≤3/evening). Covers the hook's blind spots (ZCode
   opened before 18:00 and kept open; hook misconfiguration; ZCode not
   opened at all that evening) WITHOUT any LLM session. Runs even when
   ZCode never opens — the PAT push does not need ZCode.
3. **ZCode cron automation (NIGHTLY REPORT ONLY, one session/evening)** —
   `35 23 * * 1-5`. Until 2026-09-09 this was `*/30 18-23` (12 sessions per
   evening, ≈90% pure "SKIP" no-ops ≈ 250k+ tokens/month); the owner
   flagged the waste and the trigger/execute/retry layers were moved to
   zero-token executors, leaving this single 23:35 session for the
   human-readable nightly report + full-board CI verification. On
   2026-10-06 it also carries the once-per-month review (see below).
4. **Weekly GitHub tripwire (`staleness-check.yml`)** — Mondays 02:00 UTC,
   ~30s of Actions time (~2 min/month). Reads the COMMITTED data_health
   snapshot; if older than 5 days, opens a deduplicated Issue; ALSO checks
   the last publish-site run's conclusion (a red run = deploy leg needs
   investigation). Covers even a fully offline local machine.
3. **Weekly GitHub tripwire (`staleness-check.yml`)** — Mondays 02:00 UTC,
   ~30s of Actions time (~2 min/month). Reads the COMMITTED data_health
   snapshot; if older than 5 days, opens a deduplicated Issue. This is the
   only layer that notices "the machine never opened in the evening for days"
   even when the local machine is fully offline.

```
SessionStart hook OR Task Scheduler OR (report-only) cron automation
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
  triggers after a success `SKIP:already-done` — but only if that run STARTED
  at/after 18:00 local (round 102): a morning/midday catch-up fetches the
  PREVIOUS session's data and must not suppress the evening lane (the 09-21
  one-day gap). A crash locks after 3 attempts (`SKIP:attempt-cap`, failed
  states only) until the next evening or human review; a stale `running`
  marker (>90min, any date) is treated as a crashed run and retried.
- **Missed fires are lost, not delayed** (host asleep at fire time — round-54
  lesson): the hook makes this near-moot (any session start in the window
  counts), and the 30-min cron covers "opened before 18:00, still open later".
- First scheduled run: **Monday 2026-09-07 evening** (note: US Labor Day —
  most EOD fetchers will honestly no-op; the lane still exercises end-to-end
  and commits whatever did change, e.g. GDELT/FRED).

## Month-duration facilities (the ≥1-month commitment)

- The cron automation is recurring (no expiry); the hook is workspace config
  committed to the repo. Both persist across ZCode restarts.
- **2026-10-06 one-shot review** rides the nightly 23:35 report session: a
  read-only monthly report (execution rate, reliability, soft-fail hotspots,
  publish-chain health, Actions-minute estimate) written to
  `reports/audits/2026-10-06-evening-lane-monthly-review.md` + a single-file
  commit, with continue/adjust recommendations for the owner.
- The staleness + publish-chain tripwires keep watching throughout.

Token economics (owner-raised concern, fixed 2026-09-09): the LLM-facing
surface shrank from ≤12 sessions/evening to exactly 1 (23:35 report);
trigger/execute/retry run as plain OS processes (hook + Task Scheduler) at
zero tokens ≈ **−92%** of the duty automation's token burn. If even the
nightly report session is unwanted, delete the ZCode automation — the
pipeline itself keeps refreshing with zero tokens, and the weekly GitHub
tripwire keeps the honest-failure signal.

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

> 逐源备役与断供切换剧本（Tiingo↔Alpaca、FRED/ALFRED、GDELT、EDGAR、baostock、
> LLM 模型退役等）见 [`source-redundancy.md`](source-redundancy.md)——本节管通道级
> 失败模式，那份管源级断供。

| Symptom | Behavior | Recovery |
|---|---|---|
| fetcher error/timeout | soft-fail, keep going (CI semantics) | next evening incremental |
| export/gate hard-fail | no commit, marker `failed`, exit 1 | auto-retry next fire; ≤3/evening |
| transient push failure (commit landed, push didn't) | **push-only recovery** (round 104): next hourly fire pushes the existing gate-verified commit — no re-fetch; mixed non-lane commits → full run | automatic; ~60 min saved per occurrence |
| push rejected (remote ahead) | `pull --rebase --autostash` first; conflict → fail loudly | human resolves; never force |
| PAT/credential expiry | push fails → attempt-cap locks; **`--doctor` layer 4 flags it**; nightly report carries doctor results (round 110) | refresh Windows credential; `--run --force` |
| data pushed but CI red on OUR commit | lane polls its own sha's publish-site+Tests conclusions (`ci` in marker+SUMMARY, round 107); nightly one-liner shows `CI(own):` | inspect the named workflow; human review |
| machine off all evening | fires lost | next evening catches up (increments are idempotent) |
| multi-day outage | — | Actions tab → "Refresh terminal data" → Run workflow (workflow_dispatch kept; 7 network steps retry ×3, round 106) |
| one-shot research automation missed (host asleep) | hourly guard + done-marker (round 105 pattern) | late manual execution stays valid (proven 10-02) |
| runner image drift (e.g. ubuntu-latest→26.04) | all 7 workflows pinned `ubuntu-24.04` (rounds 107/108b) | revisit the pin deliberately on each changelog sweep |
| unknown "is the stack healthy?" | `--doctor` seven-layer read-only preflight (round 109; layer 7 = site-repo drift, 2026-11-06) | 7/7 = walk away; any FAIL → named layer + 需人审 in that night's report |

### Data snapshot audit step (round 225, soft)

After the shelf/matrix re-pin, the lane runs `scripts/data_snapshot_audit.py`
(soft, 5-min cap): it re-hashes the 8 research-history caches against the
committed baseline (`reports/exploratory/data-snapshot-baseline.json`) —
appends are tolerated; a changed historical prefix = HISTORY REWRITTEN alarm
(exit 1 → soft-fail recorded, lane continues). This is the CRSP-tape lesson
(JFQA 2026-03) wired as a nightly tripwire: an upstream source silently
rewriting history surfaces in the next morning's soft-fail list instead of
going unnoticed. Baseline refresh (after intentional schema/format changes
only): `uv run python scripts/data_snapshot_audit.py --baseline` + an
exploratory ledger row.

### Audit-chain backup (round 170)

```bash
uv run python scripts/backup_audit_chain.py [--out D:/backups]
```

Creates a timestamped raw copy of `runs/ledger.jsonl` + a full git bundle
(all refs) in `data/backups/` (gitignored). Retention: 30 most recent
pairs. Addresses the round-155 reflection gap: the audit chain previously
existed only in this repo + GitHub. Run after any ledger-touching event or
add to a weekly schedule.

## GitHub 计费冻结应对（billing lock playbook，2026-11-06 立案）

先例：2026-08-20→09-01 首次冻结（结清后恢复）；2026-11 复发（"billing lock
#2"，commit `18001a804`）。冻结是**账户级**的——连公开仓库的 Actions 也一并
停止，"转 Public 免修账单"不成立（state/current.md §10 结论）；唯一出路是
Settings → Billing 结清/解锁。

**症状**（2026-11-05 实测 `gh run list`）：`Tests` 与 `Publish site (gh-pages)`
的 run 在 **3-4 秒**内 conclusion=failure（正常要数分钟），run 详情是 billing
类注解。看到"全仓库所有 workflow 集体秒红"即可定性为计费冻结——不要浪费
时间排查代码或 runner。

**影响面**：

- **全停**：`Tests`、`publish-site.yml`（发布）、`staleness-check.yml`（周绊网）
  及其余全部 workflow。绊网本身就是 Actions workflow——**Actions 全停时绊网
  也停**，云端信号全部失效，这正是冻结期的监测盲区（第 7 层为根治而设）。
- **不受影响**：本地 evening lane（SessionStart hook + Task Scheduler，纯本地
  进程）照常 fetch/export/gate/commit/**push**——push 走业主 PAT，不消耗
  Actions 分钟。后果是 origin/main 每晚前进、线上站点停在最后一次成功部署
  （11-02），**仓库-站点漂移**随天数累积。

**冻结期监控**（Actions 全停后，本地探测是唯一信号）：

- `--doctor` 第 7 层（site-repo drift）：本地 curl 线上
  `api/v1/panels/data_health.json` 的 `snapshot_ts`，与仓库
  `web/src/data/aionis/data_health.json` 的同名时间戳对比。线上缺失/解析失败
  → FAIL（"live site unreachable or invalid — deploy may be frozen
  (billing?)"）；线上落后仓库 >48 小时 → FAIL（"live site lags repo by N
  days — deploy frozen?"）；一致或线上更新 → PASS。网络不可达按 FAIL 诚实
  上报（fail-honest），异常在层内捕获、doctor 永不崩溃。
- 夜报（23:35 cron）随报 doctor 结果（round 110 起）：连续数晚**第 7 层 FAIL
  且其余 6 层全绿** = 典型"本地栈健康、发布被冻结"签名，提醒业主去修
  Billing（2026-11-06 实测即此形态）。

**恢复**：Settings → Billing 解锁（09-01 先例：结清后即刻恢复）。**无需手工
重部署**——`publish-site.yml` 由 push 触发，下一次 evening lane 的 push 照常
构建并发布，线上站点自动追平（第 7 层随之转 PASS）。若想解锁后立即验证而
不等晚间 lane，推一个空提交即可：`git commit --allow-empty -m "chore(site):
redeploy after billing unlock" && git push`。

### 解锁后一键恢复（recovery automation，2026-11-06 立案）

Billing 解锁本身零动作（Settings → Billing 结清即恢复）；恢复的最后一公里是
让部署链重新跑起来。三条路径按需取用：

1. **被动等通道（默认，零操作）**：下一次 evening lane 的 push（Task
   Scheduler 18:05 起每小时）照常触发 `publish-site.yml` + `Tests`，线上
   站点自动追平，doctor 第 7 层随之转 PASS。无需任何手工命令。
2. **立即验证（不等晚间 lane）**：对最新一次红 run 重跑——

   ```bash
   gh run list --limit 5        # 找最新红 Tests / Publish site (gh-pages) 的 run id
   gh run rerun --failed <run-id>
   ```

   幂等性：rerun 对**同一 commit** 重跑——`publish-site.yml` 重新构建同一
   sha 并 rsync 到 gh-pages；若站点内容无变化，`git diff --cached --quiet`
   直接 "No site changes — nothing to publish"（exit 0），**不产生重复
   部署**。若 main 在冻结期前进过，rerun 发布的是该 run 自己的 sha（数据
   截至该提交），之后的增量仍由下一次 18:05 push 补齐。
3. **冻结未解除期间的替代发布（本地冻结通道）**：
   `uv run python scripts/ops_freeze_deploy.py --dry-run`（预检 + 同步，
   不推送；确认输出后由业主决定是否 `--deploy` 真推 gh-pages——见脚本
   docstring。前置自检会拦下"本地 out 比线上旧一个月"的回退陷阱， FAIL 时
   先按提示 `pnpm build` 再试）。

**解锁时刻的自动检测**（夜报班用）：
`uv run python scripts/ops_freeze_deploy.py --check-recovery` —— 读最新
`Tests` run 结论：conclusion=success → 打印「已恢复，可停止使用冻结通道」
并**退出 2**（夜报捕获退出码 2 即宣告恢复、停止冻结通道播报）；仍锁定
（failure）或无法判定（gh 失败 / 无 run）→ **退出 0** 继续播报。对应测试：
`tests/test_ops_freeze_deploy.py` 的三种 gh 状态分支。

## Manual operations

```bash
uv run python scripts/ops_local_refresh.py --status        # marker state
uv run python scripts/ops_local_refresh.py --guard         # what triggers would do
uv run python scripts/ops_local_refresh.py --run --force   # bypass guard (human)
uv run python scripts/ops_evening_hook.py                  # simulate the hook (silent)
uv run pytest -q tests/test_ops_local_refresh.py           # lane logic tests
uv run python scripts/ops_local_refresh.py --doctor       # seven-layer preflight
```

`--doctor` (round 109; layer 7 added 2026-11-06): one read-only command that
verifies the whole stack — marker/guard sanity, Task Scheduler registration,
SessionStart hook config, git push credential (ls-remote), gh auth, the two
API env keys (names only), and site-repo drift (layer 7: the LIVE Pages
snapshot vs the committed one — see the billing-freeze playbook below). Run
it after any machine/credential change or before a renewal decision; live
result at introduction: 6/6 pass (6 layers then).

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

### Manual evidence re-exports (the 2026-09-20 near-miss rule)

Re-exporting ONE evidence artifact standalone (atlas / dossier / matrix)
leaves the COMMITTED `knowledge_shelf.json` pinning the OLD sha256 — the
shelf drift alarm (`test_knowledge_shelf_evidence_artifacts_reconcile_to_repo`)
then hard-fails the lane gate. Rules:

1. After any standalone evidence re-export, re-run the canonical chain tail
   (evidence_html -> dossier -> phase_meta -> shelf+matrix) or simply
   `--run --force` the lane, and let the gate pass BEFORE committing.
2. Never hand-edit `knowledge_shelf.json` pins — they are computed at export.
3. The gate failure text names the recovery (round 99); follow it, don't
   improvise. Archival copies under `reports/evidence/archive/v1/` are
   move-don't-delete history, never restoration sources.

## One-shot research automations: missed-fire protection (2026-10-02)

One-shot calendar automations fire exactly once; if the host is asleep at
that instant the node is LOST (runCount stays 0, lifecycle flips completed —
the 10-01 04:05 shadow-runbook incident). The data lane solved this class
with hourly repetition + an idempotence marker; research nodes now reuse the
same pattern:

- the 10-31 shadow-runbook + GO-evidence automation runs hourly
  04:05-23:05 on the day (`5 4-23 31 10 *`, recurring), gated by a
  completion marker `data/ops/shadow_1031.done` (gitignored runtime state):
  first live fire executes the NO-LEDGER runbook and writes the marker;
  every later fire replies one line and stops. Late fires remain valid (the
  prompt's frozen-history clause). A year-later recurrence is inert (marker
  present). If a node is ever lost anyway, late manual execution is valid
  and was proven on 10-02 (four steps EXIT 0, honest fail-closed, ledger
  byte-identical).

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

## Post-run one-command verification (round 191)

After any evening run (and especially a first run with new wiring),
verify REAL state instead of recalling it:

```bash
uv run python scripts/verify_channel_first_run.py [--date YYYY-MM-DD]
```

Checks (read-only): done-marker date/status, the evening's soft-fail
list, the SUMMARY `backup` field (audit-chain automation, round 172),
push + both CI workflows, and a news_feed as_of freshness probe. Exit 0
only when every check passes. Discriminance was proven against the
2026-10-02 run: the two then-unwired items (ticker_metadata cache mode,
backup field) correctly failed while the rest passed.
