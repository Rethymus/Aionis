/**
 * Aionis real-time price proxy — Cloudflare Worker.
 *
 * Three endpoints:
 *   GET /api/prices/us?tickers=COIN,SO,AAPL   → Tiingo IEX (15-min delayed on free tier)
 *   GET /api/prices/cn?tickers=sh.688041,...   → 东方财富 push2 (real-time, if reachable from edge)
 *   GET /api/health                             → connectivity check for both upstreams
 *
 * Anti-leakage boundary: this Worker serves DISPLAY-ONLY price data. It must
 * never be consumed by the research pipeline (features/eval/ingest). See
 * CLAUDE.md "prices = DISPLAY ONLY" guardrail.
 *
 * Caching: two layers — Cloudflare edge cache (caches.default API) + browser
 * Cache-Control header. Market-hours TTL is short (30s CN, 5min US); off-hours
 * TTL is long (24h) to conserve upstream API quota.
 *
 * Security: TIINGO_API_KEY lives in Cloudflare env (set via
 * `wrangler secret put`). It NEVER appears in client code or responses.
 * CORS is open (* — the terminal is public, no sensitive data is proxied).
 */

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
};

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    if (request.method === "OPTIONS") {
      return new Response(null, { headers: CORS });
    }
    const path = url.pathname;
    if (path === "/api/prices/us") return usPrices(url, env, ctx);
    if (path === "/api/prices/cn") return cnPrices(url, env, ctx);
    if (path === "/api/health") return health(env, ctx);
    return json({ error: "not found", endpoints: ["/api/prices/us", "/api/prices/cn", "/api/health"] }, 404);
  },

  // Pre-warm US mega-cap cache 5 min before market open.
  async scheduled(_event, env, ctx) {
    ctx.waitUntil(prewarm(env));
  },
};

// ─── US prices via Tiingo IEX ──────────────────────────────────

async function usPrices(url, env, ctx) {
  const tickers = url.searchParams.get("tickers") || "";
  if (!tickers) return json({ error: "missing tickers param" }, 400);

  const cache = caches.default;
  const cacheKey = new Request(`https://cache.local/us/${tickers}`, { method: "GET" });
  const hit = await cache.match(cacheKey);
  if (hit) return hit;

  if (!env.TIINGO_API_KEY) return json({ error: "TIINGO_API_KEY not configured" }, 500);

  try {
    const resp = await fetch(`https://api.tiingo.com/iex/${tickers}`, {
      headers: { Authorization: `Token ${env.TIINGO_API_KEY}` },
    });
    if (!resp.ok) return json({ error: `tiingo:${resp.status}` }, 502);
    const data = await resp.json();
    const out = {};
    for (const item of data) {
      out[item.ticker] = {
        price: item.last ?? item.tngoLast ?? null,
        change_pct: item.chp ?? null,
        as_of: new Date().toISOString(),
      };
    }
    const ttl = 300; // 5 min edge cache
    return cached(json(out), cacheKey, cache, ctx, ttl);
  } catch (e) {
    return json({ error: String(e) }, 502);
  }
}

// ─── A-share prices via 东方财富 push2 ─────────────────────────

async function cnPrices(url, env, ctx) {
  const tickers = url.searchParams.get("tickers") || ""; // sh.688041,sz.300223
  if (!tickers) return json({ error: "missing tickers param" }, 400);

  const cache = caches.default;
  const cacheKey = new Request(`https://cache.local/cn/${tickers}`, { method: "GET" });
  const hit = await cache.match(cacheKey);
  if (hit) return hit;

  // Convert baostock format (sh.688041) → East Money secid (1.688041).
  // Market codes: sh=1 (Shanghai), sz=0 (Shenzhen), bj=0 (Beijing).
  const secids = tickers
    .split(",")
    .map((t) => {
      const [prefix, code] = t.split(".");
      const market = prefix === "sh" ? 1 : 0;
      return `${market}.${code}`;
    })
    .join(",");

  try {
    const resp = await fetch(
      `https://push2.eastmoney.com/api/qt/ulist.np/get?fields=f2,f3,f12,f14&secids=${secids}`,
      { headers: { Referer: "https://quote.eastmoney.com" } },
    );
    if (!resp.ok) return json({ error: `eastmoney:${resp.status}` }, 502);
    const raw = await resp.json();
    const out = {};
    for (const item of raw?.data?.diff ?? []) {
      // f2 = current price (元, not 分 — ulist.np returns actual price), f3 = change %,
      // f12 = code, f14 = Chinese name
      const code = String(item.f12);
      const prefix = code.startsWith("6") ? "sh" : code.startsWith("4") || code.startsWith("8") ? "bj" : "sz";
      out[`${prefix}.${code}`] = {
        price: item.f2 ?? null,
        change_pct: item.f3 ?? null,
        name: item.f14 ?? "",
        as_of: new Date().toISOString(),
      };
    }
    const ttl = isCnMarketOpen() ? 30 : 86400;
    return cached(json(out), cacheKey, cache, ctx, ttl);
  } catch (e) {
    return json({ error: String(e) }, 502);
  }
}

// ─── Health check ──────────────────────────────────────────────

async function health(env, ctx) {
  const out = { status: "ok", tiingo: "unknown", cn: "unknown", timestamp: new Date().toISOString() };
  try {
    const r = await fetch("https://api.tiingo.com/iex/AAPL", {
      headers: { Authorization: `Token ${env.TIINGO_API_KEY}` },
    });
    out.tiingo = r.ok ? "ok" : `error:${r.status}`;
  } catch {
    out.tiingo = "unreachable";
  }
  try {
    const r = await fetch(
      "https://push2.eastmoney.com/api/qt/ulist.np/get?fields=f2,f12&secids=1.600000",
      { headers: { Referer: "https://quote.eastmoney.com" } },
    );
    out.cn = r.ok ? "ok" : `error:${r.status}`;
  } catch {
    out.cn = "unreachable";
  }
  return json(out);
}

// ─── Helpers ───────────────────────────────────────────────────

function isCnMarketOpen() {
  const now = new Date();
  const day = now.getDay();
  if (day === 0 || day === 6) return false;
  const h = now.getUTCHours();
  // A-share: 9:30-11:30, 13:00-15:00 CST = 01:30-03:30, 05:00-07:00 UTC
  return (h >= 1 && h < 4) || (h >= 5 && h < 7);
}

function json(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", ...CORS },
  });
}

function cached(response, cacheKey, cache, ctx, ttl) {
  const out = new Response(response.body, response);
  out.headers.set("Cache-Control", `public, s-maxage=${ttl}, stale-while-revalidate=${ttl * 2}`);
  ctx.waitUntil(cache.put(cacheKey, out.clone()));
  return out;
}

async function prewarm(env) {
  // Warm US mega-cap cache before market open so the first visitor sees prices instantly.
  const fakeUrl = new URL("https://x/api/prices/us?tickers=AAPL,MSFT,NVDA,GOOGL,AMZN,META,TSLA");
  const fakeCtx = { waitUntil: () => {} };
  await usPrices(fakeUrl, env, fakeCtx);
}
