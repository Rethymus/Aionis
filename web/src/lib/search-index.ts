import type { DictKey } from "@/i18n/dict";
import { aionis } from "@/data/aionis";

// Shared search index for BOTH search surfaces (top-nav command palette and
// the home hero inline search). One list, one scoring function — the two
// boxes can never drift apart on what is searchable. Pages/views are keyed by
// i18n DictKey so labels stay bilingual; icons stay with the consumers.

export type SearchPageItem = { labelKey: DictKey; href: string };

export const SEARCH_PAGES: SearchPageItem[] = [
  { labelKey: "nav.group.regime", href: "/regime" },
  { labelKey: "nav.group.picks", href: "/picks" },
  { labelKey: "nav.heatmap", href: "/heatmap" },
  { labelKey: "nav.companies", href: "/companies" },
  { labelKey: "nav.shelf", href: "/shelf" },
  { labelKey: "nav.group.confirm", href: "/confirmation" },
  { labelKey: "nav.institutions", href: "/institutions" },
  { labelKey: "nav.forcecamp", href: "/force-camp" },
  { labelKey: "nav.filers", href: "/filers" },
  { labelKey: "nav.quarterly", href: "/quarterly" },
  { labelKey: "nav.annual", href: "/annual" },
  { labelKey: "nav.group.track", href: "/track" },
  { labelKey: "nav.atlas", href: "/atlas" },
  { labelKey: "nav.group.discipline", href: "/discipline" },
  { labelKey: "nav.datahealth", href: "/data-health" },
  { labelKey: "nav.group.themes", href: "/themes" },
  { labelKey: "nav.market", href: "/market" },
  { labelKey: "nav.newsfeed", href: "/news" },
  { labelKey: "nav.stakes", href: "/stakes" },
  { labelKey: "nav.positioning", href: "/positioning" },
  { labelKey: "nav.taco", href: "/taco" },
  { labelKey: "nav.sectors", href: "/sectors" },
  { labelKey: "nav.conviction", href: "/conviction" },
  { labelKey: "nav.smartmoney", href: "/smart-money" },
  { labelKey: "nav.insiders", href: "/insiders" },
  { labelKey: "nav.reddit", href: "/reddit" },
  { labelKey: "nav.calibration", href: "/calibration" },
  { labelKey: "nav.modelhealth", href: "/model-health" },
  { labelKey: "nav.powerfloor", href: "/power-floor" },
  { labelKey: "nav.evidence", href: "/evidence" },
  { labelKey: "nav.apidocs", href: "/api-docs" },
];

export const SEARCH_VIEWS: SearchPageItem[] = [
  { labelKey: "nav.factors", href: "/picks#factors" },
  { labelKey: "nav.sectors", href: "/picks#sectors" },
  { labelKey: "nav.conviction", href: "/picks#conviction" },
  { labelKey: "nav.macro", href: "/regime#macro" },
  { labelKey: "nav.taco", href: "/regime#taco" },
  { labelKey: "nav.positioning", href: "/regime#positioning" },
  { labelKey: "nav.insiders", href: "/confirmation#insiders" },
  { labelKey: "nav.reddit", href: "/confirmation#reddit" },
  { labelKey: "nav.evidence", href: "/track#evidence" },
  { labelKey: "nav.modelhealth", href: "/track#model-health" },
];

// Hot stocks straight from the picks panel: top-10 longs + top-3 shorts, one
// keystroke from /stock/<ticker>. Display-only navigation over the same frozen
// picks data the picks page renders — no new data path.
export type StockNavItem = {
  ticker: string;
  name: string;
  short: boolean;
  region?: string;
};

export const HOT_STOCKS: StockNavItem[] = [
  ...aionis.picks.slice(0, 10).map((p) => ({ ticker: p.ticker, name: p.name, short: false })),
  ...aionis.shorts.slice(0, 3).map((s) => ({ ticker: s.ticker, name: s.name, short: true })),
];

export type UniverseStock = { ticker: string; name: string; region: "us" | "cn" };

export const STOCK_MATCH_CAP = 12;

/** Ranked ticker/company-name match over the frozen universe.
 *  Tiers: exact ticker > ticker prefix > name prefix > name substring >
 *  ticker infix. Deterministic ordering inside a tier (ticker asc). CJK
 *  company names (海光信息) match by plain substring. */
export function searchStocks(
  universe: UniverseStock[],
  rawQuery: string,
): StockNavItem[] {
  const q = rawQuery.trim().toUpperCase();
  if (!q) return [];
  const hits: { tier: number; item: StockNavItem }[] = [];
  for (const s of universe) {
    const ticker = s.ticker.toUpperCase();
    const name = (s.name || "").toUpperCase();
    let tier: number | null = null;
    if (ticker === q) tier = 0;
    else if (ticker.startsWith(q)) tier = 1;
    else if (name.startsWith(q)) tier = 2;
    else if (name.includes(q)) tier = 3;
    else if (ticker.includes(q)) tier = 4;
    if (tier !== null) {
      hits.push({ tier, item: { ticker: s.ticker, name: s.name || "", short: false, region: s.region } });
    }
  }
  return hits
    .sort((a, b) => a.tier - b.tier || a.item.ticker.localeCompare(b.item.ticker))
    .slice(0, STOCK_MATCH_CAP)
    .map((h) => h.item);
}

/** Page/view label-or-slug match (typing "picks" finds 选股决策 even in the
 *  zh UI). Empty query matches nothing — callers show curated lists instead. */
export function matchSearchPage(
  item: SearchPageItem,
  q: string,
  label: string,
): boolean {
  const needle = q.trim().toLowerCase();
  if (!needle) return false;
  return (
    label.toLowerCase().includes(needle) ||
    item.href.toLowerCase().includes(needle)
  );
}
