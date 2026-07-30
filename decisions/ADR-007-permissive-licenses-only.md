# ADR-007 — Permissive licenses only (MIT / Apache / BSD)

- **date:** 2026-07-26
- **status:** accepted

## Background
Dependency selection for a research project intended to remain OSS-able and free of
commercial/re-distribution entanglements.

## Candidates considered
1. Allow any license (pick best-in-class regardless).
2. **Permissive licenses only** (MIT / Apache / BSD).

## Chosen
**(2) permissive only.** See `../docs/data-license-allowlist.md`.

## Evidence
Non-permissive licenses create re-distribution / commercial-risk or viral-license problems:
- **Commons Clause** — vectorbt.
- **GPL** — backtrader.
- **paid / no-license** — mlfinlab.
- **AGPL** — pypbo.
- **LGPL** — nautilus_trader.

Permissive equivalents exist for every actual need: lightgbm (MIT), purgedcv (MIT), arch (NCSA ≈
BSD-3), pandas / numpy (BSD), scikit-learn (BSD-3), streamlit / plotly (Apache / MIT).

## Cost / applicability
- **Cost:** occasionally a best-in-class tool is excluded (e.g. vectorbt).
- **Applicability:** all dependencies and intake datasets (the 7-gate intake G1).

## Re-evaluation trigger
A permissively-licensed equivalent disappears AND a non-permissive tool is uniquely required to meet
a frozen spec.
