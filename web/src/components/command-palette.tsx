"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useTheme } from "next-themes";
import {
  SearchIcon,
  GlobeIcon,
  FlaskConicalIcon,
  GaugeCircleIcon,
  ShieldCheckIcon,
  LayoutDashboardIcon,
  ArrowRightIcon,
  SunMoonIcon,
  LanguagesIcon,
  FileTextIcon,
  TrendingUpIcon,
  TrendingDownIcon,
  LayoutGridIcon,
  LandmarkIcon,
  ListIcon,
  ActivityIcon,
  TerminalIcon,
  BuildingIcon,
  CalendarDaysIcon,
  FileClockIcon,
  NewspaperIcon,
  NetworkIcon,
  PercentIcon,
  BookOpenIcon,
  MapIcon,
} from "lucide-react";
import {
  CommandDialog,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from "@/components/ui/command";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useI18n } from "@/i18n/provider";
import type { DictKey } from "@/i18n/dict";
import { aionis } from "@/data/aionis";

// Command palette (cmdk — the same wheel GitHub/Vercel/Linear roll on; already
// a dependency via shadcn ui/command). The terminal has 20+ routes and deep
// in-page tabs; this is the keyboard-first way to reach any of them, plus the
// first-visit orientation the visual audit asked for: a numbered 60-second
// reading order through the argument chain (overview → context → evidence →
// validity → guard).
//
// The previous command-palette.tsx was unwired template cruft (wallet/crypto/
// login menus reading template seed data) — deleted together with seed.ts.
//
// Stock search (owner-reported 2026-08-29): the hero box promises "公司名 /
// 股票代码" but only 13 hot picks were searchable. The full frozen universe
// (1,421 US+CN rows, every one with a live /stock page) loads LAZILY via
// dynamic import on first open — a dedicated chunk, so the shared home bundle
// stays lean (the stock-universe module comment's barrel lesson). Filtering is
// done HERE with shouldFilter={false}: cmdk renders every mounted item, so
// handing it 1,421 rows would paint the whole universe on open; we render
// ranked top-N matches instead, and CJK company names (海光信息) match by
// plain substring, which cmdk's command-score handles poorly.

type PaletteItem = {
  labelKey: DictKey;
  // Optional: settings/action rows render their icon by action kind, and the
  // theme/lang/results entries are declared without one.
  icon?: React.ReactNode;
  href?: string; // internal route (may include #tab hash)
  external?: string; // external URL
  action?: "theme" | "lang";
};

const TOUR: PaletteItem[] = [
  { labelKey: "command.tour1", icon: <LayoutDashboardIcon className="size-4" />, href: "/" },
  { labelKey: "command.tour2", icon: <GlobeIcon className="size-4" />, href: "/regime" },
  { labelKey: "command.tour3", icon: <FlaskConicalIcon className="size-4" />, href: "/picks" },
  { labelKey: "command.tour4", icon: <GaugeCircleIcon className="size-4" />, href: "/track" },
  { labelKey: "command.tour5", icon: <ShieldCheckIcon className="size-4" />, href: "/discipline" },
];

