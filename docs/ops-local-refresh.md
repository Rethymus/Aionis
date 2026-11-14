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
| data pushed but CI red on OUR commit | lane polls its own sha's publish-site+Tests conclusions (`ci` in marker+SUMMARY, round 107); 2026-11-11 起 Actions 停用期记 `paused(actions-disabled)`（轮 129 短接）；nightly one-liner shows `CI(own):` | inspect the named workflow; human review |
| machine off all evening | fires lost | next evening catches up (increments are idempotent) |
| multi-day outage | — | Actions tab → "Refresh terminal data" → Run workflow (workflow_dispatch kept; 7 network steps retry ×3, round 106) |
| one-shot research automation missed (host asleep) | hourly guard + done-marker (round 105 pattern) | late manual execution stays valid (proven 10-02) |
| runner image drift (e.g. ubuntu-latest→26.04) | all 7 workflows pinned `ubuntu-24.04` (rounds 107/108b) | revisit the pin deliberately on each changelog sweep |
| unknown "is the stack healthy?" | `--doctor` nine-layer read-only preflight (round 109; layer 7 = site-repo drift 2026-11-06, layer 8 = marker deadman 2026-11-11, layer 9 = env-lock drift 2026-11-13) | 9/9 = walk away; any FAIL → named layer + 需人审 in that night's report |

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

## 失败处置矩阵与节奏（值班协议落点，2026-11-11 轮 126）

> 分工：上游「Failure modes & recovery」表管**通道行为与恢复机制**；本节管
> **值班分诊与节奏固化**——信号出现后归哪类、谁在哪个节奏里做什么。
> 本节为纯文档（值班协议层），不新增任何自动化、班次、常驻进程或稳态 token。
> 矩阵的规则建模借 StackStorm `trigger→criteria→action` 三元组
> （Apache-2.0；仅借鉴模式，**不部署平台**）。super-agent 三映射的出处见
> `reports/design/2026-11-11-super-agent-integration.md` §2/§4。

### Fast Path 分诊（2026-11-11 轮 126，可运行）

确定性 Python 先滤噪、LLM 只接分诊后的真问题——分诊在 23:35 唯一 LLM 会话**之前**
完成（`ops_local_refresh.py` 收尾处 gh 只读探针 + `triage_ci`/`triage_state`），稳态
token 不增反降（夜报上下文更小）。三分类语义：

| 分类 | 规则 | 处置 |
|---|---|---|
| `platform-failure` | CI run **<60s 红** 且平台签名确认（注解含 billing issue，或 job **零步定义**=billing 锁签名） | 归并一条已知线，**不进夜报正文细节**（钥匙在业主，见 billing playbook） |
| `infra-transient` | `soft_fails`/persistent 软失败、push 瞬态错误（既有 retry-soft / push-only recovery 面） | 走既有重试面，夜报一行如实 |
| `code-defect` | 其余一切（含**无法测量/未确认**的快速红——宁进人眼不猜） | 进夜报+按处置矩阵行动 |

- 快速红若无平台签名确认，**保守归 `code-defect`**（人审），绝不猜测归类。
- 夜报上下文包：`uv run python scripts/ops_local_refresh.py --triage`（只读+刷新
  `runs/ops_local_refresh/<date>/night_package.json`）——近 24h 事实内联、历史深度
  只留路径引用（Inline & Spill）。SessionStart 钩子在 SKIP 路径（含 23:35 报告
  会话自身的启动）零网络刷新该包，报告会话总能读到当晚最新分诊。
- `--status`/SUMMARY 自 2026-11-11 起带 `ci_triage` 字段；marker 的陈旧 `note`
  在每次 attempt 启动时清除（轮 99 时代残留曾存活至 2026-11 marker）。

### 处置矩阵（trigger → criteria → action）

| Trigger（信号） | Criteria（归类规则） | Action（处置+落点） |
|---|---|---|
| 晚间通道 `soft_fails` 非空（429/帽类/单源抖动） | 软失败=设计内自愈，CI 语义继续 | 零动作；夜报如实列名。**连续 ≥2 晚同类**才升级为 Thread 叙述并处方修复（先例：retry-soft 机制） |
| 通道 HARD-FAIL（契约门/守卫自锁，如 form8k cap 类） | **门按设计工作**——拒绝放行是防泄漏胜利，不是事故 | 禁止「顺手放宽门」：修帽/修门=显式提交+测试钉（先例 `5a1075f650`）；当晚 attempt-cap 自锁等次日自动重试 |
| Actions **全体** 3-4 秒内 failure | billing 注解 / job 零步执行 = 计费冻结签名 | 业主钥匙（见下方 billing playbook）；本地通道与 PAT push 不受影响，照常运行 |
| 单一 workflow 红、非秒级 | 真实缺陷或时变断言腐烂 | 归入 CI-红 Thread（见下）逐条修复；修复必须带测试钉（先例：news_feed 时间炸弹、IPO 帽感知） |
| ledger 异常（行数缩/历史前缀变/孤儿行） | append-only 受威胁或 worktree 孤儿 | **立即呈报业主裁决**（归并/弃置均不可逆）；工程侧零代办，严禁任何自动「清理」（先例：-wj 孤儿 2 行，轮 120） |
| 数据快照绊网 HISTORY REWRITTEN | 上游改史（CRSP 类教训） | soft-fail 记录+晨报可见，通道不阻塞；基线刷新=有意变更专用流程（见上节）+探索性账本行 |

### 四档节奏表

| 节奏 | 内容 | 载体 |
|---|---|---|
| **晚间** | 分诊（上表）+ 23:35 夜报班（全牌核验+doctor 九层+ci(own) 一行总结；**唯一稳态 LLM 会话**） | SessionStart 钩子 + Windows 计划任务 18:05-23:05 兜底 |
| **每周** | **Watchdog 外部核对**（`uv run python scripts/monthly_review.py --weekly`：7 工作流健康分诊+ledger config_committed-before-result 抽查+原地打转检测+提案闭环对账[gen2 条目 3 并入]；零 Actions 依赖，冻结期照常工作）+ staleness 绊网（每日 02:37 UTC，离整点；round 126 每日化）+ 发布链健康步；解锁日有 billing 滞留红（锁中存量零步红 + 当日一条）：rerun 一次再判（见 playbook） | **固定载体=每周五晚 23:35 夜报班前置确定性步 `--weekly`**（零 LLM，exit 码与发现进夜报正文；默认落盘锚点 `runs/ops_local_refresh/<date>/weekly_watchdog.md` 由 gen2 条目 3 代码默认值承载，`--out` 可覆盖——治「--weekly 无固定触发载体与落盘锚点」缺口，不长新班次）+ 夜报班提示词模板补一行「周五先跑 --weekly」（ZCode 工作区自动化配置，非仓库文件，工程侧零代码）+ `staleness-check.yml`（Actions；冻结期此信号全停，Watchdog 顶上） |
| **每月** | 复盘教训循环：`scripts/monthly_review.py`（执行率/可靠性/软失败热点/发布链健康）+ **`--propose` 前置步**（gen2 自进化引擎：确定性规则表零 LLM 产提案卡片 stdout/--out，产物由人工/月末会话粘贴 `state/backlog.md` 候选区——引擎对 backlog **只读**；治「月度产出不回流 backlog、改进提案无固定入口」缺口）+ 教训沉淀为 runbook 行/守卫测试（「每课一守卫」惯例；块内格式契约见下节）+ **月末会话对四档机制本身的有界复盘问题**（「四档接线/watchdog 是否原地打转或偏离值班目标？」一行结论，与 gen2 条目 4 watchdog 问题同款形态） | 月报 rides 23:35 夜报班，零新增会话；`--propose` 为月末会话前确定性执行，同样零 LLM |
| **值班协议** | 钥匙区盯守：GitHub billing 解锁、freeze 通道真推许可、账本孤儿裁决——清单见 `reports/design/2026-11-11-super-agent-integration.md` §5；任何钥匙到位后按 playbook 顺序动作 | 人工（业主）；值班自动化只呈报不代决 |

