import type { MetadataRoute } from "next";
import { stockUniverse } from "@/data/aionis/stock-universe";
import { form13f } from "@/data/aionis/form13f";

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
// No lastModified: the honest build-time choice. Panel as_of dates differ per
// route and a single global timestamp would be fiction; omitted beats wrong.
const BASE = "https://rethymus.github.io/Aionis";

// Nightly-refreshed data views (data_health daily category + the aggregating
// home/dashboard). changeFrequency reflects the evening lane, not each item's
// source cadence (some sources lag honestly — the pages still rebuild daily).
const DAILY_ROUTES = [
  "dashboard",
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
  const entries: MetadataRoute.Sitemap = [
    { url: `${BASE}/`, changeFrequency: "daily", priority: 1 },
  ];
  for (const r of DAILY_ROUTES) {
    entries.push({ url: `${BASE}/${r}.html`, changeFrequency: "daily", priority: 0.8 });
  }
  for (const r of WEEKLY_ROUTES) {
    entries.push({ url: `${BASE}/${r}.html`, changeFrequency: "weekly", priority: 0.6 });
  }
  // Per-stock drill-downs over the frozen OOS universe (display-only mirror
  // of the route's generateStaticParams — one sitemap entry per exported page).
  for (const s of stockUniverse.stocks) {
    entries.push({
      url: `${BASE}/stock/${s.ticker}.html`,
      changeFrequency: "weekly",
      priority: 0.5,
    });
  }
  // Per-manager 13F drill-downs: quarterly filing cadence upstream.
  for (const m of form13f.managers) {
    entries.push({
      url: `${BASE}/manager/${m.cik}.html`,
      changeFrequency: "monthly",
      priority: 0.4,
    });
  }
  return entries;
}
