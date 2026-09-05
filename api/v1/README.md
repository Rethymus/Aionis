# Aionis Terminal Data API (v1)

Static JSON contract served straight from GitHub Pages — read-only, no auth, no server. Panel files are the payload verbatim; this catalog is the meta layer.

## Endpoints
- catalog:      /Aionis/api/v1/catalog.json
- health:       /Aionis/api/v1/panels/data_health.json
- openapi:      /Aionis/api/v1/openapi.json
- panel (n=58): /Aionis/api/v1/panels/<key>.json
- live prices:  https://api.aionis-prices.workers.dev/api/prices/{us|cn}?tickers=...

Frozen endpoints deliberately do NOT advance (anti-leakage contract);
see the catalog's freshness field before expecting updates.
