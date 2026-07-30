# ADR-003 — VIXCLS is unrevised → PIT via no-revision (G3), not vintage tracking

- **date:** 2026-07-28
- **status:** accepted

## Background
VIX was added as the first "risk premium" main-line feature. The initial assumption was that
VIXCLS would be fetched via ALFRED real-time vintages, exactly like the revised CPI / NFP series.

## Candidates considered
1. **ALFRED real-time vintage tracking** (as for CPI / NFP).
2. **Self-dated vintages from the non-realtime series.**

## Chosen
**(2) self-dated vintages from the non-realtime VIXCLS series** (`src/aionis/ingest/vix.py`).

## Evidence
- **VIXCLS has NO ALFRED real-time vintages** — every observation has
  `realtime_start == realtime_end == today` (a historical realtime window fetch returns HTTP 400).
  The series is **unrevised.** Point-in-time correctness is therefore satisfied by the **no-revision
  contract (intake gate G3)**, NOT by vintage tracking.
- Vintage tracking remains correct for the *revised* CPI / NFP series; it is simply the wrong tool
  for an unrevised series. See `../docs/data-intake-rubric.md`.

## Cost / applicability
- **Cost:** none — this is a correctness fix (the vintage approach would have failed at fetch time).
- **Applicability:** all VIX / VIX-surprise features.

## Re-evaluation trigger
CBOE revises the historical VIXCLS methodology (it has not; the methodology is stable); OR a
distinct *revised* VIX series is introduced.
