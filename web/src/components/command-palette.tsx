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
import {
  HOT_STOCKS,
  SEARCH_PAGES,
  SEARCH_VIEWS,
  searchStocks,
  type StockNavItem,
  type UniverseStock,
} from "@/lib/search-index";

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

// Pages/views/hot-stocks/scoring live in lib/search-index — the single source
// shared with the home hero inline search, so the two boxes can never drift.
// This surface only attaches icons, by route.
const PAGE_ICONS: Record<string, React.ReactNode> = {
  "/regime": <GlobeIcon className="size-4" />,
  "/picks": <FlaskConicalIcon className="size-4" />,
  "/heatmap": <LayoutGridIcon className="size-4" />,
  "/companies": <BuildingIcon className="size-4" />,
  "/shelf": <BookOpenIcon className="size-4" />,
  "/confirmation": <ShieldCheckIcon className="size-4" />,
  "/institutions": <LandmarkIcon className="size-4" />,
  "/force-camp": <NetworkIcon className="size-4" />,
  "/filers": <ListIcon className="size-4" />,
  "/quarterly": <CalendarDaysIcon className="size-4" />,
  "/annual": <FileClockIcon className="size-4" />,
  "/track": <GaugeCircleIcon className="size-4" />,
  "/atlas": <MapIcon className="size-4" />,
  "/discipline": <ShieldCheckIcon className="size-4" />,
  "/data-health": <ActivityIcon className="size-4" />,
  "/themes": <FileTextIcon className="size-4" />,
  "/market": <GlobeIcon className="size-4" />,
  "/news": <NewspaperIcon className="size-4" />,
  "/stakes": <PercentIcon className="size-4" />,
  "/positioning": <GlobeIcon className="size-4" />,
  "/taco": <GlobeIcon className="size-4" />,
  "/sectors": <GlobeIcon className="size-4" />,
  "/conviction": <GlobeIcon className="size-4" />,
  "/smart-money": <GlobeIcon className="size-4" />,
  "/insiders": <GlobeIcon className="size-4" />,
  "/reddit": <GlobeIcon className="size-4" />,
  "/calibration": <GaugeCircleIcon className="size-4" />,
  "/model-health": <GaugeCircleIcon className="size-4" />,
  "/power-floor": <GaugeCircleIcon className="size-4" />,
  "/evidence": <ShieldCheckIcon className="size-4" />,
  "/api-docs": <TerminalIcon className="size-4" />,
};

const PAGES: PaletteItem[] = SEARCH_PAGES.map((p) => ({
  labelKey: p.labelKey,
  href: p.href,
  icon: PAGE_ICONS[p.href] ?? <FileTextIcon className="size-4" />,
}));

const VIEWS: PaletteItem[] = SEARCH_VIEWS.map((v) => ({
  labelKey: v.labelKey,
  href: v.href,
  icon: <ArrowRightIcon className="size-4" />,
}));

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
