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
      const last = item.last ?? item.tngoLast ?? null;
      const open = item.open ?? null;
      // Tiingo free tier doesn't include `chp` (change %); calculate from
      // last vs open (intraday change). If open unavailable, leave null.
      const calcChange = last != null && open != null && open > 0
        ? ((last - open) / open) * 100
        : item.chp ?? null;
      out[item.ticker] = {
        price: last,
        change_pct: calcChange,
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
  const tickersParam = url.searchParams.get("tickers") || ""; // sh.688041,sz.300223
  if (!tickersParam) return json({ error: "missing tickers param" }, 400);

  const cache = caches.default;
  const cacheKey = new Request(`https://cache.local/cn/v2/${tickersParam}`, { method: "GET" });
  const hit = await cache.match(cacheKey);
  if (hit) return hit;

  // Sina real-time quote API: hq.sinajs.cn/list=sh688041,sz300223
  // Returns GBK-encoded text: var hq_str_sh688041="海光信息,open,prevClose,price,...";
  // Fields: 0=name, 1=open, 2=prevClose, 3=currentPrice, 4=high, 5=low
  const sinaTickers = tickersParam.split(",").map((t) => t.replace(".", "")).join(","); // sh.688041 → sh688041

  try {
    const resp = await fetch(`https://hq.sinajs.cn/list=${sinaTickers}`, {
      headers: { Referer: "https://finance.sina.com.cn" },
    });
    if (!resp.ok) return json({ error: `sina:${resp.status}` }, 502);

    // Sina returns GBK — decode to UTF-8 for the name field.
    const buffer = await resp.arrayBuffer();
    const text = new TextDecoder("gbk").decode(buffer);

    const out = {};
    for (const line of text.trim().split("\n")) {
      const m = line.match(/var hq_str_(\w+)="(.*)";/);
      if (!m) continue;
      const rawTicker = m[1]; // sh688041
      const fields = m[2].split(",");
      if (fields.length < 4 || !fields[3]) continue;
      const name = fields[0];
      const prevClose = parseFloat(fields[2]);
      const current = parseFloat(fields[3]);
      const changePct = prevClose > 0 ? ((current - prevClose) / prevClose) * 100 : null;
      // Convert back: sh688041 → sh.688041
      const prefix = rawTicker.match(/^(sh|sz|bj)/)?.[1] ?? "sz";
      const code = rawTicker.replace(/^(sh|sz|bj)/, "");
      out[`${prefix}.${code}`] = {
        price: current,
        change_pct: changePct !== null ? Math.round(changePct * 100) / 100 : null,
        name,
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
    const r = await fetch("https://hq.sinajs.cn/list=sh600000", {
      headers: { Referer: "https://finance.sina.com.cn" },
    });
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