const PAGES: PaletteItem[] = [
  { labelKey: "nav.group.regime", icon: <GlobeIcon className="size-4" />, href: "/regime" },
  { labelKey: "nav.group.picks", icon: <FlaskConicalIcon className="size-4" />, href: "/picks" },
  { labelKey: "nav.heatmap", icon: <LayoutGridIcon className="size-4" />, href: "/heatmap" },
  { labelKey: "nav.companies", icon: <BuildingIcon className="size-4" />, href: "/companies" },
  { labelKey: "nav.shelf", icon: <BookOpenIcon className="size-4" />, href: "/shelf" },
  { labelKey: "nav.group.confirm", icon: <ShieldCheckIcon className="size-4" />, href: "/confirmation" },
  { labelKey: "nav.institutions", icon: <LandmarkIcon className="size-4" />, href: "/institutions" },
  { labelKey: "nav.forcecamp", icon: <NetworkIcon className="size-4" />, href: "/force-camp" },
  { labelKey: "nav.filers", icon: <ListIcon className="size-4" />, href: "/filers" },
  { labelKey: "nav.quarterly", icon: <CalendarDaysIcon className="size-4" />, href: "/quarterly" },
  { labelKey: "nav.annual", icon: <FileClockIcon className="size-4" />, href: "/annual" },
  { labelKey: "nav.group.track", icon: <GaugeCircleIcon className="size-4" />, href: "/track" },
  { labelKey: "nav.atlas", icon: <MapIcon className="size-4" />, href: "/atlas" },
  { labelKey: "nav.group.discipline", icon: <ShieldCheckIcon className="size-4" />, href: "/discipline" },
  { labelKey: "nav.datahealth", icon: <ActivityIcon className="size-4" />, href: "/data-health" },
  { labelKey: "nav.group.themes", icon: <FileTextIcon className="size-4" />, href: "/themes" },
  { labelKey: "nav.market", icon: <GlobeIcon className="size-4" />, href: "/market" },
  { labelKey: "nav.newsfeed", icon: <NewspaperIcon className="size-4" />, href: "/news" },
  { labelKey: "nav.stakes", icon: <PercentIcon className="size-4" />, href: "/stakes" },
  { labelKey: "nav.positioning", icon: <GlobeIcon className="size-4" />, href: "/positioning" },
  { labelKey: "nav.taco", icon: <GlobeIcon className="size-4" />, href: "/taco" },
  { labelKey: "nav.sectors", icon: <GlobeIcon className="size-4" />, href: "/sectors" },
  { labelKey: "nav.conviction", icon: <GlobeIcon className="size-4" />, href: "/conviction" },
  { labelKey: "nav.smartmoney", icon: <GlobeIcon className="size-4" />, href: "/smart-money" },
  { labelKey: "nav.insiders", icon: <GlobeIcon className="size-4" />, href: "/insiders" },
  { labelKey: "nav.reddit", icon: <GlobeIcon className="size-4" />, href: "/reddit" },
  { labelKey: "nav.calibration", icon: <GaugeCircleIcon className="size-4" />, href: "/calibration" },
  { labelKey: "nav.modelhealth", icon: <GaugeCircleIcon className="size-4" />, href: "/model-health" },
  { labelKey: "nav.powerfloor", icon: <GaugeCircleIcon className="size-4" />, href: "/power-floor" },
  { labelKey: "nav.evidence", icon: <ShieldCheckIcon className="size-4" />, href: "/evidence" },
  { labelKey: "nav.apidocs", icon: <TerminalIcon className="size-4" />, href: "/api-docs" },
];

const VIEWS: PaletteItem[] = [
  { labelKey: "nav.factors", icon: <ArrowRightIcon className="size-4" />, href: "/picks#factors" },
  { labelKey: "nav.sectors", icon: <ArrowRightIcon className="size-4" />, href: "/picks#sectors" },
  { labelKey: "nav.conviction", icon: <ArrowRightIcon className="size-4" />, href: "/picks#conviction" },
  { labelKey: "nav.macro", icon: <ArrowRightIcon className="size-4" />, href: "/regime#macro" },
  { labelKey: "nav.taco", icon: <ArrowRightIcon className="size-4" />, href: "/regime#taco" },
  { labelKey: "nav.positioning", icon: <ArrowRightIcon className="size-4" />, href: "/regime#positioning" },
  { labelKey: "nav.insiders", icon: <ArrowRightIcon className="size-4" />, href: "/confirmation#insiders" },
  { labelKey: "nav.reddit", icon: <ArrowRightIcon className="size-4" />, href: "/confirmation#reddit" },
  { labelKey: "nav.evidence", icon: <ArrowRightIcon className="size-4" />, href: "/track#evidence" },
  { labelKey: "nav.modelhealth", icon: <ArrowRightIcon className="size-4" />, href: "/track#model-health" },
];

