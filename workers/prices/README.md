# Aionis Prices Worker

Cloudflare Worker — real-time price proxy for the Aionis fintech terminal.

Serves **display-only** price data (US via Tiingo IEX, A-share via 东方财富 push2)
with edge caching. The API key (`TIINGO_API_KEY`) lives in Cloudflare env and
never appears in client code.

## Anti-leakage boundary

This Worker serves **display-only** data. It must NEVER be consumed by the
research pipeline (`features/`, `eval/`, `ingest/`). Prices are real-time market
observations, not PIT research signals. See CLAUDE.md guardrail.

## Deploy

```bash
cd workers/prices
npx wrangler login                        # browser auth with your Cloudflare account
npx wrangler secret put TIINGO_API_KEY    # paste your Tiingo API key
npx wrangler deploy
```

After deploy, note the Worker URL:
`https://aionis-prices.<your-subdomain>.workers.dev`

Then edit `web/src/lib/live-prices.ts` and set `WORKER_URL` to that URL.

## Verify

```bash
# Health check (tests both Tiingo + 东方财富 connectivity from the edge)
curl https://aionis-prices.<your-subdomain>.workers.dev/api/health

# US prices
curl 'https://aionis-prices.<your-subdomain>.workers.dev/api/prices/us?tickers=COIN,SO'

# A-share prices (the breakthrough test — if 东方财富 is reachable from the edge)
curl 'https://aionis-prices.<your-subdomain>.workers.dev/api/prices/cn?tickers=sh.688041,sz.300223'
```

If `health` returns `"cn": "ok"`, A-share real-time prices are unlocked — the
key breakthrough (东方财富 was unreachable from GitHub Actions' US datacenter).

## Endpoints

| Endpoint | Upstream | Cache TTL |
|---|---|---|
| `/api/prices/us?tickers=COIN,SO` | Tiingo IEX (15-min delayed, free) | 5 min |
| `/api/prices/cn?tickers=sh.688041` | 东方财富 push2 (real-time) | 30s (market) / 24h (off) |
| `/api/health` | Both (connectivity probe) | none |

## Free tier limits

Cloudflare Workers: **100k requests/day** (free). With 5-min US cache + 30s CN
cache, even continuous 24h traffic stays well under 1k upstream calls/day.
Tiingo free: 1,000 req/day (we use ~25 per page load, cached).
