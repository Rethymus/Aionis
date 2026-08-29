# archive/ — Superseded Docs / Decisions / Specs

Superseded documentation, decisions, and specs go here — they are **never
silently deleted**.

**Current contents (2026-08-30):**

- `streamlit-demo-v2/` (2026-08-30, owner-authorized): the demonstrative
  Streamlit dashboard v2 — `app_v2.py`, `demo_data.py` (the project's only
  synthetic-data generators, seed=0, DEMO-labeled), `charts_v2.py`,
  `README_v2.md`, and its test file. Its display role is fully covered by the
  web terminal (`web/src/app/(dashboard)/`, 55 real committed panels). The v1
  quant-eval dashboard (`dashboard/app.py`, real runs/ data) is NOT retired.
  Note: `pyproject.toml`'s `dashboard` extra is retained — it also carries
  `cot_reports` (used by `scripts/cot_fetch.py`) and the tearsheet libraries.
- The retired publication track — `manuscript/`
  (arXiv preprint scaffold), `quarto-site/` (paper site), `docs/methods-and-results-draft(-en).md`
  (paper drafts), `docs/replication-availability.md`, `2026-08-05-publishable-unit-positioning.md`
  (venue brief), `2026-08-05-power-floor-literature-anchoring.md`. Owner decision 2026-08-15:
  the project has no publication plans; these are kept for history only.

## Rule: move-don't-delete

When moving an item here:

1. Move, do not delete, the file.
2. Prepend a one-line header to the archived file:
   `Superseded by <path-or-ref> on <YYYY-MM-DD>.`
3. Keep the git history intact so the superseded item remains bisectable.