**稳态 token 预算声明（gen2 轮 128 入册）**：上表的 gen2 接线全部跑在**既有班次内**
——LLM 调用面维持两班不变（23:35 夜报单会话 + 月末复盘会话）；`--weekly` /
`--propose` / 提案闭环对账 / threads 折叠全部为确定性步骤**零 LLM**；platform-failure
折叠（gen2 条目 2）使夜报上下文净降。**零新班次、零常驻进程、零新依赖**。引擎
「循环不停」≠自主无限制：每环写权限止于候选文件与 state 记录（出处：
`reports/design/2026-11-11-super-agent-gen2.md` §4 守护 / §6）。

**长周期迭代：按名复跑 aionis-iterate（2026-11-11 入册）**——业主长周期指令的
字面落地通道，骨架已由主会话保存为项目级工作流 `aionis-iterate`
（`.zcode/workflows/aionis-iterate.dwf.ts`；参数 `mission` / `deliverable_path`）。
**触发时机（按需，任一即启）**：①业主 `/goal` 「继续」类长周期指令；
②`--propose` 提案卡积压（月末候选区多卡待施工）；③值班发现多轮施工主题
（同主题连续多轮未收口，`thread:spin` 同款信号）。**决策洞语义**：运行触及
决策洞（含 `mission` / `deliverable_path` 的裁量与验收裁决）**需主会话在场**
作答——按名复跑在主会话内发起并值守，不进夜间无人值守班次。**稳态 token**：
单次运行本身消耗大（多施工员会话），**按需触发、不进固定班次**——稳态预算
（上文声明）不含此项；它不是班次，是显式人工触发的工作流复跑，与「零新班次」
不冲突。

### 值班协议行为准则（super-agent 三映射，纯文档采纳）

1. **Inline & Spill（夜报=自包含上下文包）**：近 24h 变更内联进夜报正文；月报、
   ADR、设计报告一律只留**路径引用**不内联——防 handoff/state 膨胀
   （出处：https://zhuanlan.zhihu.com/p/2099987320443237060 与
   https://mp.weixin.qq.com/s/lcIkBMOKHSvkRYELgkduMg 的 Aionis 映射；
   微信正文 2026-11-11 复核实测可读：curl HTTP 200、js_content×18）。
2. **Thread 稳定 ID 归组**：CI-红、守卫失败、ledger 异常各归一条 Thread 叙述——
   夜报与 handoff 按类**续写**既有 Thread，不逐条新起会话/小节；轮 128 起续写
   引用下方登记表的稳定 ID（机器可查）
   （出处：https://zhuanlan.zhihu.com/p/2099987320443237060 与
   https://linux.do/t/topic/3109398）。
3. **投机执行红线**：23:35 夜报班**可以预草** handoff/复盘文本（供人工验收后
   采用）；但**任何触及 `runs/ledger.jsonl` 或冻结配置的写入必须人工确认 +
   显式 ledger 行**——杜绝「静默修复」改账本，守 `config_committed` BEFORE
   result 红线（出处：https://mp.weixin.qq.com/s/lcIkBMOKHSvkRYELgduMg）。

**Thread 稳定 ID 登记表（gen2 轮 128 起）**——「按类续写」由人工纪律变为**机器可查**
（grep 可验）：夜报包 threads 桶（gen2 条目 2 起逐条挂 ID）与 handoff 轮次条目引用
同一组 ID 续写，不另起编号体系。

| 稳定 ID | 归入信号（对应上方分诊/处置矩阵） | 实例后缀 |
|---|---|---|
| `thread:ci-red` | 单一 workflow 红、非秒级（code-defect 桶） | `thread:ci-red:<workflow>` |
| `thread:guard-fail` | 契约门/守卫自锁（HARD-FAIL 桶） | `thread:guard-fail:<step>` |
| `thread:platform-billing` | 全体秒级红/零步红（platform-failure 桶 → 钥匙区，见 `reports/design/2026-11-11-super-agent-integration.md` §5；归并单线不展开） | —（按类归并，不逐 workflow） |
| `thread:ledger-anomaly` | 行数缩/历史前缀变/孤儿行（业主裁决区） | — |
| `thread:spin` | 原地打转（`--weekly` spin 命中；连续 ≥2 晚同类软失败升级的 Thread 叙述） | — |

**handoff 轮次记录规范（轮 128 起）**：轮次条目涉及上述五类信号时，条目内**引用对应
thread: 稳定 ID 续写**（如「续 `thread:platform-billing`：…」），不逐条新起小节——
按类续写自此可由 grep 验证，不再依赖人工纪律（出处：
`reports/design/2026-11-11-super-agent-gen2.md` §5 条目 1 / §6）。

**handoff 轮次条目三行结构化字段（patch-unit-fields，2026-11-14 轮 147 首例）**
——hermes-patches 五列卡的 Aionis 化（backlog 延伸索引㉜；Patch/Surface/Purpose/
Evidence/Rollback 五列中，叙事段承载 Patch/Purpose，结构化三行取 surface/evidence/
rollback）：报告仍叙事、底账结构化，锚债跟踪从「通读全文」变「按卡检索」。红线：
**只增不改**——handoff 旧条目零回改（append-only 人读账本不破坏）；新条目在叙事段
外补三行；evidence 统一四级标签 **Verified / Partially verified / Code present only /
Risk**（语义同 ㉜：存在≠生效、部分验证≠已验证），口径=「跑过的报 rc、没跑的如实
not-run」。格式（轮次叙事 bullet 末尾、缩进三行子条目）：

- `surface:` 触碰面清单（文件:行/节，逗号分隔；docs-only 面如实注记）
- `evidence:` 四级标签（多条目批=逐条目标签）+ 关键实跑命令与 rc；未跑项如实 not-run
- `rollback:` 回滚方式——docs/state 批=git revert 对应 commit；handoff 条目自身=
  append-only 勘误节追加不回改（沿轮 8 §7+轮 10/11 hunk errata 先例）

### 判别层/生成层分层（值班协议认知固化，2026-11-12 轮 130-续；Jev 专题条目 4，docs-only）

值班协议按两层固化——System 1/2 仅作快/慢分层的认知类比**命名**，止步于分层事实，
不宣称认知架构（「内部世界模型」叙事不采用）：

- **判别层（确定性规则引擎，快、零 LLM）**：`--weekly` 看门狗、`--propose` 提案
  引擎（`scripts/monthly_review.py:1742` argparse help：zero LLM, zero network）、
  Fast Path `--triage` 分诊、夜报包组装——规则表判别红牌/信号；引擎不归类者交
  人工归类（`monthly_review.py:895`）。
- **生成层（月末 LLM 会话，慢、唯一生成面）**：月末复盘/教训撰写/Watchdog 有界
  问题作答（`WATCHDOG_BOUNDED_QUESTION`，`monthly_review.py:1453`）；预算仍为
  单场 23:35 LLM 会话（`monthly_review.py:1274` Budget 注）——分层**不新增**
  会话/进程/依赖。
- **不引入外部判别 API**：判别层只由本地确定性代码构成；接入 Jev API /
  typesafe-sdk 违 provider 红线（LLM pool = GLM/SiliconFlow/ModelScope ONLY，
  AGENTS.md）且无许可证白名单轮子支撑（`docs/data-license-allowlist.md` 零命中）。
  消歧义结论与同构/过度类比两栏裁决见 `reports/audits/2026-11-12-iterate-round.md`
  Jev 章节；Jev 指认规则见 `state/backlog.md`「名词指认资料」区。
- **引用锚与取向注记（2026-11-12 append，仅补引不重做）**：学术锚 RLCD
  （arXiv:2307.12950，Yang et al.，ICLR 2024）——判别器反馈即改进信号，Jev 消歧
  报告同构点 2 的机器化依据；官方无公开代码 repo，仅文档引用。外部旁证 Luo 2025
  （独著，PMC12736879，Sensors）：确定性结构作 LLM 护栏（procedural guardrails）
  为既有模式——仅借「确定性护栏」模式、非同构证据（该文按快慢轴取
  FSM=System 1 / LLM=System 2，与本节命名同向，差异在其 LLM 仍在交互环内）。
  **取向差异（防误引错向）**：多数 2025 实践把 LLM 放快环（System 1 快环）+
  外部确定性控制当 System 2；Aionis 相反——判别=本地确定性规则引擎占值班环，
  生成=月末单场 LLM 会话（出环）；引用外部文献一律以本取向为准，勿按外部取向
  倒读本分层。
