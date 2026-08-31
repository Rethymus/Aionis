# Post-parity roadmap — the final form after the reference retired itself

Owner directive (2026-08-25): iterate visually until fully aligned with the
reference terminal, adapt ALL of its content (not surface data), then deeply
plan the project's future direction — the reference (参照站) was
declared the terminal form Aionis has been pursuing.

## 0. Where this round landed (Tier-7 evidence)

Reference-status fact (re-verified 2026-08-25 via 1.1.1.1/DoH): **the
reference is still gone** — `参照站` and `参照站` are
NXDOMAIN (operator-deleted 2026-08-24 mid-session); root `参照站`
resolves but hosts no data terminal; Wayback has zero snapshots. The frozen
reference set (`runs/ui-iter/`: 12 of their PNGs, 10 HTML pages, their
compiled CSS) is the only legal baseline, and every one of their 19 routes
has a live counterpart built to the converged design system (tiers 1–6, all
committed through `692674b`).

Tier-7 (this round) closes the last visible gap — **home module parity**:

- Reference home = 15 sections; ours had 6 of them. Added: 最新举牌 /
  近期 IPO / 机构最新申报 (FilingStrip upgrade) / 明星投资人 / ARK 基金仓位异动 /
  重大事件 / 高管人物变动 / 探索全部数据模块 footer grid + 散户情绪榜 &
  政客交易 upgraded to their full row anatomy + StatBand switched to
  directory-scale counts (their home flexes scale; ours now flexes real
  scale). All client-side from existing panels — zero new fetch paths.
- 8 pages that never had a direct baseline (taco / stakes / market / annual /
  executives / manager / api-docs / filers) were visually audited this round
  against the family anatomy — all PASS (one vision-model "legend overlap"
  report on /market was DOM-refuted: no Legend element exists; treated as
  hallucination per the documented cross-check rule).

## 1. Content-depth ledger (ours vs their declared KPIs) — the "not surface
data" audit

Their home stat band declares scale; our panels beat or honestly disclose:

| dimension | their declared | ours (committed panels) | verdict |
|---|---|---|---|
| 上市公司 | 6,517 | **10,387** (companies_dir, SEC snapshot) | deeper |
| 机构 | 8,741 | **9,385 filers / 37,348 filings** (filers13f) | deeper |
| 明星投资人 | 43 | 40 (5 stopped-filing entities honestly excluded) | honest −3 |
| 政客交易 | 2,778 (filing-level) | **2,812 transaction-level** (PTR PDF parsed, party join, late-filing clock) | deeper + finer grain |
| Reddit 标的 | 681 | 290 declared / 100 visible (ApeWisdom free-tier pagination dead — disclosed) | source-limited |
| 新闻 | 7×24 中文快讯 | GDELT 200/2d English (+zho probe this round) | T7B lane |
| 举牌 | 13D/A stream | 15,982 SC 13G rows + pct parsed top-150 + 13D lane | comparable+ |
| IPO | priced w/ $ | 1,046 filings / 484 issuers, **price not parsed (v1 boundary)** | residual |
| 高管人物 | person-level (离任/上任) | filing-stream level (person parse = documented red line; 660 DEF14A persons graded) | partial by design |
| ARK 异动 | ±pp 30d | today-snapshot only (ARK publishes no history; our dated local snapshots accumulate into one) | time will close it |
| 势力阵营 | "即将上线" (their TODO) | not built (reserved as Aionis lineage graph) | neither has it |

Residual-depth backlog (honest, each an S/M display-lane or bounded-parse
task): IPO offer-price parse from 424B4 (M, bounded-parse lane like
stakes_pct); ARK ±pp becomes computable after ~30 daily snapshots accumulate
(then home module upgrades from fund-count to real pp deltas); 明星投资人
+3 only if three active filers pass the honest-curation bar (never pad to
match a number); Reddit needs a second source or ApeWisdom pagination
revival (blocked, disclosed).

## 2. The strategic fact: Aionis is now the surviving instance of the final
form

