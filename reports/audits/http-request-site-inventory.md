# HTTP request-site inventory

Scope: factual source inspection for AUD-05A on 2026-07-31. The shared primitive exists, but no
adapter is integrated in this slice. Therefore none of the sites below is claimed compliant with
the project-wide >=2.0-second host-spacing contract.

## Facts: research data request sites

| Boundary / request site | Host | Type | Current delay / retry behavior | Disposition |
|---|---|---|---|---|
| `ingest/market.py:fetch_tiingo` | `api.tiingo.com` | Market data, direct `requests` | 1.0s after each symbol; linear 4/8/... retry sleep | AUD-05B: integrate shared policy |
| `ingest/market.py:fetch_alpaca` | `data.alpaca.markets` | Market data, direct `requests` | 1.0s after each symbol; linear 4/8/... retry sleep | AUD-05B: integrate shared policy |
| `ingest/fundamentals.py:_load_cik_map` | `www.sec.gov` | SEC ticker map, direct `requests` | No request spacing or local retry | AUD-05B: integrate shared policy |
| `ingest/fundamentals.py:_fetch_company_facts` | `data.sec.gov` | SEC company facts, direct `requests` | 0.15s after success; linear 4/8/12... retry sleep | AUD-05B: integrate shared policy |
| `ingest/stakes_13d.py:_get_json` | `data.sec.gov` | SEC submissions and blocks, direct `requests` | 0.15s after success; linear 4/8/... retry sleep | AUD-05B: integrate shared policy; E3 reuses this fetch path |
| `ingest/stakes_13d_efts.py:_get_json` | `efts.sec.gov` | SEC EFTS search, direct `requests` | 0.15s after success; linear 4/8/... retry sleep | AUD-05B: integrate shared policy |
| `ingest/cik_resolver.py:_fetch_with_backoff` | `www.sec.gov` | SEC ticker map, direct `requests` | No success spacing; exponential 2/4/8... retry sleep | AUD-05B: integrate shared policy |
| `ingest/cik_resolver.py:fetch_company_name_history` | `data.sec.gov` | SEC submissions, direct `requests` | 0.15s after success; no local retry | AUD-05B: integrate shared policy |
| `ingest/events.py:fetch_fred_release_dates` | `api.stlouisfed.org` | FRED release calendar, direct `requests` | No request spacing or local retry | AUD-05B: integrate shared policy |
| `features/macro_surprise.py:fetch_alfred_vintages` | `api.stlouisfed.org` | ALFRED vintage observations, direct `requests` | No spacing between pages or local retry | AUD-05B: feature-adapter integration; E3 macro collector reuses this path |
| `ingest/events.py:fetch_fomc_dates` | `www.federalreserve.gov` | Fed calendar HTML, direct `requests` | No request spacing or local retry | AUD-05B: integrate shared policy |
| `ingest/event_text.py:_fetch_text` (FOMC) | `www.federalreserve.gov` | Fed statement HTML, direct `requests` | 0.5s between event attempts; at most two connection attempts | AUD-05B: integrate shared policy |
| `ingest/event_text.py:_fetch_text` (CPI/NFP) | `www.bls.gov` | BLS release HTML, direct `requests` | 0.5s between event attempts; at most two connection attempts | AUD-05C: blocked-source disposition; do not build a transport while BLS is blocked |
| `ingest/universe.py:load_historical_membership` (hanshof) | `raw.githubusercontent.com` | GitHub-hosted membership CSV, direct `requests` | Cache miss makes one request; no spacing or local retry | AUD-05B: integrate shared policy |
| `ingest/universe.py:load_historical_membership` (pierrebrunelle) | `github.com` | GitHub membership tarball, direct `requests` | Cache miss makes one request; no spacing or local retry | AUD-05B: integrate shared policy |

## Facts: uncovered transport boundaries

| Boundary | Host / transport | Current behavior | Disposition |
|---|---|---|---|
| `ingest/vix.py:fetch_vix` | FRED through `pandas_datareader.get_data_fred` | SDK-owned HTTP; no shared host policy | AUD-05C: decide wrapper, disablement, or a separately approved task |
| `ingest/vix.py:_download_vix_vintages` | FRED through `pandas_datareader.get_data_fred` | SDK-owned HTTP; no shared host policy | AUD-05C: decide wrapper, disablement, or a separately approved task |
| `features/selection_panel.py:fred_series` | FRED through `pandas_datareader.get_data_fred` | SDK-owned HTTP; no shared host policy | AUD-05C: decide wrapper, disablement, or a separately approved task |
| `features/selection_panel.py:fama_french_daily` | Kenneth French Data Library through `pandas_datareader.get_data_famafrench` | SDK-owned HTTP; no shared host policy | AUD-05C: decide wrapper, disablement, or a separately approved task |
| `ingest/reddit_sentiment.py:fetch_reddit_posts` | Reddit through PRAW | SDK-owned HTTP; 1.5s only between subreddit pulls | AUD-05C: decide wrapper, disablement, or a separately approved task |
| `features/event_vector.py:GLMEmbedder` | Configured model endpoint through OpenAI SDK | SDK retry configured; no shared data-fetch policy | AUD-05C: explicit model-boundary disposition; outside AUD-05A data-adapter integration |
| `features/causal_broadcast.py:GLMCausalEdgeClient` and `extraction/llm_client.py` | GLM / SiliconFlow / ModelScope through OpenAI SDK | Model-specific retry/cooldown behavior | AUD-05C: explicit model-boundary disposition; preserve provider policy ownership |
| `scripts/health_check.py` | FRED, Fed, SEC, GitHub, Tiingo, Alpaca and probes | Global 2.0s gap before probes; retry loops have separate 1/2/4 sleeps | AUD-05C: explicit health-check disposition; script is outside AUD-05B adapter allowlist |

