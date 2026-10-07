# Security & Responsible Use

## Reporting a vulnerability

Please use **GitHub's private vulnerability reporting** on this repository
(Report a vulnerability → Security tab). Do not open a public issue for
anything security-sensitive. Reports are read by the maintainer; you will
get an acknowledgement within 14 days.

## Scope

- The research pipeline (`src/aionis/`, `scripts/`) and its data fetchers.
- The deployed research terminal (`web/`) and the display-only price worker
  (`workers/prices/`) — note the worker proxies prices for **display only**;
  it must never be promoted into any research/OOS path (that is a leakage
  boundary, not a security boundary, but reports about boundary violations
  are equally welcome).
- CI workflows (`.github/workflows/`) and the locally-run nightly refresh
  lane (`scripts/ops_local_refresh.py`).

## Secrets & data policy

- `.env`, `data/`, and `*.parquet` are **never committed** (`.gitignore`
  enforced; committing them past the ignore is a Forbidden act per
  `CLAUDE.md`/`AGENTS.md`). If you find committed secrets or data in any
  copy of this repository, report immediately — history will be treated as
  compromised, keys rotated, and the incident disclosed.
- API keys (FRED/Tiingo/Alpaca/Reddit) and LLM provider keys live only in
  the local `.env`. Prefer expiring fine-grained PATs for push credentials
  with `contents:write` only.
- No secrets are required to run the hermetic test suite
  (`uv run pytest -q`) or to read the public data API of the terminal.

## License abuse (repackaged resale)

The code is **PolyForm-Noncommercial-1.0.0** (noncommercial use only;
see [`LICENSE`](LICENSE) and
[`decisions/ADR-013-polyform-noncommercial-license.md`](decisions/ADR-013-polyform-noncommercial-license.md)).
If you find this project — or a derivative of it — being **sold or packaged
as a commercial product** (e.g., a paid "AI stock picker" built on this
codebase), that is an unlicensed commercial use: please report it via the
same private channel with links and evidence. This matters doubly here,
because the project's own results are **null** — anyone selling predictions
from it is selling something the evidence does not support.

## This project will never

- Ask you for trading capital, offer returns, or run a live trading bot.
- Publish investment advice. The terminal is a research-validity exhibit.
