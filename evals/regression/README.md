# evals/regression/ — Hermetic Regression Suite

The regression suite **lives at `../../tests/`**. This directory is a pointer,
not a duplicate.

## How to run

```bash
uv run pytest -q
```

## Characteristics

- **Hermetic** — no network, no real API keys, labeled/synthetic fixtures only.
- **AAA pattern** — Arrange / Act / Assert (see `../../tests/` for examples).
- **Descriptive names** — each test name states the behavior under test.
- **Deterministic** — same seeds, `n_jobs=1`; H6 determinism is asserted here.

## How to add a test

Mirror an existing test in `../../tests/`:

1. Find the closest existing test module by topic
   (`test_determinism.py`, `test_metrics.py`, `test_phase_*_controls.py`, ...).
2. Copy its structure: imports → labeled fixture → act → assert.
3. Keep it hermetic (no network, no real keys, synthetic/labeled data only).
4. Run `uv run pytest -q <new_test>.py -q` to confirm it passes.

## See also

- `../../tests/` — the actual suite
- `../README.md` — eval system map