## Inferences

- Cache hits in the inspected data adapters return before their direct HTTP call, so integration can
  place policy acquisition immediately around actual cache-miss requests without sleeping on hits.
- Host-scoped coordination must be shared across modules: `www.sec.gov`, `data.sec.gov`,
  `api.stlouisfed.org`, and `www.federalreserve.gov` each have more than one logical caller.
- E3 does not need a separate limiter where its forward collectors reuse the listed SEC and ALFRED
  functions; compliance depends on those underlying functions being integrated in AUD-05B.

## AUD-05C Disposition Table (2026-07-31)

| Boundary | Current transport state | Disposition | C-task | Owner/dependency | Stop-condition |
|---|---|---|---|---|---|
| **BLS CPI/NFP** (`ingest/event_text.py:_fetch_text`) | Direct `requests.get()` to `www.bls.gov` (0.5s spacing, 2 attempts) | **BLOCKED + disable** (cache miss → fail-closed) | C1 | Owner GO after 05C complete | BLS blocked per CLAUDE.md data-source constraints |
| **VIX `fetch_vix`** (`ingest/vix.py`) | `pandas_datareader.get_data_fred("VIXCLS")` (SDK-owned HTTP, no shared policy) | **C2: approved FRED SDK wrapper** (preserve ADR-003 VIX PIT/no-revision/cache/ledger) | C2 | Owner GO + AUD-05B APPROVE | Preserve VIX risk-premium semantics |
| **VIX `_download_vix_vintages`** (`ingest/vix.py`) | `pandas_datareader.get_data_fred("VIXCLS")` (SDK-owned HTTP, no shared policy) | **C2: approved FRED SDK wrapper** (same as fetch_vix) | C2 | Owner GO + AUD-05B APPROVE | Preserve self-dated vintage synthesis |
| **selection-panel FRED** (`features/selection_panel.py:fred_series`) | `pandas_datareader.get_data_fred(series_id)` (SDK-owned HTTP) | **OWNER-DECISION: data-intake gate** (cache miss BLOCKED or disable until approved) | None | Owner data-intake review | Clear 7-gate rubric first |
| **selection-panel Fama-French** (`features/selection_panel.py:fama_french_daily`) | `pandas_datareader.get_data_famafrench()` (SDK-owned HTTP, Kenneth French Data Library) | **OWNER-DECISION: data-intake gate** (cache miss BLOCKED or disable until approved) | None | Owner data-intake review | Clear 7-gate rubric first |
| **PRAW Reddit** (`ingest/reddit_sentiment.py`) | PRAW SDK (1.5s between subreddits, SDK-owned HTTP) | **C3: owner-held** (7-gate clearance required before wrapper) | C3 | Owner 7-gate approval | G1-G7 must pass first |
| **`scripts/health_check.py`** | Direct `requests.get()` to FRED/Fed/SEC/GitHub/Tiingo/Alpaca (global 2.0s gap) | **C4: owner-held** (remove blocked probes first, then decide shared-policy hookup) | C4 | Owner probe inventory + hookup decision | Remove akshare/EastMoney; keep approved sources |
| **GLMEmbedder** (`features/event_vector.py`) | OpenAI SDK → GLM embedding-3 (max_retries=3, disk cache by text hash) | **C5: owner decision** (≥2s rule scope: model APIs exempt vs. all HTTP calls) | C5 | Owner politeness rule clarification | Clarify if model APIs are SDK-exempt |
| **GLMCausalEdgeClient** (`features/causal_broadcast.py`) | OpenAI SDK → GLM-4-Flash (max_retries=0, sha256 cache) | **C5: owner decision** (same as GLMEmbedder) | C5 | Owner politeness rule clarification | Preserve provider set (GLM/SiliconFlow/ModelScope) |
| **OpenAICompatClient + ProviderRouter** (`extraction/llm_client.py`) | OpenAI SDK → GLM/SiliconFlow/ModelScope (router-level cooldown on 429) | **C5: owner decision** (same as GLMEmbedder) | C5 | Owner politeness rule clarification | Preserve provider set (GLM/SiliconFlow/ModelScope) |

## Hypotheses requiring AUD-05B/05C verification

- A module-level shared policy can cover all approved direct-`requests` sites without changing cache
  semantics or response parsing. **VERIFIED: AUD-05B APPROVED**
- SDK-owned transports may require transport injection rather than a call-site wrapper; AUD-05C must
  verify this before choosing integration, disablement, or a separately scoped task. **VERIFIED: C2 (VIX) requires wrapper**
