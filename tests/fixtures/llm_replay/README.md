# SYNTHETIC LLM Replay Fixtures

This directory contains **synthetic test fixtures only**. These fixtures are:

- **NOT real API responses** — they are fabricated for testing
- **NOT real filing text** — they use dummy company "EXAMPLE CORP"
- **NOT real accessions/identifiers** — they use placeholder values
- **NO real API keys, tokens, or credentials** — all values are fake

## Purpose

These fixtures mimic the SHAPE of OpenAI-compatible chat-completion responses
with controlled malformations to test parser stability deterministically.

## Fixture Types

1. `valid_*.json` — Well-formed, valid ERL responses
2. `invalid_json_*.json` — Malformed JSON (syntax errors)
3. `truncated_*.json` — Incomplete JSON (missing closing braces)
4. `extra_text_*.json` — Valid JSON surrounded by extra text
5. `unknown_enum_*.json` — JSON with unknown enum values

## Naming Convention

All fixtures use descriptive prefixes (`valid_`, `invalid_json_`, etc.) and
placeholder content (e.g., "EXAMPLE CORP", "dummy-accession-123").
