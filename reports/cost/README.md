# reports/cost/ — Token / Compute / API-Cost Notes

**Placeholder.** No paid/third-party cost data is tracked here yet.

## What this tracks

Per the project's token-budgeting rules, notes on token, compute, and API-cost
for LLM extraction and pipeline runs.

## LLM provider surface (factual)

- The only LLM providers are **GLM / SiliconFlow / ModelScope** (all
  OpenAI-compatible), routed through a policy-aware multi-key router that
  auto-fails-over on rate-limits:
  `../../src/aionis/extraction/providers.py`.
- Per-call token usage is logged in the extraction layer:
  `../../src/aionis/extraction/` (`llm_client.py`, `extract.py`).

Per the project constraint, **GLM is a test-only provider**; do not treat GLM
token figures as production cost.

## See also

- `../../src/aionis/extraction/providers.py` — multi-key router
- `../../src/aionis/extraction/` — per-call token-usage logging
