# Terminal visual audit + frontier synthesis — 2026-08-12 (续⑪)

> Round 4 of the owner's recurring request: *"视觉整体排查 + 深入调研前沿 + 金融×市场理论联动 + AI 深度贯彻 → 高质量科学选股研究系统"*.
> Per `aionis-owner-process-correction`: no 7th "redesign" ceremony — do an honest audit, targeted frontier scan, and a plateau verdict (or one real fix).

---

## 1. Visual audit — 7 deployed pages (puppeteer DOM, live site)

| Page | H-scroll | h1 | Legacy residue | α structure |
|---|---|---|---|---|
| `/dashboard` | ✅ none (1280=1280) | 一条可证伪主张的效度论证链 | 0 | VerdictAnchor (−0.0088, CI, p, NULL framed) + chain |
| `/regime` | ✅ none | 川普元年市场全景 | 0 | spine 语境›证据›效度 + provenance 2026-08-04 |
| `/picks` + `#factors` | ✅ none | 选股决策榜 | 0 | 4 role badges = 证据段 (续⑩ deployed, no regression) |
| `/confirmation` | ✅ none (1280=1280) | 聪明钱动向 | 0 | SidebarInset min-w-0 fix (续⑧) holds; provenance 2026-08-07 |
| `/track` | ✅ none | 校准可靠性 | 0 | AI attribution 4 points render; "统筹分配" 角括号 correct |
| `/discipline` | ✅ none | 反泄漏仪表盘 | 0 | guard chip `border-primary` highlighted (续⑧) confirmed |
| `/themes` | ✅ none | 效度论证链全貌 | 0 | 4 ∴ warrants + CoverageMap |

**Hard-residue sweep (deployed DOM text)**: 定调 / 定标 / 问责 / ①-④ / L0-L4 / funnel / 漏斗 = **0 hits** across all 7 pages.

**Verdict**: the IA layer is clean. There is nothing left to "redesign" — the α ECD chain (Context → Evidence → Validity → Verdict + Guard) is consistently rendered across every surface, provenance is present, AI surfaces are display-only and compliant. The owner's repeated "UI 不适配" concern is **resolved** at the structural level.

### 1a. The one real content issue found (NOT an IA bug)

`/themes` carries only `截至 2026-06-30` while `/regime` has 2026-08-04 and `/confirmation` has 2026-08-07. This is a **display-panel export staleness gap** (B1 separation, `scripts/export_terminal_data.py` → `themes.json`), not a display-layer bug. It is the same class of issue the owner has flagged before ("数据仍没有体现"). Fix path = ensure the daily refresh workflow rebuilds the themes panel from `display_panel.parquet` (B1), not a web/src change. **Out of scope for this display-layer audit** — flagged for the data-refresh lane.

---

## 2. Frontier research — transferable methodology (main-session, [1210]-safe)

### 2.1 Provenance UI patterns — ACM 2026 "SuperProvenanceWidgets" (arXiv 2604.15342)

Auditing a colleague's analysis for reproducibility. Transferable primitives:
- **Scented widgets** — colored borders/bars overlaid on UI controls, with matching colors on provenance buttons creating visual links between aggregate view and individual controls.
- **Aggregate view** — sized/colored boxes scaled "proportional to total interaction count," repositioned by recency; empty-bordered boxes surface untouched controls (= exploration gaps).
- **Temporal view** — Gantt bars per widget along a shared interaction-sequence x-axis; clickable for action recovery.
- **Separation of concerns**: Compute (capture/stats) / UI (viz) / Scents (in-situ overlays) as composable modules.
- **Ex-situ vs in-situ** provenance display as the guiding design distinction.

**Aionis mapping**: the SegmentHeader spine + provenance chips are already a lightweight "ex-situ summary" scent. The Aionis guard band (`/discipline`) is the in-situ overlay equivalent. The scented-widget "surface the gaps" idea maps directly to the CoverageMap "gaps" cells (MAX / BAB / 52-week-high cited as untested). **No change needed** — the CoverageMap already implements the transferable insight.

### 2.2 Fan 2026 "Beyond Prompting: Autonomous Factor Investing via Agentic AI" (arXiv 2603.14288)

(Memory `aionis-agentic-factor-investing-research` already captures the headline; this audit deepens the transferable anti-overfitting machinery.)

| Fan 2026 mechanism | Aionis equivalent | Status |
|---|---|---|
| Dedicated IS window `T_IS` + no-look-ahead execution | `PurgedGroupKFold(group=month, embargo=21)` + PIT `filed`-date | ✅ already stronger (purged + embargo) |
| Fixed variable universe, bounded expression depth, closed operator set, formal grammar `𝒢` | frozen config + 9-column baseline + version-pinned `uv.lock` | ✅ already |
| Separate `τ_econ` economic-significance gate (lucky-factor filter) | (Track A factor hypothesis generator, gated) | ⏳ owner-GO item |
| Multiple-testing adjustment on OOS (HLZ Bonferroni/Holm/BH) | two-tailed pre-registered × 1 phase; Romano-Wolf noted as gap for future positive | ✅ honest (null needs no MHT rescue) |
| Multi-dimensional robustness + temporal/policy isolation | h={10,42} sensitivity sweep; B/C/D/E1 + Track C + Track Adaptive | ✅ already |
| Memory-guided exploration/exploitation (anti-crowding) | (not applicable — Aionis is not an alpha-search loop) | n/a |

