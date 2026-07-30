# ADR-002 — Exclude GKX; self-built ticker-keyed PIT universe

- **date:** 2026-07-27
- **status:** accepted

## Background
Phase B needed a fundamentals factor panel. The Guo–Kavalakis–Xiu (GKX) master dataset was the
candidate "A-GKX" path.

## Candidates considered
1. **A-GKX** — use the GKX master factor data (permno-keyed).
2. **A-自建 (self-built)** — ticker-keyed fundamentals from EDGAR + PIT S&P 500 membership.

## Chosen
**(2) self-built, ticker-keyed.** Path = A-自建.

## Evidence
- **Critic finding C1:** GKX is **permno-keyed** with **no free point-in-time permno↔CIK bridge**;
  a today-snapshot `cik_map` would be a **look-ahead leak**.
- Self-built sources (both **MIT committed-data**, no scrapers run): hanshof daily 1996–2025
  (primary) + pierrebrunelle monthly 2016–2026 (cross-check). `src/aionis/ingest/cik_resolver.py`
  resolves historical-ticker→CIK from SEC `company_tickers.json` (public domain); real Jaccard
  agreement min 0.8544 / mean 0.9272 over 106 months 2016+ (residual = ticker *renames*, not
  company disagreement; no ad-hoc rename map — that would be p-hacking). Clean OOS universe = **588**.

## Cost / applicability
- **Cost:** 588/705 = 83.4% of pierrebrunelle (114 unresolved renamed/merged). Both arms use the
  same set → the **differential is valid**; absolute coverage is documented.
- **Applicability:** Phase B+ fundamentals.

## Re-evaluation trigger
A free, PIT permno↔CIK bridge appears; OR the coverage gap is proven to bias the differential.
