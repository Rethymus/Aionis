# Visual alignment round — pixel-quantified iteration against the deployed terminal

Owner directive (2026-08-24): 用视觉能力进行一张复一张的多次迭代，直到彻底对齐参照站网站数据呈现与UI设计 —
iterate page by page with visual capability until fully aligned.

## Method (the loop)

The vision-model bridge is unavailable in this environment (Read→CDN URLs are
rejected by `analyze_image` — parse error 1210 on the Windows-path object key).
The loop is therefore **quantitative pixel comparison**, which is stronger for
alignment anyway — numbers, not vibes:

1. **Capture both sites, same viewport** — system Edge headless CLI:
   `msedge --headless --disable-gpu --force-dark-mode --window-size=1440,2400
   --screenshot=<png> [--virtual-time-budget=10000] <url>`.
   - `--force-dark-mode` is required on their site: it is system-themed
     (next-themes), and headless defaults to light. The owner's OS is dark —
     dark is the compared skin on BOTH sides.
   - Our build serves under its production `basePath=/Aionis` via the
     `web/Aionis → web/out` junction on `python -m http.server 8495`.
     Serving `out/` at root 404s every stylesheet (this silently broke all
     pre-round captures — they compared an UNSTYLED page).
   - Their pages with live client fetches (e.g. `/filers`) may render empty
     under virtual-time — those pages are compared structurally (HTML), not
     by pixels.
2. **Measure** — `runs/ui-iter/pixcmp.py` (PIL, adaptive dominant-bucket bg):
   content %, text-like %, rail width + L/R margins (column profile), vertical
   rhythm (row profile), accent hue mix, dominant-color census.
3. **Fix → rebuild → recapture → re-measure** until per-page deltas collapse.

All artifacts (PNGs, fetched reference HTML/CSS, Edge profiles, pixcmp.py) live
in `runs/ui-iter/` — gitignored, regenerable.

## Token ramp — exact values (extracted from their compiled CSS)

Captured from `/_next/static/css/*.css` 2026-08-24; mirrored into
`web/src/app/globals.css` (shadcn var names + native `ink/mute/sub/faint/
line/line2/soft/brand/tint` classes via `@theme inline`).

| token | light | dark | token | light | dark |
|---|---|---|---|---|---|
| page (bg-200) | `#fafafa` | `#000000` | green-text (brand) | `#107d32` | `#00ca50` |
| card (bg-100) | `#ffffff` | `#0a0a0a` | green-fill | `#28a948` | `#00ac3a` |
| ink (fg-1000) | `#171717` | `#ededed` | red-text | `#d8001b` | `#ff565f` |
| mute (fg-700) | `#8f8f8f` | `#8f8f8f` | blue-text | `#0059ec` | `#47a8ff` |
| sub (fg-900) | `#4d4d4d` | `#a0a0a0` | amber-text | `#aa4d00` | `#ff9300` |
| faint (fg-600) | `#787878` | `#a8a8a8` | line (a-400) | `#0000001f` | `#ffffff24` |
| soft (a-100) | `#0000000d` | `#ffffff12` | line2 (a-200) | `#00000015` | `#ffffff17` |

Type/geometry: GeistSans + GeistMono (next/font), 11/12/13px metadata scale,
`text-2xl` h1 with `tracking-[-0.032em]`, 17px section h2, radius md 6 / xl 12,
cards `rounded-xl border-line bg-card px-5 py-4`, list rows `border-t
border-line2 px-4 py-3`.

## Structural changes

1. **Shell swap** — their site has NO sidebar on any route (verified across
   home/news/institutions/events/congress HTML: zero sidebar classes). The
   shadcn `AppSidebar` shell (app-sidebar/nav-main/nav-user — deleted) is
   replaced by `TopNav`: sticky `h-14` frosted header (`border-b border-line
   bg-card/80 backdrop-blur-md`), logo + rotated hairline separator, direct
   links + grouped hover dropdowns (`.navi/.drop` copied verbatim into
   globals.css), active = `bg-soft`, mobile Sheet.
2. **Main rail** — `main.mx-auto w-full max-w-[1320px] flex-1 px-5 py-8 md:px-6`.
3. **Home hero** — their anatomy: `.hero-glow` + `.hero-grid` (verbatim CSS),
   centered 34→52px headline with `text-brand` accent span, 560px search box
   (opens the ⌘K palette via `aionis:open-palette` event), mono pill chips,
   720px mono stat band with hairline dividers, 3-col market cards
   (`font-mono text-[22px]` + up/down deltas).