// Hot stocks straight from the picks panel: top-10 longs + top-3 shorts, one
// keystroke from /stock/<ticker>. Display-only navigation over the same frozen
// picks data the picks page renders — no new data path.
type StockNavItem = { ticker: string; name: string; short: boolean; region?: string };
const HOT_STOCKS: StockNavItem[] = [
  ...aionis.picks.slice(0, 10).map((p) => ({ ticker: p.ticker, name: p.name, short: false })),
  ...aionis.shorts.slice(0, 3).map((s) => ({ ticker: s.ticker, name: s.name, short: true })),
];

const STOCK_MATCH_CAP = 12;

type UniverseStock = { ticker: string; name: string; region: "us" | "cn" };

/** Ranked ticker/company-name match over the frozen universe.
 *  Tiers: exact ticker > ticker prefix > name prefix > name substring >
 *  ticker infix. Deterministic ordering inside a tier (ticker asc). */
function searchStocks(universe: UniverseStock[], rawQuery: string): StockNavItem[] {
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

export function CommandPalette() {
  const { t, lang, setLang } = useI18n();
  const { resolvedTheme, setTheme } = useTheme();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  // Lazy-loaded frozen universe (1,421 rows) — null until first open.
  const [universe, setUniverse] = useState<UniverseStock[] | null>(null);

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen((o) => !o);
      }
    };
    // Hero search box (and any fake-input trigger) opens the same palette.
    const openEvt = () => setOpen(true);
    document.addEventListener("keydown", down);
    window.addEventListener("aionis:open-palette", openEvt);
    return () => {
      document.removeEventListener("keydown", down);
      window.removeEventListener("aionis:open-palette", openEvt);
    };
  }, []);

  // Pull the universe chunk once, on first open (off the home-bundle path).
  useEffect(() => {
    if (!open || universe) return;
    let alive = true;
    import("@/data/aionis/stock-universe")
      .then((m) => {
        if (!alive) return;
        setUniverse(
          m.stockUniverse.stocks.map((s) => ({
            ticker: s.ticker,
            name: s.name || "",
            region: s.region,
          })),
        );
      })
      .catch(() => {
        // Chunk load failure must not brick the palette: page search keeps
        // working, stock search degrades to the hot list.
        if (alive) setUniverse([]);
      });
    return () => {
      alive = false;
    };
  }, [open, universe]);

  const runItem = (item: PaletteItem) => {
    setOpen(false);
    if (item.action === "theme") {
      setTheme(resolvedTheme === "dark" ? "light" : "dark");
    } else if (item.action === "lang") {
      setLang(lang === "zh" ? "en" : "zh");
    } else if (item.external) {
      window.open(item.external, "_blank", "noopener,noreferrer");
    } else if (item.href) {
      router.push(item.href);
    }
  };

  const openStock = (ticker: string) => {
    setOpen(false);
    router.push(`/stock/${ticker}`);
  };

  const renderItems = (items: PaletteItem[]) =>
    items.map((item) => (
      <CommandItem
        key={`${item.labelKey}-${item.href ?? item.action ?? ""}`}
        onSelect={() => runItem(item)}
      >
        {item.icon}
        {t(item.labelKey)}
      </CommandItem>
    ));

  // With shouldFilter={false} we own matching: translated label OR the route
  // slug (typing "picks" finds 选股决策 even in the zh UI).
  const q = query.trim().toLowerCase();
  const matchItem = (item: PaletteItem) =>
    !q ||
    t(item.labelKey).toLowerCase().includes(q) ||
    (item.href ?? "").toLowerCase().includes(q);

  const tour = TOUR.filter(matchItem);
  const pages = PAGES.filter(matchItem);
  const views = VIEWS.filter(matchItem);
  const stockMatches = useMemo(
    () => (q && universe ? searchStocks(universe, query) : []),
    [q, query, universe],
  );
  // Empty query → the curated hot list (today's behavior); non-empty → ranked
  // universe matches.
  const stockRows: StockNavItem[] = q ? stockMatches : HOT_STOCKS;
  const settings = (
    [
      { labelKey: "command.theme" as const, action: "theme" as const },
      { labelKey: "command.lang" as const, action: "lang" as const },
      {
        labelKey: "command.results" as const,
        external: "https://github.com/Rethymus/Aionis/blob/main/docs/RESULTS.md",
      },
    ] satisfies PaletteItem[]
  ).filter(matchItem);
  const nothingFound =
    q.length > 0 &&
    tour.length === 0 &&
    pages.length === 0 &&
    views.length === 0 &&
    settings.length === 0 &&
    stockRows.length === 0;

  return (
    <>
      <Button
        variant="ghost"
        size="sm"
        className="h-8 gap-1.5 rounded-full px-2.5 text-xs text-muted-foreground"
        onClick={() => setOpen(true)}
        aria-label={t("command.open")}
        title={t("command.open")}
      >
        <SearchIcon className="size-3.5" />
        <span className="hidden sm:inline">{t("command.open")}</span>
        <kbd className="pointer-events-none hidden items-center gap-0.5 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium sm:inline-flex">
          ⌘K
        </kbd>
      </Button>

      <CommandDialog open={open} onOpenChange={setOpen} shouldFilter={false}>
        <CommandInput
          value={query}
          onValueChange={(v) => setQuery(v)}
          placeholder={t("command.placeholder")}
        />
        <CommandList>
          {nothingFound ? (
            <div className="py-6 text-center text-sm text-muted-foreground">
              {t("command.empty")}
            </div>
          ) : (
            <>
              {tour.length > 0 ? (
                <>
                  <CommandGroup heading={t("command.group.start")}>{renderItems(tour)}</CommandGroup>
                  <CommandSeparator />
                </>
              ) : null}
              {pages.length > 0 ? (
                <>
                  <CommandGroup heading={t("command.group.pages")}>{renderItems(pages)}</CommandGroup>
                  <CommandSeparator />
                </>
              ) : null}
              {stockRows.length > 0 ? (
                <>
                  <CommandGroup
                    heading={
                      q
                        ? t("palette.stocks.search").replace(
                            "{n}",
                            universe ? String(universe.length) : "—",
                          )
                        : t("palette.stocks")
                    }
                  >
                    {stockRows.map((s) => (
                      <CommandItem
                        key={`${q ? "search" : "hot"}-${s.ticker}`}
                        onSelect={() => openStock(s.ticker)}
                      >
                        {s.short ? (
                          <TrendingDownIcon className="size-4 text-down" />
                        ) : (
                          <TrendingUpIcon className="size-4 text-up" />
                        )}
                        <span className="flex-1 truncate">
                          {s.name ? `${s.name} (${s.ticker})` : s.ticker}
                        </span>
                        {s.short && !q ? (
                          <Badge
                            variant="outline"
                            className="badge-down ml-auto shrink-0 px-1.5 py-0 text-[11px] font-normal"
                          >
                            {t("palette.stocks.short")}
                          </Badge>
                        ) : null}
                        {s.region ? (
                          <Badge
                            variant="outline"
                            className="ml-auto shrink-0 px-1.5 py-0 text-[11px] font-normal text-muted-foreground"
                          >
                            {s.region.toUpperCase()}
                          </Badge>
                        ) : null}
                      </CommandItem>
                    ))}
                  </CommandGroup>
                  <CommandSeparator />
                </>
              ) : null}
              {views.length > 0 ? (
                <>
                  <CommandGroup heading={t("command.group.views")}>{renderItems(views)}</CommandGroup>
                  <CommandSeparator />
                </>
              ) : null}
              {settings.length > 0 ? (
                <CommandGroup heading={t("command.group.settings")}>
                  {settings.map((item) => (
                    <CommandItem key={item.labelKey} onSelect={() => runItem(item)}>
                      {item.action === "theme" ? (
                        <SunMoonIcon className="size-4" />
                      ) : item.action === "lang" ? (
                        <LanguagesIcon className="size-4" />
                      ) : (
                        <FileTextIcon className="size-4" />
                      )}
                      {t(item.labelKey)}
                    </CommandItem>
                  ))}
                </CommandGroup>
              ) : null}
            </>
          )}
        </CommandList>
      </CommandDialog>
    </>
  );
}