- **GLM json_object 枚举协议一手注记（2026-11-12 append，round 131 {answer,p}
  协议依据；仅补引不重做）**：生成层有界打分协议与 GLM 官方结构化输出文档的
  情感分析示例完全同形——官方示例即「sentiment 三选一枚举 + confidence 0-1」
  （`response_format={"type": "json_object"}` + system 消息内描述期望 JSON 结构；
  <https://docs.bigmodel.cn/cn/guide/capabilities/struct-output>，provider 池内
  唯一一手同形支撑）。**限定（防误读为强约束）**：GLM 是 json_object 模式而非
  strict json_schema 服务端强制——只保证返回可解析 JSON，字段结构靠
  system/prompt 描述约束（官方 Schema 示例亦以客户端 jsonschema 校验兜底）——
  故 `parse_bounded_answer` 的 format-miss 诚实降级兜底
  （`scripts/monthly_review.py:1462-1485`：不可解析/越界均降级为诚实标记、
  原文留档）**必须保留**，不因官方模式存在而移除。输出为单行 {answer,p}，
  约十 token 量级，落在既有月末单场 23:35 会话预算内；本注记零新增依赖、
  零新增调用面，仅描述既有 bounded question 子任务。
- **判别/生成成本结构对照（量化引用锚，2026-11-12 append，round 131 调研条目 3；
  仅补引不重做）**：外部锚——TypeSafe 发布博文的成本/延迟对照（**厂商自述、
  自称偏高端**，仅作量级参照、非独立复核的实证）：LLM output token 成本 ~5x
  input；确定性代码 70-500ms vs LLM 生成 3-329s；文内自报 193.6x/444.6x 量级差
  ——与本节「判别=快、确定性、零 token vs 生成=慢、唯一 token 面」取向同向。
  仓库内先行量化案例可直接并引（一手实测，比厂商自述硬）：2026-09-09 夜报 cron
  从 12 会话/晚（≈90% SKIP no-op ≈ 250k+ tokens/月）收缩为零 token 执行器 +
  单场 23:35 会话（本文件 `:50-56`）；token 面收缩 ≈ **−92%**（本文件 `:113`）
  ——分层取向在仓库已有落地先例，外部博文只补量级感。

**运维调用面盘点（round 131；「任务语境下对 --propose/--triage 降 token」是伪命题
的如实记录——两者本就零 LLM，无 token 可降）**：

| 调用面 | 构成与锚 | token 面 |
|---|---|---|
| 唯一 LLM 面 | 月末单场 23:35 会话：复盘/教训撰写/bounded question 作答（`monthly_review.py:1274` Budget 注） | 运维全部 token 消耗所在 |
| 零 LLM 确定性面 | `--propose`（`monthly_review.py:1742`：zero LLM, zero network）、`--triage`/`classify_run_row`（`ops_local_refresh.py:558-576` 纯规则分诊）、`--weekly` 看门狗、夜报包组装 | 恒零——「降 token」伪命题 |
| 可下探面（选择类子任务，三选） | bounded question 枚举化（`monthly_review.py:1453` + `:1422-1445` 解析兜底）；lessons `event:` 四操作定档（`monthly_review.py:1488` lesson_seeds 播种，写入方定档）；propose 卡 S/M/L 定档复核（`monthly_review.py:862-967`） | 唯一真实下探面——均在月末单场会话内，枚举/定档化不新增会话 |

**OTel GenAI 语义命名锚注记（外向调研条目 2，2026-11-12 append；纯文档、
零依赖零服务零新进程）**：OpenTelemetry GenAI 语义约定属性与仓库既有记录
同构——`gen_ai.evaluation.{name, score.value, score.label}` ↔ bounded
question 的 `{answer, p}` 判断记录（读侧锚：`scripts/monthly_review.py`
reconcile_predictions `:1002-1074`——name≈claim、score.value≈p、
score.label≈answer/带位）；`gen_ai.usage.{input_tokens, output_tokens}` ↔
`src/aionis/extraction/llm_client.py:122-134` 的 prompt_tokens/
completion_tokens 记账。将来**运维面** LLM 记账文件（夜报/月末会话侧）按
`gen_ai.*` 命名即获跨观测工具互认；`llm_client.py` 现有字段名**不动**
（本注记只读引用——研究管线零改动红线，AGENTS.md）。**诚实边界**：GenAI
属性已自 open-telemetry/semantic-conventions 主仓迁独立新仓（registry 页
每条属性均标 "Moved"），新仓名先前经 GitHub API 核实 404 未成功——引用锚
用 opentelemetry.io registry 文档页（CC BY 4.0，
<https://opentelemetry.io/docs/specs/semconv/registry/attributes/gen-ai/>，
2026-11-12 fetch 复核可达）+ semantic-conventions 主仓（Apache-2.0，先前
调研已经 GitHub API 核实）。本注记不装包、不接线、不加进程，仅钉命名锚。

**跨月累积 p 呈现护栏注记（p-trajectory-presentation，2026-11-13 append；纯文档、
零依赖零服务零新进程）**：`reconcile_predictions`（`scripts/monthly_review.py:1017-1091`，
def/return 实测）现仅**单月**呈现——judgments/facts 分账 + p>0.6 高带挂固定呈现标签
「仅自动进入对账候选呈现，无任何自动处置」（`:986-987` 实测原文）；全仓
`prediction_records` 唯一消费点=stats 计数（`monthly_review.py:806`，scripts/src/
tests/dashboard 四域 grep 实测），输出经 `proposal_reconciliation`（:768，只读扫
当月 backlog）进 `--weekly` 面按日落盘——**现无跨月累积 p 呈现面，逐条 p 亦无跨月
聚合持久化**。将来若做跨月累积 p 轨迹呈现，护栏三条钉死：
①**只记录不决策**——呈现层只读历史记录，零阈值/自适应/再打分逻辑；n=1 月度样本
禁统计拟合、禁显著性声称（既有红线，与 backlog 候选⑤诚实边界同向）。
②**peeking 文献锚（2026-11-13 fetch 双双复核可达）**：arXiv:1512.04922
（Johari/Pekelis/Walsh，Always Valid Inference——摘要原句：用户「continuously
monitoring」时常规 p 值/置信区间推断 wholly unreliable，即持续查看抬升假阳率，
「只记录不决策」的动机锚）与 arXiv:2210.01948（Ramdas/Grünwald/Vovk/Shafer，
Game-theoretic statistics and safe anytime-valid inference——e-process/置信
序列于任意停时有效=对照面锚）——两锚仅支撑「为何只记录」，**绝不构成**把
anytime-valid/e-process 引入 eval 层重算的许可（改推断程序=frozen config 语义
变更，config_committed 红线，AGENTS.md）。③**图形态待数据面实证**——plotly
MIT 已在栈（`pyproject.toml:42/:65`，零新依赖），但折线需跨月 p 数据面（逐条 p
无跨月聚合持久化，本注记不虚构其位置）；数据面现成前止步本注记级，届时限
dashboard/ 呈现侧折线、**禁回归/拟合线**；`sklearn CalibrationDisplay` 系
二分类可靠性图（分箱校准语义），与月度 p 轨迹错位，不采用。

### lessons 块格式（月度教训写回契约，gen2 条目 4 钉契）

月度复盘教训经 `--append-lessons-from` append-only 写回 handoff（轮 126-续3）。
2026-11 月底首块写入前，块内契约按 gen2 条目 4 钉死如下（协议借 noahshinn/reflexion
MIT 与 mem0ai/mem0 Apache-2.0，**仅借协议不装包**）：

- **计划形契约**：每条教训必须是可执行动作计划——「下次 X 触发时做 Y」，非事件
  描述（Reflexion 计划形提示词移植）。
- **`event:` 行（四操作裁决，mem0 分类学）**：`ADD`（新教训）/ `UPDATE`
  （`supersedes month=YYYY-MM#条目`）/ `DELETE`（`voids month=…`）/ `NONE`
  （重复已录，不重写）。append-only 语义下 UPDATE/DELETE 均为**引用式标记**，
  不改旧块字节——与 ledger「新行不覆盖」同构。
- **`evidence:` 行**：指向 run.log / 审计报告的**路径引用**（Inline & Spill：附录式
  挂新块，不回填历史块）。