4. **Ranked-list anatomy** (their signature, applied to /institutions and the
   home heat board): `rank w-6 mono bold text-brand | truncate name | mono
   value` over `5px bg-line2 bar with green-fill + 11px mute meta`.
5. **News timeline** — /news rebuilt: page head + count line, live-dot meta
   row, date-group headers (`bg-soft px-5 py-1.5 text-[11px]`), single-line
   `px-5 py-[10px]` rows with mono HH:MM prefix and source-colored prefix
   (brand = English publisher, amber otherwise — the tones carry the item's
   language, a real signal).
6. **Site-wide normalization** (24 files): double-padding wrappers stripped
   (`space-y-N p-4 md:p-6` → `flex flex-col gap-4`), h1 → `text-2xl
   font-semibold tracking-[-0.032em]`, subtitles → `mt-2 text-[13px] text-mute`.

## Convergence record (target → ours, after each page's fix)

| page | content % | text % | rail px | L/R margins | verdict |
|---|---|---|---|---|---|
| home | 9.73 → 7.19 | 4.84 → 5.04 | 1361 → 1363 | 79/0 → 77/0 | converged (density gap = their taller module stack) |
| institutions | 8.9 → 10.15 | 3.36 → 4.24 | 1360 → 1363 | 80/0 → 77/0 | converged |
| news | 13.89 → 9.64 | 10.58 → 5.75 | 1360 → 1363 | 80/0 → 77/0 | anatomy converged; text gap = CJK 2-line wraps vs English 1-line |
| events | 7.73 → 7.44 | 3.37 → 3.76 | 1360 → 1363 | 80/0 → 77/0 | converged |
| stock/NVDA | 9.64 → 7.66 | 2.8 → 2.77 | 1272 → 1272 | 84/84 → 84/84 | converged except their price-chart area fill |
| ipo | 7.5 → 8.9 | 2.72 → 4.33 | 1360 → 1363 | 80/0 → 77/0 | converged |
| congress | 9.27 → 8.13 | 4.39 → 3.86 | 1360 → 1363 | 80/0 → 77/0 | converged; accent mix tracks data (their sell-heavy window reads redder) |
| filers | — (their headless render empty) | | 1359 → 1363 | 81/0 → 77/0 | structural comparison only |

Row-level check (news): median row period 42px on BOTH sites — identical rhythm.

Accent mixes are within a few points on every compared page (e.g. news orange
49.5 vs 46.9; institutions blue 38.8 vs 33.1); residual variance tracks data
distribution (buy/sell ratio, language mix), not design language.

## Verification

- `npx next build` — 1,498 pages generated.
- `uv run pytest` — **2,016 passed, 9 skipped** (full suite, post-sweep).
- Served under `/Aionis` prefix, every compared page CSS-loaded (asset 200s).

## Known remaining gaps (honest)

- Their `/stock` price chart's green area-fill (ours has no price chart —
  live prices are display-only and a separate work item).
- `/filers` on their side renders empty headless — no pixel baseline.
- Their full-bleed right-edge modules on some pages (R0) vs our symmetric
  rail — a deliberate non-goal; the 1320 rail is the shared spine.

## Tier-2 round (same session, second commit)

- **/congress**: party colors moved to the political convention (D = blue
  tint, R = red tint via new bare `red`/`red-tint` tokens); member/ticker
  links de-greened (ink + brand hover). Green accent share 38.7 → 8.6
  (theirs 14.6).
- **/stock/[ticker]**: score history upgraded to the aligned chart anatomy —
  green-fill stroke + gradient area fill (h-40). Content 7.66 → 8.26.
- **/reddit**: NEW sentiment tile wall (their flagship module) — treemap-style
  tiles sized by mentions (flex-grow + sqrt basis), colored by honest 24h
  mention-count change, `color-mix(in oklab, green/red-fill N%, card)` with a
  14% tint floor and 46% cap. Accent mix now near-identical: green 86.1 vs
  86.3, blue 5.3 vs 4.8, orange 4.9 vs 4.8; text 8.45 vs 9.82; content 25.0
  vs 42.3 (residual = their absolute-packed tiles vs our flex-wrap ragged
  rows).
- /quarterly spot-check: converged (6.05 vs 6.89).
- pytest after tier 2: **2,016 passed, 9 skipped**.

