# Aionis Terminal — the validity-argument chain (web UI)

> The browser-rendered research surface for [Aionis](../README.md): a falsifiable,
> **anti-leakage** stock-selection research harness. Display layer only.

**Live**: <https://rethymus.github.io/Aionis/> · **Research README**: [`../README.md`](../README.md)

## What this terminal is — and is not

Not a trading bot, not a prediction engine, not an "AI stock picker". It is a
**validity-argument chain**: one falsifiable claim's argument, made visible. Every
page declares its place on the chain, every number carries provenance, and the
headline verdict — currently **NULL** — is framed as the intended outcome. The
claim: *does adding alt/fundamental factors beat a price-only baseline on
cross-sectional monthly rank-IC of S&P 500 PIT constituents?* The confirmatory
answer (ledger #49): combined rank-IC **−0.0088**, 95% CI `[−0.034, +0.016]`,
p=0.484 over 71 months — **null**.

## The information architecture (paradigm α — ECD)

```
  语境 Context  →  证据 Evidence  →  效度 Validity  →  裁决 Verdict
  (market regime)  (model picks +      (calibration,       (null + honest
                     corroboration)      power floor)        disclosure)
                        └──── 守卫 Guard spans the whole chain ────┘
                         (PIT · embargo · H6 · provenance)
```

Every page carries a **SegmentHeader** breadcrumb (its place on the chain) and a
**provenance chip** (as-of date). The chain is the spine; around it the terminal
has grown a PIT data directory and filing/event streams that feed corroboration.

## Routes (38 under `(dashboard)/`, plus `/` → redirect to `/dashboard`)

### 研究链 · Argument chain

| Route | What it shows |
|---|---|
| `/dashboard` | Overview — verdict anchor, the full chain, research-at-a-glance, guard band |
| `/regime` | Context — macro context & market-regime read |
| `/picks` | Evidence core — the model's current stock picks |
| `/conviction` | Pick conviction — conviction ranking of the current picks |
| `/confirmation` | Corroboration hub (tabbed): 13D smart money · Form 4 insiders · Reddit · news |
| `/track` | Validity hub (tabbed): calibration · power floor · model health · cost · AI attribution · evidence wall |
| `/evidence` | Evidence wall — corroborating evidence behind the picks |
| `/shelf` | Method shelf & research links out |
| `/atlas` | Research atlas — editorial diagrams: claims · divergence · diagnostics · lineage |
| `/model-health` | Model-health diagnostics |
| `/calibration` | Calibration reliability |
| `/power-floor` | Power floor — the minimum effect this design could detect |
| `/positioning` | Positioning — long/short pressure & COT z-reads |

### 数据目录 · Data directory

| Route | What it shows |
|---|---|
| `/companies` | Listed-company directory (A–Z) |
| `/stock/[ticker]` | Per-stock drill-down — statically generated for the frozen OOS universe only |
| `/manager/[cik]` | Per-manager drill-down — star-manager 13F registry, keyed by EDGAR CIK |
| `/institutions` | Star managers' real 13F books |
| `/filers` | 13F filer directory — every filing institution |
| `/heatmap` | Cross-sectional score heatmap |
| `/sectors` | Sector probabilities |
| `/executives` | Officer profiles & boards |

### 事件流 · Event streams

| Route | What it shows |
|---|---|
| `/events` | Material events (8-K): M&A / officers / delisting filings |
| `/insiders` | Insiders — Form 4 activity |
| `/smart-money` | Smart money — 13D filings |
| `/stakes` | 举牌 — active/passive large-stake (13G) disclosures |
| `/congress` | Congressional trading disclosures |
| `/reddit` | Retail buzz |
| `/news` | Market news feed |
| `/ipo` | IPO calendar — pricing, listings & registration |
| `/annual` | 10-K annual-report filing stream |
| `/quarterly` | 10-Q quarterly-report filing stream |
| `/taco` | TACO index |
| `/market` | Market panorama |
| `/force-camp` | Force camps — institutions · people · stake networks |

### 元页面 · Meta

| Route | What it shows |
|---|---|
| `/data-health` | Data health — freshness/provenance of every panel |
| `/api-docs` | The static data API catalog |
| `/discipline` | Guard — anti-leakage discipline (why the argument is trustworthy) |
| `/themes` | The argument-chain diagram (ECD warrants) + factor coverage map |

`/track` and `/confirmation` are tabbed hubs that embed the standalone views, so
every tab (`/calibration`, `/power-floor`, `/model-health`, `/evidence`,
`/discipline`, `/smart-money`, `/insiders`, `/reddit`, `/news`) is also an
independently routable page.

## AI surfaces — and the compliance rule

AI contributes **interpretation and coverage, never an out-of-sample signal**: the
**AI attribution** card (why the frozen null is null — a pure function of
already-frozen public numbers) and the **factor coverage map** (factor families ×
tested/exploratory/gaps, anchored to frozen ledger rows).

> **Hard rule (leakage guard):** LLM features in the frozen out-of-sample pipeline
> are a known leakage channel. AI stays in OOS-*out* roles. Any AI-proposed
> factor = a new preregistration + a new `config_committed` ledger row + an
> independent OOS walk-forward — never a silent edit to the frozen surface.

## Architecture & anti-leakage separation

```
web/src/
  app/(dashboard)/{route}/page.tsx — thin route shells (38 routes)
  components/
    overview/   — Overview, provenance anchor, research glance, trust ribbon
    ai/         — attribution-card (why-null), coverage-map (display-only)
    segment-header.tsx / provenance-badge.tsx — spine breadcrumb + as-of chip
    {domain}/   — one view directory per route (picks/, institutions/, taco/, …)
  i18n/dict.ts  — single typed zh+en dictionary (zh is the canonical key set)
  data/aionis/  — 56 JSON panels (committed aggregated outputs — the
                  gitignore's explicit `!web/src/data/` exception; never raw
                  data or runs/ parquet)
web/scripts/build-api.mjs — `prebuild`: mirrors every panel JSON into
  public/api/v1/ (catalog.json · health.json · panels/*.json · openapi.json);
web/scripts/i18n-audit.mjs — orphan-key audit of the dictionary
```

**Data layer.** The terminal reads only exported JSON panels; the export pipeline
(`scripts/export_terminal_data.py`, repo root) is the **only** bridge from the
research pipeline and never exports forward-looking or unfrozen OOS metrics. The
data-health registry tracks **54 panels** (19 frozen / 25 daily / 10 cadence)
across 56 JSON files on disk; `prebuild` re-mirrors them into a read-only static
data API (`/api/v1/…`, OpenAPI 3.1) served from GitHub Pages, so the deployed API
can never drift from the panels the terminal renders.

**Honesty constraints (binding).** Every number carries an as-of watermark;
drill-down links are **universe-gated** (`/stock/[ticker]` exists only for the
frozen OOS universe; `/manager/[cik]` only for the committed star-manager
registry); live prices via the Cloudflare Worker (`workers/prices/`) are
**display-only** and never enter research modules; AI never produces OOS signals.

## Develop (pnpm — see `pnpm-lock.yaml`)

```bash
cd web
pnpm install
pnpm dev        # next dev → http://localhost:3000 (basePath /Aionis is prod-only)
pnpm build      # prebuild mirrors the static API, then static-exports the site
pnpm lint       # eslint
```

Next.js runs with `output: "export"` (static site, no Node server) and
`basePath: "/Aionis"` in production. Deploy is automatic via GitHub Actions:
`Deploy Static Site to GitHub Pages` on push to `main`, plus the daily
`Refresh terminal data` workflow (22:00 UTC Mon–Fri) that re-exports the panels
and triggers the Pages deploy.

## Design provenance

The IA paradigm and AI-compliance layer are documented in
`reports/design/2026-08-12-terminal-ia-paradigm-shift.md` (the α paradigm +
ECD/ModelCards/Compendium grounding) and the companion migration and
frontier-research syntheses in the same directory.
