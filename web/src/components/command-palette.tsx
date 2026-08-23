"use client";

import { useEffect, useState } from "react";
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
} from "lucide-react";
import {
  CommandDialog,
  CommandEmpty,
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

type PaletteItem = {
  labelKey: DictKey;
  icon: React.ReactNode;
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
  { labelKey: "nav.group.confirm", icon: <ShieldCheckIcon className="size-4" />, href: "/confirmation" },
  { labelKey: "nav.institutions", icon: <LandmarkIcon className="size-4" />, href: "/institutions" },
  { labelKey: "nav.filers", icon: <ListIcon className="size-4" />, href: "/filers" },
  { labelKey: "nav.group.track", icon: <GaugeCircleIcon className="size-4" />, href: "/track" },
  { labelKey: "nav.group.discipline", icon: <ShieldCheckIcon className="size-4" />, href: "/discipline" },
  { labelKey: "nav.datahealth", icon: <ActivityIcon className="size-4" />, href: "/data-health" },
  { labelKey: "nav.group.themes", icon: <FileTextIcon className="size-4" />, href: "/themes" },
  { labelKey: "nav.market", icon: <GlobeIcon className="size-4" />, href: "/market" },
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
type StockNavItem = { ticker: string; name: string; short: boolean };
const STOCKS: StockNavItem[] = [
  ...aionis.picks.slice(0, 10).map((p) => ({ ticker: p.ticker, name: p.name, short: false })),
  ...aionis.shorts.slice(0, 3).map((s) => ({ ticker: s.ticker, name: s.name, short: true })),
];

export function CommandPalette() {
  const { t, lang, setLang } = useI18n();
  const { resolvedTheme, setTheme } = useTheme();
  const router = useRouter();
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen((o) => !o);
      }
    };
    document.addEventListener("keydown", down);
    return () => document.removeEventListener("keydown", down);
  }, []);

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

  const renderItems = (items: PaletteItem[]) =>
    items.map((item) => (
      <CommandItem key={`${item.labelKey}-${item.href ?? item.action ?? ""}`} onSelect={() => runItem(item)}>
        {item.icon}
        {t(item.labelKey)}
      </CommandItem>
    ));

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

      <CommandDialog open={open} onOpenChange={setOpen}>
        <CommandInput placeholder={t("command.placeholder")} />
        <CommandList>
          <CommandEmpty>{t("command.empty")}</CommandEmpty>
          <CommandGroup heading={t("command.group.start")}>
            {renderItems(TOUR)}
          </CommandGroup>
          <CommandSeparator />
          <CommandGroup heading={t("command.group.pages")}>
            {renderItems(PAGES)}
          </CommandGroup>
          <CommandSeparator />
          <CommandGroup heading={t("palette.stocks")}>
            {STOCKS.map((s) => (
              <CommandItem
                key={`${s.short ? "short" : "long"}-${s.ticker}`}
                value={s.name ? `${s.name} (${s.ticker})` : s.ticker}
                keywords={[s.ticker, s.name]}
                onSelect={() =>
                  runItem({ labelKey: "palette.stocks", icon: null, href: `/stock/${s.ticker}` })
                }
              >
                {s.short ? (
                  <TrendingDownIcon className="size-4 text-down" />
                ) : (
                  <TrendingUpIcon className="size-4 text-up" />
                )}
                <span className="flex-1">{s.name ? `${s.name} (${s.ticker})` : s.ticker}</span>
                {s.short && (
                  <Badge variant="outline" className="badge-down ml-auto shrink-0 px-1.5 py-0 text-[11px] font-normal">
                    {t("palette.stocks.short")}
                  </Badge>
                )}
              </CommandItem>
            ))}
          </CommandGroup>
          <CommandSeparator />
          <CommandGroup heading={t("command.group.views")}>
            {renderItems(VIEWS)}
          </CommandGroup>
          <CommandSeparator />
          <CommandGroup heading={t("command.group.settings")}>
            <CommandItem onSelect={() => runItem({ labelKey: "command.theme", icon: null, action: "theme" })}>
              <SunMoonIcon className="size-4" />
              {t("command.theme")}
            </CommandItem>
            <CommandItem onSelect={() => runItem({ labelKey: "command.lang", icon: null, action: "lang" })}>
              <LanguagesIcon className="size-4" />
              {t("command.lang")}
            </CommandItem>
            <CommandItem
              onSelect={() =>
                runItem({
                  labelKey: "command.results",
                  icon: null,
                  external: "https://github.com/Rethymus/Aionis/blob/main/docs/RESULTS.md",
                })
              }
            >
              <FileTextIcon className="size-4" />
              {t("command.results")}
            </CommandItem>
          </CommandGroup>
        </CommandList>
      </CommandDialog>
    </>
  );
}