- **片段生命周期双路径（Memp 协议映射+Memory-R1 outcome 门控；iterate 轮 14 框架③）**：
  月末会话抽片段前先裁决路径——**路径 A 新登记**：本月 resolved 对账行支撑的新教训 →
  `event: ADD`，每条带 `hook=<可证伪依据> ref=<YYYY-MM#n>` 信封（质量门①三判据把关）；
  **路径 B 既有片段处置**：新 outcome 证据指向既有片段时 → refinement=`event: UPDATE`
  （`supersedes month=YYYY-MM#条目`，修正形接替、replacement 携教训前行）或
  deprecate=`event: DELETE`（`voids month=YYYY-MM#条目`，废弃退役）；无证据变化 →
  `event: NONE`（重复已录不重写，轮 145 先例）。**片段保留/晋升须引用月度 resolved
  对账 outcome 证据（`ref=`）而非自评**（Memory-R1 outcome 门控协议映射；
  arXiv:2508.19828+yansikuan/memory-r1，Apache-2.0/134★——协议级只读参照，PPO/GRPO
  训练与 LoCoMo/MSC/LongMemEval 评测基建全不采）；UPDATE/DELETE 的 `month#条目` 目标
  必须真实存在（伪 id=quality-miss[bad-ref]，与①第二判据同一 gate、零新增 reason）。
  prose 由会话 LLM 生成，门零 LLM 零嵌入零 I/O。

### lessons 首跑预演注记（monthend-dryrun，2026-11-13；2026-11 月末首块写入前注意事项）

月末首跑就绪证明（三链实弹 + tmp 隔离写回，载体
reports/audits/2026-11-13-iterate-round-6.md）落地后的首跑注意事项四条 +
一条实测格式陷阱：

- **(a) 首次月末对账面为空是预期**：backlog `prediction:` 行现 **0 条**
  （grep 实测）——预测接线 2026-11-12 起、首批 due 月 2026-11 月末才到期，
  reconcile_predictions 首跑零记录=机制就绪、数据面从零起，非缺陷（与 iterate
  轮 5 报告口径一致）。
- **(b) 聚合视图空态是如实输出**：handoff 现无任何 lessons 块
  （`monthly-reflexion-lessons` grep 零命中）→ --lessons §6 Active lessons
  首跑输出 none yet/空态非缺陷。
- **(c) 缺席工作日=整月口径**：--lessons 无 SUMMARY 工作日列表含当天及未来
  日期（2026-11-13 实测列至 2026-11-30；collect_log_days 整月遍历）——月中
  运行看到「未来缺席」非缺陷，月末（11-30 后）运行自然收敛。
- **(d) --weekly 双红为已知**：vintage-probe code-defect + billing
  platform-failure（≥2 workflow fast-red 平台签名合并）均已在册已知项
  （billing playbook 节）——首跑勿当新缺陷处置；判结构健康看 §4 invariants
  OK。
- **格式陷阱（tmp 预演首跑实测触发，非预设）**：`event:` 行必须自身是 bullet
  列表项（`- event: ADD`；EVENT_OP_RE `monthly_review.py:1286` 要求 `[-*]`
  前缀，entry 以 event 行起头、计划文本与 `evidence:` 作附着行
  :1270-1283）——--lessons 渲染的写回契约行未写明 bullet 语法，裸写缩进形
  `  event: ADD` 会被 exit 3 契约门拒。首块组织按 bullet 语法。
- **诚实边界**：本注记与就绪证明背书的是**机制面**（三链可跑通、写回契约门
  三态行为正确、append-only 逐字节成立）；不背书月末会话产出教训的质量，也
  不背书 bounded question 口头 p 的校准度——第三方实证 arXiv:2611.11480
  （Beyond Ranking: Are Decision Models Calibrated Relevance Scorers?，
  cs.IR 2026-11-08，本会话 fox_fetch 一手复核可达；与本轮条目 3① 呼应）实测
  Jev 类决策模型原生概率**过自信**（>0.9 分带仅 66% 相关、需 2 参数校准
  修复）——正因如此 Aionis 运维层 p 仅记录轨迹、禁再校准拟合与显著性声称
  （既有红线），首跑勿因「p 看起来偏高/偏低」临时引入校准。

## GitHub 计费冻结应对（billing lock playbook，2026-11-06 立案）

先例：2026-08-20→09-01 首次冻结（结清后恢复）；2026-11 复发（"billing lock
#2"，commit `18001a804`）。冻结是**账户级**的——连公开仓库的 Actions 也一并
停止，"转 Public 免修账单"不成立（state/current.md §10 结论）；唯一出路是
Settings → Billing 结清/解锁。

**2026-11-11 业主停用令（Actions pause order）**：锁定期间业主指示本项目
**暂不再启用 GitHub Actions，相关任务一并暂停**。已执行（全部可逆）：

- `gh workflow disable` ×6：Tests、Publish site、Staleness check、Vintage
  Drift Probe、E3 Forward、Refresh terminal data（deploy-pages 此前已停；
  Dependabot 与 pages-build-deployment 是 GitHub 服务本体、不占 Actions
  用量，保持原样）。停用走 API 开关，**零文件改动**，hygiene 守卫不受影响。
- 晚间通道 own-commit CI 轮询加停用感知（轮 129）：`_actions_paused()` 探测
  ci.yml+publish-site.yml 双双非 active 时，`verify_own_commit_ci` 直接记
  `paused(actions-disabled)`，不再每夜空烧 6 分钟有界窗口；单边重启用
  （解锁过渡期）保持诚实轮询；探测失败 fail-open 回退旧行为。23:35 夜报班
  提示词同步（CI(own)=paused 不判红；发布链=冻结；出现意外新 run 报"需人审"）。
- staleness-check 的**远端** marker-deadman 随停用暂停；本地层（doctor 第
  7、8 层 + 夜报班）是停用期唯一监测信号，照常运转。

**恢复清单（业主 billing 解锁后，钥匙在业主）**：① `gh workflow enable`
逐条恢复六工作流（Tests→publish-site→staleness→其余）；② 按
reports/audits/2026-11-11-env-testpipeline-round.md 的解锁日首验清单执行
（node24 首跑全绿核对、YAML 卫生守卫 CI/本地同绿、滞留红 rerun 一次再判、
refresh 双缓存 GC、Pages billing usage、freeze 通道 --check-recovery 三态）；
③ ~~publish-site 的 node20 残余钉点须在首推前重钉~~（轮 130 已清偿：:46/:50
重钉至 pnpm v6.1.1 / setup-node v7.1.0 node24 SHA，与 ci.yml/deploy-pages.yml
同款，YAML 卫生守卫 23 用例复跑全绿）；④
本停用段（2026-11-11 起）在月报 Actions 分钟口径中记为零。停用期间**绝不**
自行 enable——夜报班红线已加。

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
  且其余各层全绿** = 典型"本地栈健康、发布被冻结"签名，提醒业主去修
  Billing（2026-11-06 实测即此形态；时点为 7 层期）。
- `--doctor` 第 8 层（marker deadman，2026-11-11 轮 126）：healthchecks.io
  Period+Grace 语义（BSD-3-Clause，仅借协议）——最近 ok_committed 晚间
  marker 过期（Period=1 个工作日晚，Grace=1 个工作日；周末 SKIP:weekend
  不计时，条件性假日跳过由 Grace 吸收）即 FAIL："lane silently dead"。
  这是**结果层**（层 1-7 查部件，层 8 查产出），本地判定不受计费锁影响。
  远端镜像=`staleness-check.yml` 的 `marker-deadman` job（cron 已升为每日
  02:37 UTC，读 main 上最新 `chore(data): evening terminal refresh` 提交日
  应用同一规则；**verification-pending**：billing 解锁后首跑核验，见上
  playbook 顺序；锁定期间 Actions 不运行=无误报，解锁日滞留红按轮 125
  操作顺序重跑一次再判）。