The audit of 2026-08-24 (bb) established the reference ran OUR data under a
different skin (its /institutions carried this repo's 40-star curation, zh
aliases, 7-category buttons verbatim). The operator then deleted the
subdomain mid-alignment-round. Whatever the operator's reason, the
consequence is structural: **the "final target form" no longer exists as an
external site — it exists as this repo's web terminal**, which now carries
both skins' union (their presentation anatomy + Aionis's provenance, honest
counting, bilingual UI, research-validity layer). Parity is no longer the
frontier. The frontier is what the reference never had:

1. **Provenance-first data terminal** — every panel carries source, license,
   as-of, and parse-honesty metadata (their footer said "第三方非公开数据库";
   ours is 7-gate public first-party sources).
2. **A falsifiable research layer coexisting with live panels** — the frozen
   verdict chain (VerdictAnchor → GuardBand) beneath the cockpit is
   something no data terminal does; it is Aionis's identity, preserved
   deliberately below the fold.
3. **Bilingual + color-convention awareness** (zh/en, red-up/green-up toggle).

## 3. Priority horizons (what "future direction" concretely means next)

### H1 — Bring the terminal back online (owner-paused; the highest-leverage
next move)
GitHub Actions billing froze deploy + daily refresh on 08-20. The terminal's
data is only as alive as its refresh lane. The full engineering decision
document is `2026-08-22-realtime-deployment-architecture.md` (recommendation
B: CF Pages shell + data-gateway Worker/R2/Cron, $0 tier; ladder 1 = local
scheduled task + gh-pages direct push, half a day, zero new accounts).
Owner gates: D0 (fix billing) or ladder-1 bypass; D2 host choice; D7 runner
choice. Nothing in H1 touches ledger/frozen/OOS — it is pure display-lane
rehosting.

### H2 — Real-time price surface (display-only)
The one visual module the reference had that we deliberately lack: a live
price chart on /stock (ours charts score history; live prices tick in the
header pill). The display-only Cloudflare Worker (`workers/prices/`) already
serves prices. Next: an intraday sparkline/area on /stock fed by the same
Worker, clearly labeled display-only. S task, zero research-surface contact
(the anti-leakage boundary is documented and binding).

### H3 — Depth residuals (§1 backlog)
IPO price parse; ARK history accumulation (automatic with daily refresh);
news bilingual stream (T7B probe); 明星投资人 honest +3. Each is bounded,
disclosed, display-lane.

### H4 — Research line convergence (the Aionis differentiator)
The terminal currently shows FROZEN research results (ledger #49 chain). The
only legal way those numbers move is E3 forward-live (commit-then-reveal,
PIT-safe sources already flowing through this terminal's own panels: 13D,
Form 4, macro) and Track A factor generation. When E3 ignites, the cockpit
gains a "forward ledger" module — the terminal becomes the E3 observatory.
Gates: AUD-06 + owner GO (unchanged).

### H5 — 势力阵营 (the graph panel neither site has)
Their nav promised it ("即将上线"), we reserved it (lineage graph from 13D
coalitions / 13F co-holding / DEF14A boards). Data partially exists
(form13f, def14a_persons, stakes). M/L task when the owner wants it; it is
the first module with NO reference to align against — pure Aionis original.

### H6 — Terminal API (already shipped, extend)
/api-docs + public/api/v1 (OpenAPI 3.1) exist. As panels deepen, keep
catalog/health in lockstep (the contract gate enforces shape; rows counts
added this round give the catalog real scale numbers).

## 4. Anti-goals (recorded so they don't drift back)
- No fabrication to match a number (43 stars, 681 tickers, $ prices we
  haven't parsed, pp deltas we have no history for).
- No research-surface contact for display work (prices display-only; panels
  never feed features/eval/ingest research paths).
- No resurrecting external scrapes of the retired reference (frozen
  baselines only; the license was never clear and the site is gone).

## 5. Owner decision list (unchanged gates, restated)
D0 billing / D2 host / D7 runner (H1); KRX key or accept C proxy (Korea
lane, closed at proxy); E3 GO + AUD-06 (H4); 势力阵营 GO (H5).
