import type { MetadataRoute } from "next";
import { stockUniverse } from "@/data/aionis/stock-universe";
import { form13f } from "@/data/aionis/form13f";
import { aionis } from "@/data/aionis";

// The barrel exports one aggregate object; alias the panel-health slice so
// the per-route lastModified lookups below stay readable.
const dataHealth = aionis.dataHealth;

// output: "export" requires route handlers to opt into static generation.
export const dynamic = "force-static";

// Public-site discoverability (display lane): one static sitemap for the whole
// static export. GitHub Pages serves this site from the /Aionis/ project
// subpath, so robots.txt at the domain root is not ours to control — the
// sitemap is built for manual submission (Search Console / Bing Webmaster)
// and for any future custom-domain move. URLs use the .html forms that are
// proven-served online (round 87/90 live verification), absolute under the
// canonical base.
//
// lastModified (round 180): REAL per-panel as_of dates from data_health.
const BASE = "https://rethymus.github.io/Aionis";

const ROUTE_PANEL: Record<string, string | null> = {
  market: "market_context", news: "news_feed", ipo: "ipo",
  insiders: "form4", congress: "politician_trades", events: "form8k",
  "smart-money": "smart_money", stakes: "stakes_13g", reddit: "reddit",
  themes: "themes", sectors: "sector_breakdown", companies: "companies_dir",
  executives: "def14a_persons", filers: "filers13f", institutions: "form13f",
  positioning: "cot", atlas: "atlas_claims", calibration: "calibration_reliability",
  discipline: "ledger_audit", evidence: "evidence", power_floor: "power_floor",
  shelf: "knowledge_shelf", taco: "taco", regime: "cot",
};
const _panelByKey = new Map(dataHealth.panels.map((p) => [p.key, p]));
const _snapshotDate = dataHealth.snapshot_ts?.slice(0, 10) ?? undefined;
function _lastMod(route: string): string | undefined {
  const pk = ROUTE_PANEL[route];
  if (pk) {
    const panel = _panelByKey.get(pk);
    const asOf = panel?.as_of;
    if (typeof asOf === "string" && asOf.length >= 10) return asOf.slice(0, 10);
  }
  return _snapshotDate;
}

// Nightly-refreshed data views (data_health daily category + the aggregating
// home/dashboard). changeFrequency reflects the evening lane, not each item's
// source cadence (some sources lag honestly — the pages still rebuild daily).
const DAILY_ROUTES = [
  // "dashboard" is NOT here — it is the priority-1 canonical home entry above
  // (round 144 dedup: option B made / and /dashboard the same content).
  "market",
  "news",
  "heatmap",
  "ipo",
  "insiders",
  "congress",
  "events",
  "smart-money",
  "stakes",
  "reddit",
  "themes",
  "sectors",
  "companies",
  "executives",
  "filers",
  "institutions",
  "positioning",
  "data-health",
] as const;

// Research narrative / frozen / methodology pages: rebuilt on code or panel
// contract changes, not nightly.
const WEEKLY_ROUTES = [
  "atlas",
  "calibration",
  "confirmation",
  "conviction",
  "discipline",
  "evidence",
  "force-camp",
  "model-health",
  "picks",
  "power-floor",
  "quarterly",
  "annual",
  "regime",
  "shelf",
  "taco",
  "track",
  "api-docs",
] as const;

export default function sitemap(): MetadataRoute.Sitemap {
  // Round 144: the root entry is folded into dashboard.html — since round
  // 116 (option B) `/` renders the same content with canonical pointing at
  // dashboard.html, and a sitemap should list canonical URLs only. The home
  // page keeps priority 1 on its canonical URL.
  const entries: MetadataRoute.Sitemap = [
    { url: `${BASE}/dashboard.html`, changeFrequency: "daily", priority: 1, lastModified: _snapshotDate },
  ];
  for (const r of DAILY_ROUTES) {
    entries.push({ url: `${BASE}/${r}.html`, changeFrequency: "daily", priority: 0.8, lastModified: _lastMod(r) });
  }
  for (const r of WEEKLY_ROUTES) {
    entries.push({ url: `${BASE}/${r}.html`, changeFrequency: "weekly", priority: 0.6, lastModified: _lastMod(r) });
  }
  // Per-stock drill-downs over the frozen OOS universe (display-only mirror
  // of the route's generateStaticParams — one sitemap entry per exported page).
  const stockAsOf = stockUniverse.as_of as Record<string, string>;
  for (const s of stockUniverse.stocks) {
    entries.push({
      url: `${BASE}/stock/${s.ticker}.html`,
      changeFrequency: "weekly",
      priority: 0.5,
      lastModified: stockAsOf[s.region],
    });
  }
  // Per-manager 13F drill-downs: quarterly filing cadence upstream.
  for (const m of form13f.managers) {
    entries.push({
      url: `${BASE}/manager/${m.cik}.html`,
      changeFrequency: "monthly",
      priority: 0.4,
      lastModified: _lastMod("institutions"),
    });
  }
  return entries;
}