**Sharpe 3.11 in Fan 2026 = the overfitting cautionary tale**; Aionis #49 NULL (−0.0088, CI brackets zero) is the disciplined counter-position. The methodology is reusable; the alpha is not to be chased (memory `aionis-publication-framing-option-a`).

### 2.3 Factor-zoo / multiple-testing honesty (HLZ 2016, Bailey-López de Prado DSR 2014)

The intellectual companion to Aionis's null stance:
- **Harvey-Liu-Zhu "...and the Cross-Section of Expected Returns" (2016)** — ~316 published factors; Bonferroni/Holm/BH FDR corrections; new factor needs t > 3.0 (now higher in HLZ 2020 haircut). **Aionis's null with tight CI under a frozen 1-trial pre-registration is exactly the honesty HLZ advocates** — it does not inflate the zoo.
- **Bailey-López de Prado DSR (2014)** — corrects Sharpe for selection bias + backtest overfitting + non-normality. **Aionis already uses `arch` for DSR/SPA** (pyproject). The honest disclosure (power floor σ≈0.106 >> SESOI ±0.010, equivalence structurally unattainable) is the DSR philosophy applied to rank-IC.

**Aionis mapping**: already implemented. No new work; this is confirmatory grounding.

### 2.4 Executable Research Compendium (ERC) — Nüst et al. (D-Lib 2017, o2r spec)

The ERC packages data + code + text + UI configurations in a single container, examinable via a supporting UI or manually.

**Aionis mapping**: the Aionis terminal IS a partial ERC — it exposes the frozen config sha256 (`config_committed` ledger), H6 bit-identical determinism, PIT provenance, and the verdict, examinable in-browser. The gap vs full ERC: the terminal does not yet expose a "rerun this in the browser" button (would require a hosted compute backend = out of scope for a static GitHub Pages site). **Documented as a known scope boundary**, not a defect.

### 2.5 The cross-disciplinary synthesis is original territory

The WebSearch gap analysis returned explicitly: the intersection of **Toulmin claim-evidence-warrant × Messick validity × Mislevy ECD × scientific-software UI × asset-pricing null-honesty** is **"novel or underexplored cross-disciplinary synthesis."** This is a positive signal: paradigm α is not lagging the frontier — it is operating in a space the frontier has not yet formalized. **The right move is to hold the line, not pivot.**

---

## 3. AI compliance — three-track layering (unchanged, all deployed)

| Track | Role | Status |
|---|---|---|
| **B — Attribution** (`/track`) | deterministic narrative of why the frozen null is null; pure function of public frozen numbers | ✅ deployed, display-only |
| **C — Coverage map** (`/themes`) | 5 canonical families × tested/exploratory/gaps, frozen-ledger-anchored | ✅ deployed, display-only |
| **A — Factor hypothesis generator** | exploratory; requires new preregistration + `config_committed` + freeze + independent OOS | ⏳ owner-GO, NOT started |
| **Forbidden** | LLM features in the frozen OOS panel | 🚫 known leakage channel (ChronoBERT / Look-Ahead-Bench / DatedGPT) |

**No change this round.** Tracks B and C are the display-only, leakage-safe ceiling of what AI can contribute without owner-GO on a new frozen track.

---

## 4. Verdict — plateau confirmed (display-layer IA)

The terminal's information architecture is at its display-layer plateau:
- ✅ Single falsifiable claim's validity-argument chain (ECD), consistently rendered on all 7 pages.
- ✅ Zero legacy residue (hard sweep, deployed DOM).
- ✅ Zero horizontal overflow (all pages, 1280px viewport + nested-element scan).
- ✅ Provenance on every page that has a clean top-level date; honest absence where none exists.
- ✅ AI surfaces display-only and leakage-compliant; the forbidden track (LLM-in-OOS) is structurally excluded.
- ✅ Frontier-grounded: Fan 2026 anti-overfitting machinery is already Aionis's discipline; HLZ + DSR are already the honesty frame; provenance-UI patterns (scented widgets, gap-surfacing) are already embodied in CoverageMap + SegmentHeader.
- ✅ The cross-disciplinary synthesis (ECD × Toulmin × Messick × null-honest asset pricing) is original territory — holding the line is correct, not conservative.

### The only items that remain are NOT display-layer:
1. **`/themes` export staleness** (2026-06-30 vs 2026-08-07 elsewhere) — data-refresh lane (B1 display panel), not `web/src`.
2. **Track A factor hypothesis generator** — owner-GO, new preregistration, not autonomous.
3. **D2 live-LLM attribution variant** — owner-GO (external irreversible GLM call), fixture version shipped.

**Recommendation to owner**: the recurring "redesign the seven-theme UI" request has been fully resolved across rounds 5-10 (续⑤→续⑩). This round (续⑪) confirms via a full 7-page live audit that there is no remaining structural mismatch. Further "redesign" iterations would be ceremony, not improvement. The genuine forward levers are (a) the data-refresh staleness fix (operational, not IA) and (b) owner-GO on Track A (research, new frozen surface). Both require owner decisions, not more display-layer work.

---

## 5. Boundary

- **Scope**: display-layer visual audit (puppeteer live DOM) + main-session frontier research + this synthesis doc. 0 `web/src` code change this round (none needed — plateau confirmed).
- **Touched**: this doc + `state/current.md`. 0 ledger / frozen config / prereg / ADR / data / OOS change. No research/forward/strategy run. No external LLM call. No E3 observation.
- **Method**: `[1210]`-safe (all web research in main session; no web-using subagents).