- `--doctor` 第 9 层（env-lock drift，2026-11-13 轮 133）：H6 version-pinned
  守卫——`uv lock --check` 主判（lockfile vs pyproject 脱钩即报错）+ `uv sync
  --all-extras --locked --dry-run` 并行（**--all-extras 必带**：bare
  `--locked --dry-run` 系 base-sync 语义假计划，实测 2026-11-13 会列
  "Would uninstall 101 packages"——extras 包假漂移信号，非 lock 漂移）。
  本地层、读侧探测、零新依赖（uv 为既有项目工具链）。

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
uv run python scripts/ops_local_refresh.py --doctor       # nine-layer preflight
```

`--doctor` (round 109; layer 7 added 2026-11-06, layer 8 marker deadman
added 2026-11-11, layer 9 env-lock drift added 2026-11-13): one read-only
command that
verifies the whole stack — marker/guard sanity, Task Scheduler registration,
SessionStart hook config, git push credential (ls-remote), gh auth, the two
API env keys (names only), site-repo drift (layer 7: the LIVE Pages
snapshot vs the committed one — see the billing-freeze playbook below), and
env-lock drift (layer 9: `uv lock --check` + `uv sync --all-extras --locked
--dry-run` — the H6 version-pinned guard). Run
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

## 渐进自治梯（L0-L3 automation ladder，2026-11-13 入册）

蓝本：`reports/design/2026-11-14-personal-training-method-and-automation-ladder.md` §3（定夺轮定案稿）。入册原则：**先入册后启用**——L2 及以上在晋级门槛满足且业主显式扳键前一律不启用；本节只定形，全节引用既有锚不重复展开。

### 分级表

| 级 | 定义 | 状态 | 判据/互锁 |
|---|---|---|---|
| **L0 呈现** | 确定性信息呈现：夜报包、`--status`、`--doctor`、runbook 注记。零动作 | 在位 | 无（纯只读） |
| **L1 自动候选** | 引擎只建议、人裁决：`--propose` 七卡（`run_propose` `monthly_review.py:1198`、零 LLM 零网络声明 :1679；引擎对 backlog/tasks 只读——节奏表 :230「绝不自动写」）+ `--triage` 三分类分诊（`classify_run_row` `ops_local_refresh.py:558-576` 纯规则，三桶常量 :542-544 = platform-failure / infra-transient / code-defect） | **现状（在位）** | 只读 + 人工采纳门 |
| **L2 校准达标后·可逆运维决策自动执行** | 合格面三件：软败重试升级（`--status` retry_soft 先例）/ 分诊带动作（triage 结论→预设处置映射，处置集封闭枚举）/ propose 自动派发候选（`render_card` `monthly_review.py:990` 的 disposition 行 :997 → `scripts/orchestrate_dispatch.py` 派发路径；仍不写 backlog/tasks 本体） | **未启用（先入册后启用）** | 三互锁（下）+ 量化门槛（下）+ 业主扳键 |
| **L3 业主定义** | 待定义 | 未定义 | 待业主区（`state/current.md`） |

### 永不合格面（无论校准几级达标，永不自动执行）

外部工程佐证：OpenAI Operator System Card（风险×可逆性判据 + 证券买卖 fully restrict）——分级表必须有硬禁区；「运维面低风险」不得滑坡成研究面豁免。

1. **研究管线**（`src/aionis/`、`scripts/phase_*`、dashboard 研究面）；
2. **`runs/ledger.jsonl` 写入与一切 frozen config 变更**（config_committed BEFORE result 红线，AGENTS.md）；
3. **业主钥匙面**（`.env`、billing、推送凭证）；
4. **交易执行/下单**——Aionis 阶梯**永不含**（量化项目特有条款）。

### L2 三互锁（缺一即不许启用）

1. **attempt-cap**：3 次失败锁死等次日或人工（本档 `SKIP:attempt-cap` :89、:646 一带 push 失败锁定 + 交互恢复路径先例）；
2. **审计轨迹**：每次自动执行写 handoff 审计行（触发信号 / 所执行动作 / 回滚点三要素）；
3. **一键回滚**：backup ok + `push_only_recovery`（`--status` 实测字段，2026-11-13 复测在位）；revert 路径随启用入册时写死。

### 晋级门槛（形先入册；L1→L2 需同时满足，数值待基线后业主定标）

X/N/Y/M 数值待首月基线数据后由业主入册——当前 resolved 对账记录 = 0 条（`grep -c "prediction:"` / `grep -c "outcome:" state/backlog.md` 双零，2026-11 = 基线月，设计报告 §4），**不凭空造阈值**（RouteLLM n=1 禁拟合锚，`state/backlog.md:210` 延伸索引⑤）：

- a) 汇总 mean Brier < X，连续 M 个月；
- b) resolved 对账记录累计 n ≥ N；
- c) 各桶 Wilson 95% CI 上界 < Y（样本量足以让 CI 收窄到可用）；
- d) 期间零 insight 违例（无「自动调 p」类指令混入 lessons）；
- e) **业主显式扳键**（待业主区：L2 启用钥匙）。

口径同构锚：arXiv:2610.18614——晋级看「对月末**结局**校准的置信」（Brier 分桶 + 样本量门槛），不看单条建议自评；trust/abstain/handoff 三态 ≈ 自动执行 / 跳过待人工 / 上抛业主（只借评价口径，Aionis 是月度粒度）。工程同构三原则（Anthropic「Building effective agents」2024-12 原文口径）：最简起步、按需增复杂度（L0 起步逐级不跳级）；checkpoint + stopping conditions（attempt-cap + 人工互锁的直接工程先例）；evaluator-optimizer（每步拿环境 ground truth 反馈再迭代——校准飞轮同构）。**边界：不因此引入任何 SDK / MCP / 框架组件**（provider 红线 + 零新依赖）。

### 晋级门槛 gate 数学定义（iterate 轮 11；promotion-gate-function——只算不启用）

可计算函数 `promotion_gate_assessment(records, thresholds)`（`scripts/monthly_review.py:2324`；纯函数零 LLM 零新依赖——statsmodels `proportion_confint` 已 pinned，沿 `calibration_bucket_summary` 先例）：输入 resolved records（`_collect_prediction_records` 四字段形）+ X/N/Y/M 四参数（**数值留待业主定标——函数只收参数、不内嵌魔数；未定标轴→理由行而非布尔**）；输出三态 **met / not-met / not-enough-data** + 逐项理由行。**只算不启用，钥匙在业主（上表 e 项语义不变）；与 OOS 判定零关系——gate 数学仅运维面晋级自检，不触碰任何研究面判定**（常量 `GATE_SCOPE_NOTE` :2048）。

- **X 轴（技能分）**：BSS = 1 − BS/BS_base，其中 BS = mean((p−y)²)、**base = 无条件 base-rate（climatology）预测器「永远输出 p̄」**（p̄=历史命中率；BS_base = mean((p̄−y)²) = p̄(1−p̄)）——X 判据由「汇总 mean Brier < X」数学化为「**BSS > X_min**」（优于 base-rate 基线），非裸 Brier。数学正身：arXiv:2611.14465（BSS 权重语义=比 base rate 有信息量/better-than-chance）。背景锚：arXiv:2610.38211 RainCheck（BSS 相对 climatology 带 95% CI 的报告口径；其 temporal 跌破 climatology=反泄漏立场第三方同构实证）。**边界**：BS_base=0（p̄ 退化为 0 或 1——全部 y 同值或单行）→ BSS 无定义 → 诚实理由行，不造假分。
- **N 轴（学够了没有）**：累计 resolved 行数 n ≥ N_min；不足 → not-enough-data 理由行（同构『学够了没有』）。
- **Y 轴（CI 收窄）**：各已入桶（p≥0.5 固定五桶、n≥1，**空桶不判**）Wilson 95% CI **上界** < Y_max（wilson 法保守侧；全命中桶上界恒为 1.0——「CI 收窄到可用」的设计本意）。**anytime 注记行**：月度连续重复查询需 anytime 校正（arXiv:2610.28979 只借原则）；当前每月 1 点，AsympCS 类渐近校正不成立——局限如实注记，不照搬渐近实现（常量 `ANYTIME_MONITORING_NOTE` :2045）。
- **M 轴（连够了没有）**：按 due 月分组、月度 BSS > X_min 的**连续月数** streak ≥ M_min；月度基线退化月（月内 p̄∈{0,1}→月度 BSS 无定义）不计入 streak。
- 三态判定序：任一轴 undetermined（未定标或数学不可判）或 not-enough-data（N/M 不足）→ **not-enough-data**；四轴全定标且数据充分、任一可算轴客观失败 → **not-met**；全过 → **met**。当前真实态（2026-11 基线月、resolved=0）= **not-enough-data**——首月唯一真实可达分支。
- tests 六钉 `tests/test_monthly_review.py:972-1068`：met 全过 / not-met（Wilson 上界失败）/ N、M 不足 / 退化基线 BSS 无定义 / 未定标理由行+无桶可判 / 真实账本当前态断言；synthetic 夹具经真函数实测锁定（BSS=0.119、最宽 Wilson 上界 0.9433）。

## 首月执行剧本（2026-11-30 月末全链操作手册，2026-11-13 入册）

审计主题②落地：2026-11 是首个带 prediction/outcome 接线的完整月（基线月——本节
入册当日 `grep -c "prediction:" state/backlog.md` 与 `grep -c "outcome:"` 实测
**0/0** 双零起跑）。本节把月末全链钉成六步操作手册：每步命令/预期输出/检查点/
失败处置，吸收调研四检查点（落点汇总见本节末表）。**本节纯 docs：零代码、零新
旗标、零新班次**——所有命令均为既有 CLI 面（`scripts/monthly_review.py`），证据
链主载体=强制 `--out` 落盘（见「GBK 坑处置」节）。

### 总览（六步 × 运行日 × LLM 面）

| 步 | 动作 | 运行日 | LLM 面 | 证据载体 |
|---|---|---|---|---|
| 1 | `--propose` 打卡（月末前置确定性步） | 11-30 会话前 | 零 | `reports/monthend/2026-11/01-propose-cards.md` |
| 2 | 月末会话：粘贴卡+填 p+bounded answer+lessons 草稿 | 11-30 | **是（月内唯一）** | backlog 候选区粘贴 + `03-lessons-draft.md` |
| 3 | `--verify-bounded` 校验（answer 行纯校验） | 11-30 会话尾 | 零 | `04-verify-bounded.md` |
| 4 | outcome 记录（due 月到点逐条追加） | 12 月末（首轮） | 会话内人裁 | backlog 同条目 `outcome:` 行 |
| 5 | reconciliation（--weekly 面）+ calibration_summary（--lessons 面） | 每周五/月末 | 零 | `05-weekly-reconcile.md` + `06-monthly-report.md` |
| 6 | `--append-lessons-from` 写回（insight 沉淀 rides 此通道） | 每月末 | 会话内（草稿撰写） | handoff lessons 块（append-only） |

**--month 语义坑（default_month=上月，`monthly_review.py:81-88`）**：复盘 /
--lessons / --append-lessons-from 的缺省月=**上一个月**（原设计「新每月 6 日回望
上月」）；而 `--propose` 缺省=**当前月**（月末载体语义，`monthly_review.py:1800-1802`
注释钉死）。故 11-30 当天跑步 2 取月报与步 6 写回**必须显式 `--month 2026-11`**
（缺省会拿到 2026-10、写错月份块）；步 1 propose 无需 --month。

### 步 1 —— `--propose` 打卡（零 LLM，引擎只读）

```bash
uv run python scripts/monthly_review.py --propose \
  --out reports/monthend/2026-11/01-propose-cards.md
