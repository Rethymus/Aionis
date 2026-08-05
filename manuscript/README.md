# Aionis — arXiv Preprint Scaffold

> **Status: v0.1-prep · 2026-08-05 · NOT submitted.** Owner approved framing (a)
> (power-floor theorem as lead contribution) and LaTeX scaffolding. **arXiv upload
> is NOT authorized** — it is an irreversible externalization requiring a separate
> explicit owner sign-off. This folder is the "one-click upload" prep.

## Framing

Framing **(a)** — the power-floor theorem is the lead methodological contribution,
carried by the end-to-end anti-leakage discipline and the 15-row null evidence.
Selected 2026-08-05 by owner. The Section order reflects this: power-floor is
introduced in the abstract + intro and developed in §5.

## Files

- `main.tex` — the manuscript. Standard `\documentclass{article}` (arXiv-universal);
  only universally-available packages (amsmath, booktabs, hyperref, natbib). No custom
  `.cls` so it compiles anywhere.
- `references.bib` — academic references. Entries marked `% verified` were WebSearch-
  verified on 2026-08-05; the rest are standard, well-known methods references whose
  exact bibliographic details (page numbers, edition) should be confirmed at submission.

## Build

The Aionis repo has **no LaTeX toolchain** (no `pdflatex`/`latexmk`). Compile in one of:

```bash
# Option A — local TeX Live (if installed):
latexmk -pdf main.tex            # produces main.pdf
# Option B — Overleaf: upload this folder as a new project, set main.tex as the main file.
```

To target an Elsevier venue later (JFEc / JEF), swap `\documentclass{article}` →
`elsarticle` (download `elsarticle.cls` from CTAN or the Overleaf Elsevier template);
the content is class-agnostic.

## Content provenance and cross-checks

- Numbers are cross-checked against `runs/ledger.jsonl` row #49 (`confirmatory:first`,
  combined IC −0.0088, p_hac=0.484, J-T look-1 NOT_EQUIVALENT) and the Chinese v1.0 /
  English v1.0-en drafts in `docs/`.
- The §5 power-floor table (`n_min` 869/580/435) comes from `scripts/track_c_power_analysis.py`.
- The §5 σ(IC) range `[0.092, 0.163]` across 20 series comes from `scripts/ic_noise_floor_survey.py`
  (artifact `runs/ic_noise_floor_survey.json`, gitignored).
- The 15-row evidence table mirrors `docs/methods-and-results-draft.md` §4.

## Known prep-to-submission gaps (honest)

1. **Uncompiled** here (no local TeX) — first compile may surface minor LaTeX issues;
   fix-forward. Standard packages only, so risk is low.
2. **References**: 6 cited, 5 extra standard refs included. Confirm exact bibliographic
   details (page numbers, editions) before submission.
3. **Figures**: none yet. The GitHub Pages static site (`scripts/build_static_site.py`)
   already has Plotly charts that could be exported as PDFs for the manuscript if desired.
4. **Author/affiliation**: placeholder "Rethymus"; owner fills.
5. **Venue**: not chosen (see `reports/design/2026-08-05-publishable-unit-positioning.md`).
   The format is arXiv-compatible regardless; venue-specific tailoring (length, emphasis)
   follows the owner's venue decision.

## Boundary

This folder is docs/manuscript prep. It does not touch `runs/ledger.jsonl`, frozen
configurations, preregistrations, ADRs, or E3. No upload has occurred.
