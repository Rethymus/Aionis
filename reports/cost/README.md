# reports/cost/ — Token / Compute / API-Cost Notes

No paid/third-party cost registry is tracked here yet. Unknown costs must remain
unknown; token observations and token estimates are not currency costs.

## What this tracks

Per the project's token-budgeting rules, notes on token, compute, and API-cost
for LLM extraction and pipeline runs.

## Current recorded boundary

| item | value | status/source |
|---|---:|---|
| Phase A prompt tokens | 41,689 | observed in historical `runs/extract_scaled.log`; recorded by the 2026-07-31 audit |
| Phase A completion tokens | 8,636 | observed in the same log; recorded by the audit |
| Phase A extraction total | 50,325 | sum logged by extraction counters; not a paid-cost record |
| total Phase A research tokens | approximately 72K | historical estimate in `docs/frontier_positioning.md`; different scope from extraction total |
| paid API cost | **not tracked** | no invoice/currency registry |
| compute/storage/human review cost | **not tracked** | no durable cost registry |

The 50,325 logged extraction tokens and approximately 72K research-total estimate
must not be presented as interchangeable. No current evidence supports a monthly E3
cost, cost per effective event, or cost per successful extraction.

## LLM provider surface (factual)

- The only LLM providers are **GLM / SiliconFlow / ModelScope** (all
  OpenAI-compatible), routed through a policy-aware multi-key router that
  auto-fails-over on rate-limits:
  `../../src/aionis/extraction/providers.py`.
- Per-call token usage is logged in the extraction layer:
  `../../src/aionis/extraction/` (`llm_client.py`, `extract.py`).

The Phase A observation used GLM-4-flash. Do not treat its token figures as
production cost or as evidence that B/C/D/E1 used LLM features; those four
headline arms are zero-LLM.

## See also

- `../../src/aionis/extraction/providers.py` — multi-key router
- `../../src/aionis/extraction/` — per-call token-usage logging
- `../audits/2026-07-31-quant-llm-research-audit.md` — recorded audit boundary
- `../../docs/frontier_positioning.md` — historical approximately 72K estimate