```

- **命令语义**：确定性信号×规则表→提案卡（`run_propose` `monthly_review.py:1198`；
  头部「零 LLM、零网络」声明 :1223；引擎对 backlog/tasks **只读**）。
- **预期输出**：提案卡 N 张（2026-11-13 基线七卡）+ 刷新指令 0..n 条；每张含
  `prediction:` 行（p=「待月末会话填写 0..1」——引擎绝不代填，`render_card`
  :975/:1208）与 `disposition:` 三去向行（:997：accept→tasks/active/ · defer 留
  候选区 · reject→tasks/rejected/）。exit 恒 0。
- **检查点**：零提案=合法态非失败（无信号或全在册）；去重刷新指令仅人工执行；
  **不自动写任何文件**（节奏表 :230「绝不自动写」）。
- **失败处置**：git pickaxe 不可用→老化信号「不可用=不猜」如实降级；--out 笔误
  未落盘→stdout 仍可读但证据链缺主载体，补 --out 重跑（确定性幂等，零成本）。

### 步 2 —— 月末会话：填 p + bounded answer（11-30，月内唯一 LLM 面）

先取月报+种子（确定性输入，零 LLM）：

```bash
uv run python scripts/monthly_review.py --month 2026-11 --lessons \
  --out reports/monthend/2026-11/02-monthly-report.md
```

- **命令语义**：月报 + §5 Reflexion seeds（`lesson_seeds` :1448：缺席晚/
  persistent/spin + watchdog bounded question :1413 + 校准事实[环1a 注入] +
  insight 钩子）+ §6 Active lessons 聚合（`render_reflexion_section` :1521）。
  正常 exit 0（有 SUMMARY 晚且零采集异常；异常 exit 1 如实，不当缺陷掩埋）。
- **会话动作三件**（全部在**单场**月末会话内——23:35 班次承载，零新增会话）：
  1. **粘贴**：步 1 新卡人工粘贴 `state/backlog.md` 候选区（刷新指令按提示人工
     更新时间戳），并**逐卡填 p**（0..1 口头置信度——judgments 面，引擎永不
     代填；p>0.6 高带=仅自动进入对账候选呈现，无任何自动处置，:1029）。
     **对账行形（解析契约）**：入册的 prediction 行须用紧凑契约形
     `- 甲（prediction: 断言（p=0.8）due=2026-11）`——解析器
     `_collect_prediction_records` :1061-1067 要求行内**连串 `（p=` 子串**，
     卡面展示形 `（judgments: p=…` 不含该子串（flywheel-rehearsal 演练实测
     发现，2026-11-13 勘正），粘贴时须落契约形；outcome 行随后
     `  - outcome: y=0|1 (YYYY-MM-DD)`。
  2. **bounded answer**：对 WATCHDOG_BOUNDED_QUESTION（:1413 固定选项 A=原地
     打转 / B=偏离值班目标 / C=正常）**只回单行 JSON**
     `{"answer": "A"|"B"|"C", "p": 0到1}`（约十 token 量级；answer 只回选项
     标签，不得自由文本）。
  3. **lessons 草稿**：写 `reports/monthend/2026-11/03-lessons-draft.md`——
     计划形「下次 X 触发时做 Y」+ `- event: ADD|UPDATE|DELETE|NONE`（**必须
     bullet 语法**：EVENT_OP_RE :1269 要求 `[-*]` 前缀——tmp 预演首跑实测陷阱，
     见本文件 :421 注记）+ `evidence:` 路径引用；bounded answer 行写进草稿
     （=步 3 的校验对象）。
- **检查点**：p 仅记录轨迹，禁再校准拟合/禁显著性声称（红线）；首月如实面——
  校准事实=`none yet (baseline collection month)`、insight 钩子=「本月无
  resolved 对账行，insight 步跳过」（零 resolved 降级行）——**两处空态均如实
  输出，首跑勿当缺陷、勿造数据**（:401 预演注记 (a)/(b) 同口径）。
- **失败处置**：answer 写偏（自由文本/p 越界）→步 3 逐行抓住（exit 1），改草稿
  重校验（有界单次重试）；草稿缺 event: 行→步 6 exit 3 契约门拒（回改草稿，
  绝不回改 handoff）。

### 步 3 —— `--verify-bounded` 校验（零 LLM 零网络，纯校验）

```bash
uv run python scripts/monthly_review.py \
  --verify-bounded reports/monthend/2026-11/03-lessons-draft.md \
  --out reports/monthend/2026-11/04-verify-bounded.md
