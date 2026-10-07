# Aionis task runner — one entrypoint, canonical order (audit round 221/222).

# Why `just`: 2026-consensus runner (single binary, Windows+Git-Bash first-class,
# no make staleness semantics — and "must ALWAYS run, in order" is exactly what
# file-staleness models get wrong for evidence pipelines).
# Install:  uv tool install just     (or: cargo install just / winget install Casey.Just)

default:
    @just --list

# Install everything (base + extraction + dashboard + dev extras)
install:
    uv sync --all-extras

# Hermetic tests + lint (the same gates CI runs)
check:
    uv run ruff check
    uv run pytest -q

# One-time data fetch for the frozen PIT universe (resumable, polite).
# Requires .env (see .env.example). NOT needed for the test suite.
fetch:
    uv run python scripts/phase_b_fetch.py

# A confirmatory run (Phase D example): config_committed BEFORE result, H6-verified.
run:
    uv run python scripts/phase_d_run.py

# Re-render the evidence cascade in the canonical order (panels -> atlas ->
# dossier -> shelf/matrix re-pin), then run the evidence contract gate.
# This is the ONLY supported way to refresh evidence interactively.
evidence *args:
    uv run python scripts/evidence_refresh.py --check {{args}}

# Guard what gets committed (data/ · *.parquet · .env · >5MB). Same checks as
# the pre-commit hook, runnable by hand.
guard:
    uv run python scripts/precommit_guard.py

# Re-verify the four-link proof chain of every frozen claim (the CLI twin
# of the /proof terminal page).
verify *args:
    uv run python scripts/verify_claim.py {{args}}

# Data-snapshot audit: verify no upstream source rewrote history since the
# committed baseline (CRSP-tape tripwire). --baseline re-anchors (owner note:
# only after intentional data-format changes).
snapshot *args:
    uv run python scripts/data_snapshot_audit.py {{args}}

# The nightly refresh lane (evening window guard applies — usually you want
# the automation, not this manual call). See docs/ops-local-refresh.md.
lane:
    uv run python scripts/ops_local_refresh.py

# Local quant dashboard (Streamlit).
dashboard:
    uv run streamlit run dashboard/app.py

# Local dev server for the web terminal.
web:
    cd web && pnpm install && pnpm dev
