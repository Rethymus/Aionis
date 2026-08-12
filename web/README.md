# Aionis Terminal — the validity-argument chain (web UI)

> The browser-rendered research surface for [Aionis](../README.md): a falsifiable,
> **anti-leakage** stock-selection research harness. This is the display layer —
> it never touches the frozen research pipeline, the ledger, or out-of-sample data.

**Live**: <https://rethymus.github.io/Aionis/> · **Research README**: [`../README.md`](../README.md)

---

## What this terminal is — and is not

It is **not** a trading bot, a prediction engine, or an "AI stock picker". It is a
**validity-argument chain**: one falsifiable claim's argument, made visible. Every
page declares its place on the chain, every number carries provenance, and the
headline verdict (currently **NULL**) is framed as the intended, publishable outcome.

The headline claim: *does adding alt/fundamental factors beat a price-only baseline
on cross-sectional monthly rank-IC of S&P 500 PIT constituents?* The confirmatory
answer (ledger #49): combined rank-IC **−0.0088**, 95% CI `[−0.034, +0.016]`, p=0.484
— **null**.

## The information architecture (paradigm α — ECD)

The terminal is organized as a single falsifiable claim's argument, not as an
analyst workflow. The spine is:

```
  语境 Context  →  证据 Evidence  →  效度 Validity  →  裁决 Verdict
  (market regime)  (model picks +      (calibration,       (null + honest
                     corroboration)      power floor)        disclosure)
                        └──── 守卫 Guard spans the whole chain ────┘
                         (PIT · embargo · H6 · provenance)
```

Every page carries a **SegmentHeader** breadcrumb showing its place on the chain
(the current segment highlighted), a **provenance chip** (as-of date), and a guard
link. There are no numbered steps, no "定调/定标/佐证/问责" role labels — the
structure emerges from the falsifiability argument.

### Routes

| Route | Segment | What it shows |
|---|---|---|
| `/dashboard` | — (overview) | Verdict anchor + the full chain + research-at-a-glance + guard band |
| `/regime` | Context | market · COT positioning · TACO · macro (the claim's market domain) |
| `/picks` | Evidence · core | model picks · sectors · conviction · factor families |
| `/confirmation` | Evidence · corroboration | 13D smart money · Form 4 insiders · Reddit · news |
| `/track` | Validity | calibration · power floor · model health · cost · **AI attribution** · evidence wall |
| `/discipline` | Guard | anti-leakage discipline + evidence wall (why the argument is trustworthy) |
| `/themes` | full chain | the argument-chain diagram (ECD warrants) + **factor coverage map** |

## The AI surfaces — and the compliance rule

AI contributes **interpretation and coverage**, never an out-of-sample signal.

1. **AI attribution** (`/track`) — a deterministic, hand-anchored narrative of *why*
   the frozen null is null (IC magnitude, CI bracketing zero, power-floor
   unattainability, discipline). Pure function of the already-frozen public numbers;
   no external call, no side-effect.
2. **Factor coverage map** (`/themes`) — the 5 canonical factor families ×
   tested/exploratory/gaps, each "tested" cell anchored to a frozen ledger row,
   "gaps" citing canonical academic anomalies (MAX, BAB, 52-week-high, …).
3. **Research-at-a-glance** (`/dashboard`) — compact digests of both, with deep-dive
   links.

> **Hard rule (leakage guard):** LLM features in the frozen out-of-sample pipeline
> are a **known leakage channel** (training corpora contain future information;
> ChronoBERT / Look-Ahead-Bench / DatedGPT document this). Therefore AI is confined
> to OOS-*out* roles (attribution, coverage, exploratory hypothesis generation). Any
> new factor a future AI track proposes = a new preregistration + a new
> `config_committed` ledger row + an independent OOS walk-forward — never a silent
> edit to the frozen surface. A live-LLM attribution variant is gated on explicit
> owner approval (external, irreversible call).

## Architecture & anti-leakage separation

```
web/src/
  app/(dashboard)/{route}/page.tsx   — thin route shells
  components/
    overview/     — Overview, VerdictAnchor, ArgumentChain, ResearchGlance, GuardBand
    segment-header.tsx    — the spine breadcrumb (+ provenance + guard)
    provenance-badge.tsx  — uniform "as of" chip
    themes/argument-chain-diagram.tsx — the ECD warrant chain
    ai/attribution-card.tsx   — why-null (Track B, display-only)
    ai/coverage-map.tsx       — factor-family coverage (Track C, display-only)
  i18n/dict.ts   — zh + en (bilingual)
  data/aionis/  — JSON panels (regenerable, gitignored source; exported by scripts/export_terminal_data.py)
```

The terminal reads only exported JSON panels. The export pipeline
(`scripts/export_terminal_data.py`) is the **only** bridge from the research
pipeline to the display layer, and it never exports forward-looking or unfrozen OOS
metrics. Live prices (Cloudflare Worker) are **display-only** and never enter the
research modules.

## Develop

```bash
cd web && npm install && npm run dev      # http://localhost:3000
npm run build && npm run start            # production
```

Deploy is automatic via GitHub Actions (`Deploy Static Site to GitHub Pages`) on
push to `main`.

## Design provenance

The IA paradigm and AI-compliance layer are documented in:
- `reports/design/2026-08-12-terminal-ia-paradigm-shift.md` — the α paradigm + ECD/ModelCards/Compendium grounding
- `reports/design/2026-08-12-terminal-ia-paradigm-alpha-migration.md` — the per-file migration spec
- `reports/design/2026-08-12-scientific-research-system-synthesis.md` — frontier research (Fan 2026 agentic loop, Harvey-Liu-Zhu multiple-testing, López de Prado DSR, Gu-Kelly-Xiu, the LLM-lookahead-bias literature) anchored to Aionis's null stance

**Standing on giants**: Evidence-Centered Design (Messick / SRI), Model Cards &
Datasheets (Gebru / Mitchell), Executable Research Compendium (rOpenSci / Turing
Way / OSF), data provenance / observability (QVeris evidence-first).