```

- **命令语义**：`run_verify_bounded` :1615——逐行扫含 `{"answer","p"}` 双键
  字面的行（与 WATCHDOG 契约同形），经 `parse_bounded_answer` :1422 判四态：
  ok / format-miss（raw 原文留档，未虚构）/ p-not-numeric / p-out-of-range。
- **预期输出**：本月草稿 1 行 answer→`L{n}: **ok** —— answer=… p=…（口头
  置信度，仅记录轨迹）`，exit 0。**首月预检变体**（对「上月块摘录」跑，
  :1699-1700 帮助文本示例）：11-30 无上月块→零候选行→`none yet` + exit 0
  不误报（:1621-1622 设计语义）。
- **检查点**：任一失败行=exit 1；有界重试一次，仍红→按 AGENTS.md 升级
  （2 轮失败封顶，不无限迭代）。
- **失败处置**：format-miss→按单行 JSON 契约改写该行重跑；p 越界→改 p∈[0,1]。
  **禁改 parse_bounded_answer 语义来「让校验通过」**（宽松化=契约腐蚀）。

### 步 4 —— 下月 outcome 记录（gate 时间纪律）

- **动作**（2026-12 月末会话内，人工裁决）：对 backlog 中 due=2026-11 的
  `prediction:` 条目，在同一条目追加一行 `→ outcome: y=0|1 (YYYY-MM-DD)`——
  解析契约 `outcome:\s*y=([01])\s*\((\d{4}-\d{2}-\d{2})\)`
  （`_collect_prediction_records` :1071）；记法在提案卡面即印（`render_card`
  :965「对账记法=该条目追加 → outcome: y=0|1 (YYYY-MM-DD)」）。
- **gate 时间纪律**（四检查点①，FinBench arXiv:2607.16229 同构——报告口径
  明示 gate 时间，time-gated 评测与月末 outcome 对账同构）：y 按**due 月月末
  可得事实**裁定，outcome 行必须带**实际记录日期**——hindsight 不入 y（不用
  事后知识回改早月判断）；due 已过未记=pending 如实分列（对账呈现「due 已过」
  标记，:1012 一带），不虚构 y。
- **检查点**：改前后 `grep -c "prediction:" state/backlog.md` /
  `grep -c "outcome:"` 计数对账（本节入册日基线 0/0）。
- **失败处置**：outcome 行不进解析（缺日期/缺 `y=` 前缀/写错条目层级→该条
  停留 pending）→对照 :1071 契约修正格式即可，零工具介入。

### 步 5 —— reconciliation + calibration_summary（两个既有呈现面）

```bash
# 面一：逐条对账（rides --weekly，每周五已在跑；月末显式重跑留档）
uv run python scripts/monthly_review.py --weekly \
  --out reports/monthend/2026-12/05-weekly-reconcile.md
# 面二：校准聚合（rides --lessons 月报 §5「校准事实」）
uv run python scripts/monthly_review.py --month 2026-12 --lessons \
  --out reports/monthend/2026-12/06-monthly-report.md
```

- **命令语义**：面一 `proposal_reconciliation` :768（run_weekly 内调 :637）内调
  `reconcile_predictions` :1002/:791——逐条 resolved（(p−y)²+方向命中）/
  pending（due 已过如实标记）/未填 p 分列，judgments/facts 分账；面二
  `calibration_bucket_summary` :1118——五桶 [0.5,0.6)/…/[0.9,1.0] n/命中/
  命中率 + Wilson 95% CI + **每桶 p 原值计数**（反聚集）+ 汇总 mean Brier
  （与逐条 (p−y)² 同口径）；p<0.5/p 未填/pending/越界分列不计桶。
- **逾期 outcome 独立统计区（iterate 轮 12 `overdue-outcome-watch`；
  `overdue_outcome_records` `monthly_review.py:1094`）**：面一 §4 findings
  尾部新增**独立统计块**——汇总行「N 张预测卡 due 已过仍未记 outcome」+
  逐卡清单行（claim+due+p），逾期卡不再淹在逐行 findings 流里。语义：
  todo_or_die（backlog 延伸索引㉘）=到期显式爆发**呈报不阻断**+严格时间门
  （`due<当前月`，在期卡零噪音）；2611.03928（延伸索引㉚）=零主动查询预算
  纯呈报审计——outcome 只随月末真实数据到，**绝不提前补查**；逾期即提示
  **人记** outcome，引擎只读不代记（红线）。零逾期=整块不渲染（诚实缺省）。
  月报面同步：§5 Reflexion seeds 有一行 facts-only「本月有 N 张预测卡逾期
  未记 outcome」（零逾期不渲染，沿环 2 降级先例）。
- **预期输出（首轮 12 月末）**：面一=11 月卡逐条 resolved/pending 行；面二=
  首个非空桶表（若仍零 resolved=基线延续，如实）。
- **检查点（四检查点②，p 聚集警讯）**：若 [0.8,0.9)/[0.9,1.0] 桶 p 原值计数
  呈单值堆积（如 `0.9×N`），系 small-llm-calibration（GitHub license=MIT
  已核）实证的 verbalized p 聚集 85-95% 高带=崩塌警讯——**记录进 lessons
  （事实呈现），禁据此调 p 或定阈值**（`CALIBRATION_FEEDBACK_NOTE` :1503
  固定禁令字面：阈值与处置语义只在代码侧规则门，NEVER in any LLM prompt）。
- **失败处置**：--weekly exit 1 含对账发现行（pending due 已过=设计内的人工
  理由项，非通道失败）——逐条给人裁决；桶表空=零 resolved 如实，非缺陷。

### 步 6 —— `--append-lessons-from` 写回 + insight 沉淀

```bash
uv run python scripts/monthly_review.py \
  --append-lessons-from reports/monthend/2026-11/03-lessons-draft.md \
  --month 2026-11