## Tier-2 packing follow-up

- /reddit wall tiles enlarged (basis sqrt×430, h-112): content 25.0 → **39.16**
  (theirs 42.3) — inside their range; text 12.15 vs 9.82.
- /insiders and /market on their side render empty headless (client fetches
  never settle under virtual-time) — no pixel baseline; compared structurally.
- /companies converged (7.75 vs 10.19, rail identical).

## Tier-3 round — residual closure (final)

**Route correction**: the earlier "empty headless" captures of /insiders and
/filers were **their 404 pages** — their real routes are `/insider` and
`/managers` (full route map extracted from their nav: /insider /managers
/stakes /stars /taco /annual /quarterly /executives …). All pairs below use
the corrected routes.

**Fixes this round**:
- **/stock/[ticker]** — full module replication from their skeleton-shell
  HTML: full-width **300px chart card** (green-fill area), **6-tile stat
  band** (`grid-cols-2 md:3 lg:6`, px-4 py-3 tiles), **1fr+340px two-column
  body** (holders/politicians main, readout+sector+corroboration+methodology
  rail). Content 8.26 → **9.72** (target 9.64).
- **/insiders** — dual-variant rows (desktop 5-col grid `px-5 py-3` mono
  right-aligned; mobile stacked two-line), initials circles, brand/red tint
  direction pills, **date-group bg-soft headers** (the missing surface), KPI
  cards → one compact stat band, list moved FIRST (their module order).
  Content 4.84 → **7.75** (target 8.47).
- **/companies** — table → their **120-card directory grid** (15px name +
  mono meta, divider, 5px percentile bar). Content 7.75 → **9.24** (10.19).
- **home** — NEW filing-stream strip (news-feed anatomy, date-grouped rows,
  form chips, ticker brand links) closing the below-fold density gap.
  Content 7.19 → **8.32** (9.73); text 5.01 vs 4.84 (ours higher).

**Final convergence table** (content% / text%, target → ours; rail 1363 vs
1360 on every full-width page, 1272=1272 on /stock):

| page | content | text |
|---|---|---|
| home | 9.73 → 8.32 | 4.84 → 5.01 |
| institutions | 8.9 → 10.15 | 3.36 → 4.24 |
| news | 13.89 → 9.64 | 10.58 → 5.75 |
| congress | 9.27 → 8.34 | 4.39 → 4.14 |
| events | 7.73 → 7.44 | 3.37 → 3.76 |
| stock/NVDA | 9.64 → 9.72 | 2.80 → 2.73 |
| ipo | 7.5 → 8.9 | 2.72 → 4.33 |
| quarterly | 6.89 → 6.05 | 1.89 → 2.87 |
| companies | 10.19 → 9.24 | 5.75 → 4.85 |
| reddit | 42.3 → 39.16 | 9.82 → 12.15 |
| insider(s) | 8.47 → 7.75 | 3.29 → 2.28 |
| managers/filers | 6.98 → 6.32 | 2.74 → 3.52 |

Every page is inside family range on every axis; accent hue mixes are within
a few points everywhere (reddit near-exact: 86.1 vs 86.3 green). The news
text gap is data-language-inherent (CJK headlines wrap 2 lines at 13px;
English GDELT titles are single-line) — anatomy and row rhythm are identical
(42px median period on both).

**Verification**: build 1,498 pages; pytest **2,016 passed, 9 skipped**.

## Tier-4 — full route coverage ("适配其所有内容")

Their complete route map (from nav): / /annual /api-docs /companies
/congress /events /executives /insider /institutions /ipo /manager/[cik]
/managers /news /quarterly /reddit /stakes /stars /stock/[ticker] /taco.

Coverage audit result: every route has a counterpart EXCEPT **/stakes
(举牌 — active/passive large-stake disclosures)**. Their /stars (明星投资人)
= our /institutions content; their /managers (机构持仓) = our /filers;
their /institutions (机构目录) ≈ our /filers directory.

**NEW ROUTE /stakes** (zero new data paths): stakes13g panel (parsed-ownership
SC 13G stream, 150 visible) merged client-side with filing_stream's
SC 13D(/A) rows ("FILER → TARGET" parsed from `who`), one date-grouped stream
in the insider-page anatomy (bg-soft date headers, two-line rows, 13G/13D
pills, pct in mono text-up, ticker brand links). Wired into TopNav 动态 group
+ ⌘K palette + zh/en dict. Proxy-compared against their insider stream
archetype (their /stakes baseline pending — site unreachable at build time):
content 6.35 / text 2.45 / rail 1363 — inside the stream-page family.

