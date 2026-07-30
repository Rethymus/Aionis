# ADR-006 — Durable registry, not disposable one-shot artifacts

- **date:** 2026-07-27
- **status:** accepted

## Background
There is a temptation to treat each confirmatory run as a one-shot "spent witness" — run once, lock,
never re-run.

## Candidates considered
1. **One-shot runs** — no re-runs; each run is a spent witness.
2. **Durable registry** — `config_committed` sha256 recorded BEFORE the result; same-sig reruns are
   expected and bit-identical; a changed config is a new ledger row.

## Chosen
**(2) durable registry.**

## Evidence
- Anti-leakage requires the frozen config to be **witnessed before the result is observed**
  (`config_committed` → `runs/ledger.jsonl` before any OOS metric).
- Reproducibility (H6 determinism) **requires** deterministic same-config re-runs (the IC series AND
  raw scores are bit-identical). Same-sig reruns are therefore **evidence of correctness**, not waste.
- The anchor is the **sha256**, not ceremony. A headline can never be "rerun-to-significance" rescued
  (a changed config is a new row). See `../docs/05-acceptance.md`, `../CLAUDE.md`.

## Cost / applicability
- **Cost:** discipline overhead — the config must be committed before results are observed.
- **Applicability:** all confirmatory + exploratory runs.

## Re-evaluation trigger
None expected (foundational). Re-open only if the registry is shown to permit a silent overwrite of
a frozen config.