```

- **命令语义**：`append_lessons` :1348——append-only 写入 `state/handoff.md`
  本月 `monthly-reflexion-lessons` 块（一簿一月；旧块字节永不回改，
  UPDATE/DELETE 为 supersedes/voids 引用式标记——与 ledger 新行不覆盖同构）。
- **insight 沉淀（环2，rides 此通道）**：有 resolved 对账行的月末，会话按
  `INSIGHT_HINT` :1515 从 resolved 行 + active lessons 蒸馏 **0-2 条** IF-THEN
  policy 片段写入草稿（片段禁含「自动调 p」指令）。**0-2 条上限的第三方依据**
  =ERL arXiv:2603.24639（LEARN 每次只抽**少量精炼规则**入 prompt——少而精，
  非全量倾倒）。11-30 首跑零 resolved→降级行如实（insight 步跳过），**首次
  insight 生效=12 月末**。
- **lessons 注入预算口径（LIMBO arXiv:2609.14138 锚，2026-11-14 append，
  frontier-citation-anchors ⑳）**：回放非免费——反哺行（校准事实入 lessons，
  步 5 检查点②）占上一 bullet 的 0-2 条额度中 1 条，注入须显式预算、不超限倾倒。
- **重点反哺行同桶去重契约（iterate 轮 12 `feedback-dedup-contract`，
  `feedback_dedup_verdict` `monthly_review.py:1927`；零 LLM 零嵌入确定性实现）**
  ——月报 §5 重点反哺行渲染前，对 §6 active_lessons 各条做**同桶区间 key
  预检**，规则表：

  | 判重输入 | 规则 | 结果 |
  |---|---|---|
  | 反哺行桶区间字面（如 `p∈[0.9,1.0]`）vs 各 active 条文本 | **同桶字面子串命中** | 无条件降级为「**刷新提示**」+附已有教训 `[month#idx]` 引用；本月事实行仍呈现（写回按 event: NONE[重复已录]/UPDATE 定档——写入方裁决）；**不附**反哺预算注记（刷新提示不占新 insight 额度） |
  | 异桶（`p∈[0.6,0.7)` 等）或无桶字面的别类教训 | 不同月/不同类**永不判重** | 保留新条原渲染+预算注记照附 |
  | 基线月（反哺行无桶字面）或 active 为空/无 lessons 块 | 无 key 可比 | 不降级（诚实缺省 none yet 同款） |

  语义三源合一：**Hindsight**（arXiv:2512.12818+vectorize-io/hindsight，backlog
  延伸索引㉕）=写前过滤前置、同桶 key 才比对——保护跨月时间维度记录不互删、
  no-change→no-op 省预算；**mem0**（arXiv:2504.19413，延伸索引㉛）=Algorithm 1
  「无语义等价才 ADD」的**确定性半边**（信息量升格门 InformationContent 比较
  **不实现**——仅引用锚，启用须业主点名，LatentGym A/B 同款边界）；**A-MEM**
  （arXiv:2502.12110，延伸索引㉗）=更新优于追加——降级刷新提示即「引用式
  接替」的呈现半边。**红线**：判重零 LLM 零嵌入（纯字面子串）；既有教训
  append-only 不删不改（引用式，与 ledger 新行不覆盖同构）。
- **预期输出**：exit 0、stderr 无 refuse；handoff 尾部新增块（header 含
  `month=2026-11` 与契约字面）。
- **检查点**：块内 ≥1 条 `- event:` 行（bullet 语法）；`evidence:` 指向
  `reports/monthend/2026-11/` 各步落盘文件（证据链闭环）。
- **失败处置**：exit 2=同月块已存在（下月修或人工补——**绝不回改旧块**）；
  exit 3=零 event: 行（回改草稿重跑，不绕契约门）。

### 演进视图口径（跨月校准演进，iterate 轮 12 `cross-month-evolution`）

- **属月判据=对账月**（outcome 到达月），与对账时点纪律同族——不按 prediction
  卡开立月归属（`_collect_prediction_records` 记录 claim/p/due/y 无属月戳=设计
  决策点，本口径不补戳、不挖史）。
- **选型否决理由（决策员拍板）**：否决「backlog git 史重算」路径——本仓
  `prediction:`/`outcome:` 双零 0/0（2026-11-14 复算）无史可挖，且对 append-only
  长文本挖史脆；**不改 prediction 卡格式**（ZCode 月末提示词模板 {answer,p} 在
  业主待办区，不耦合）。采「逐月对账行存档」：新 durable 载体
  `state/calibration-months.md`（append-only tracked registry，ADR-006 合规；
  2026-11-14 新建，state/ 原仅 backlog/blockers/current/handoff 四文件无既有
  可复用存档——实测核实）。
- **快照行入册步（月末会话，人工 append）**：`--lessons` 月报 §5「跨月校准
  演进」节末渲染「本月快照行」（facts-only 截面：各桶 n/命中率+Brier+BSS 分量
  ——BSS 与 promotion gate X 轴**同一实现** `_bss_components`，月度切片）。
  月末会话将该行 **人工 append** 入 `state/calibration-months.md`（呈报-入册
  分离：引擎只渲染、绝不写 state/ 档案——与 backlog 卡区人工维护同模式）。
  **零 resolved 月不存档**（基线月无截面可记）。
- **演进呈现三态**（`calibration_evolution_lines`，入 lesson_seeds §5）：有两月
  →「上月→本月」两窗口变化行（各桶 `命中率 0.500→0.000（n 2→1）` 方向与幅度、
  BSS 同款；单侧桶如实命名新入/本月空，不外推）——Evidently（backlog 延伸索引
  ㉙）reference-vs-current 两窗口范式锚；仅本月 →「first month, no prior」诚实
  首月；零 resolved →「none yet」。facts/beliefs 分离口径引 Hindsight（延伸索引
  ㉕）锚：p=演化中信念轨迹、outcome=事实。
- **呈现边界（红线，`EVOLUTION_SCOPE_NOTE` 固定字面随节渲染）**：仅两窗口变化
  呈现——**禁趋势拟合/斜率宣称/显著性**；**不设自动判优/劣门**（Evidently
  auto-Tests 自动派生阈值明确不采；判定门唯一=promotion gate 且只算不启用、
  钥匙在业主）。

### GBK 坑处置与证据链载体（--out 强制落盘）

- **前科**：2026-09-10/11 GBK 控制台乱码致当晚通道事故（`reports/audits/
  2026-09-28-interim-coverage-ledger.md:15-16` 在册「GBK era / UTF-8 patch
  fixed mid-evening」）；`monthly_review.py:1772-1775` 已修 stdout
  （`sys.stdout.reconfigure(encoding="utf-8", errors="replace")`——legacy
  GBK 控制台下保 CJK 完整）。
- **剧本规矩**：即便 stdout 已修，终端显示仍随 codepage 漂——**全链六步一律带
  `--out` 落盘**：四个 --out 分支均 `write_text(encoding="utf-8")` 且自动建
  父目录（:1612/:1637/:1657/:1677）。落盘文件=证据链**主载体**，stdout 仅
  人读辅助。
- **目录选型**：`--weekly` 默认锚点 `runs/ops_local_refresh/<date>/` 系
  **gitignored**（`.gitignore:41`，check-ignore 实测）→ 本链证据统一落
  `reports/monthend/<YYYY-MM>/`（tracked、随提交进版本库；文件名 01-06 编号
  即步序）。

### 审计轨迹位置一览

| 载体 | 内容 | 写者 |
|---|---|---|
| `reports/monthend/<月>/` | 六步 --out 落盘（本剧本强制主载体） | 各步命令 |
| `state/backlog.md` 候选区 | 提案卡粘贴 + `prediction:` p + `outcome:` 行 | 人工/月末会话 |
| `state/handoff.md` | `monthly-reflexion-lessons` 块（append-only） | 步 6 |
| `runs/ops_local_refresh/<date>/weekly_watchdog.md` | --weekly 默认锚（本地、gitignored） | 周五班 |
| `runs/ledger.jsonl` | **零触碰**（本链运维面，0 ledger——研究面红线不受染） | — |

### oversight 层边界与三互锁自查表（四检查点④：arXiv:2604.23049 HITL 解耦）

**边界**：判别层=`monthly_review.py` 运维面（确定性、零 LLM、对 backlog/tasks
只读）；生成层=月末 HITL 会话（月内唯一 LLM 面：填 p / 答 bounded question /
撰 lessons）。HITL 解耦锚（2604.23049）明示 oversight 层与执行层分离——月末链
中 oversight=月末会话+业主（p 填写、outcome 裁定 y、lessons 定稿、disposition
三去向均**人裁**），引擎只呈报不代决——与 :697 自治梯 L1「现状」严格一致：
**本剧本不改任何级的启用状态**（L2 仍先入册后启用）。

**三互锁自查表**（沿 :719-723 L2 三互锁形态；此处为月末链**人工自查**、非 L2
启用判据）：

| 互锁 | 月末链对应物 | 自查问句 |
|---|---|---|
| attempt-cap | 会话失败有界重试（复活链三次 Model creation failed 教训，handoff 轮 131 在册）；步 3 exit 1 有界单次重跑；步 6 exit 2/3 改草稿不硬塞 | 「同一失败是否已重试 ≥2 轮？」→是则升级，不无限迭代 |
| 审计轨迹三要素 | 触发信号（--propose 卡/weekly findings）/ 所执行动作（粘贴/append/落盘）/ 回滚点（提交前 diff 审阅 + append-only 旧块不动） | 「本步触发-动作-回滚点三件是否都在 reports/monthend/ 与 git diff 里可指认？」 |
| 一键回滚 | 提交原子性（Conventional Commits 单批）；backlog 粘贴在 commit 前 `git checkout --` 可弃；lessons 块不可回改但可 voids 引用式标记；backup ok + push_only_recovery（--status 实测字段） | 「若本步全错，恢复路径是否一步可达？」 |

### 四检查点落点汇总（调研一手核实；本节为唯一落点表）

| # | 锚 | 一手核实要点 | 落点 |
|---|---|---|---|
| ① | FinBench arXiv:2607.16229 | confidence-competence gap 列**头号盯防失败模式**；报告口径明示 gate 时间——time-gated 与月末 outcome 对账同构 | 步 4 gate 时间纪律（y 按 due 月月末事实裁定 + 记录日期显式 + hindsight 不入 y）；盯防面：p 高带而连续未命中=confidence-competence gap 警讯→只记录进 lessons |
| ② | small-llm-calibration（GitHub license=**MIT** 已核） | verbalized p 聚集于 85-95% 高带=崩塌警讯 | 环1a 每桶 p 原值计数反聚集（:1118 一带）的第三方实证；步 5 检查点（单值堆积→记录、不调 p） |
| ③ | arXiv:2610.25846 预注册审计 | verbalized **单通道**效度局限 | 只引注作诚实边界：bounded p 系口头置信度仅记录轨迹（:1364 口径）——**不增设第二通道**（不引入 logprobs/二次问答） |
| ④ | arXiv:2604.23049 HITL 解耦 | oversight 层边界明示 + 三互锁对照 | 上节边界段 + 三互锁自查表 |

次级锚：**ERL arXiv:2603.24639**（LEARN 每次抽少量精炼规则）→ 步 6
INSIGHT_HINT 0-2 条上限的第三方依据。**CAGE-1 arXiv:2607.03510 本剧本不落**——
主用途=L2 晋级自检清单，留待晋级轮（:697 自治梯节启用时入册）。

**边界重申**：本节零代码/零依赖/零新班次；六步全在既有 CLI 面与既有会话预算内
（月末单场 LLM 会话承载步 2/6 的生成面，其余全零 LLM）；研究面 / runs/ledger /
frozen config 零触碰；待业主区不受本节影响（billing 解锁 / L2 钥匙与定标 /
ZCode 月末提示词模板 {answer,p} 同步确认等，见 `state/current.md`）。产物提交按
Conventional Commits 原子批（运维面 lane）。