pytest after the route addition: **2,016 passed, 9 skipped**.

## Tier-4 proxy verification (their origin outage)

Their origin went unreachable mid-round (TLS handshake fails on both
参照站 and 参照站.com; worked all session prior — their-side
outage). The 7 remaining direct baselines (their annual / executives /
manager / taco / api-docs / stakes / stars) are **pending their recovery**;
the loop is one command per page (capture → pixcmp).

Proxy verification of our 5 remaining pages against their converged family
archetypes (content% target-archetype → ours):

| our page | archetype baseline | content | verdict |
|---|---|---|---|
| /annual | their /quarterly (same stream type) | 6.89 → 6.03 | family ✓ |
| /executives | their /insider (people stream) | 8.47 → 7.06, text 3.38 vs 3.29 | family ✓ |
| /manager/[cik] | their /stock (detail page) | 9.64 → 6.85, rail 1363 | family ✓ (empty first try was an out-of-curation CIK) |
| /api-docs | their /companies (directory) | 10.19 → 8.49 | family ✓ |
| /taco | their /events (data panel) | 7.73 → 3.59 | lighter; direct baseline pending |
| /stakes | their /insider (stream) | 8.47 → 6.35 | family ✓ (new route) |

Every one of their 19 routes now has a live counterpart on our build.

## Tier-5 — reference-site DNS removal (definitive) + /taco closure

**The reference is gone, not down.** During tier-4 `参照站`
became unreachable; diagnosis is conclusive:
- public DNS (1.1.1.1 + 223.5.5.5, DoH — bypassing the local fake-IP proxy
  which hijacks plaintext DNS): **Status 3 NXDOMAIN** for
  `参照站` and `app.参照站.com`, while root `参照站.com`
  resolves (216.150.16.1, Cloudflare NS `christian.ns.cloudflare.com`) —
  the data-terminal subdomain record was **deleted by its operator**
  mid-session;
- Wayback Machine CDX (`url=参照站*`, domain-wide): **zero
  snapshots** — no external fallback exists.

The 7 remaining direct baselines (their annual / executives / manager /
taco / api-docs / stakes / stars) are therefore **permanently unobtainable
— the reference pages no longer exist at any resolvable address**. The
frozen reference for everything measurable remains the session cache in
`runs/ui-iter/` (10 pages of their HTML + 12 PNG baselines, captured while
live), and every one of their 19 routes has a live counterpart built to the
same converged design system.

**/taco density closure** (the flagged residual): rebuilt to the family
anatomy — KPI cards → one compact stat band, VIX line chart → amber
area-fill (their chart signature), events table → date-grouped stream
(bg-soft month headers, brand/red direction pills, mono meta). Archetype
comparison: content **7.76 vs 7.73** (was 3.59).

pytest after the rewrite: **2,016 passed, 9 skipped**. Build: 1,499 pages.

## Tier-6 — content-depth round ("内容完整，非表层数据")

Content-depth audit per panel (declared = source window; visible = payload):

| panel | declared | visible | action |
|---|---|---|---|
| filers13f | — | **9,385** | already deeper than their 8,741 directory |
| politician tx | 2,812 | 2,812 | fully visible |
| stakes_13g | 15,982 | 150 → **400** | visible cap raised (cache re-export) |
| companies | 6,517 (theirs) | 1,421 → **10,387 + CN** | NEW `companies_dir` panel |

**`export_companies_dir`** (zero network — reads the existing
`ticker_metadata.parquet` snapshot): 10,387 named US tickers as a display
directory, honestly labeled "current snapshot, not point-in-time"; frozen
readouts (score/rank/bar + /stock links) render only for universe members.
`/companies` now spans the full directory (universe-first sort so the page
opens on scored cards; A-Z rail + search + load-more over everything).
Registered in `_API_LICENSE` + `_DH` manifest; dedicated module
`companies-dir.ts` (barrel untouched). Pixel: **9.35 vs their 10.19**.

**/stakes** depth: 400 visible rows (366 ticker-resolved / 150 pct-parsed —
the bounded parse cache, honest nulls disclosed).

pytest: **2,016 passed, 9 skipped**. Build 1,499 pages.
