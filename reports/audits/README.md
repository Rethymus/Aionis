# reports/audits/ — Security / Leakage / Dependency Audits

**Placeholder.** No audits are fabricated here yet; this directory reserves
space for future audit reports (security, leakage, dependency-license).

The **standing intake audit** is already enforced via the 7-gate rubric applied
to every third-party dataset:

- `../docs/data-license-allowlist.md` — permissive licenses only (MIT/Apache/BSD)
- `../docs/data-intake-rubric.md` — the 7 gates:
  license / PIT / no-revision / snapshot / exploratory-only / selection-honesty
  / politeness

Planned audit report types (when written, one file per audit, dated):

- **Leakage audit** — verify the anti-leakage identity (PIT data, PurgedGroupKFold
  + embargo, `config_committed`-before-result, bundle-shuffle placebo) for a phase.
- **Dependency-license audit** — diff installed deps against the allowlist.
- **Security audit** — secrets, input validation, no `data/` or `*.parquet` staged.

## See also

- `../docs/data-license-allowlist.md`
- `../docs/data-intake-rubric.md`
