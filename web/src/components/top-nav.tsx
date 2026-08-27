"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { useI18n } from "@/i18n/provider";
import { ColorConvToggle } from "@/components/colorconv-toggle";
import { CommandPalette } from "@/components/command-palette";
import { LangToggle } from "@/components/lang-toggle";
import { ThemeToggle } from "@/components/theme-toggle";
import { Sheet, SheetContent, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import {
  ActivityIcon,
  BookOpenIcon,
  BuildingIcon,
  CalendarDaysIcon,
  ChevronDownIcon,
  FileClockIcon,
  FileTextIcon,
  FlaskConicalIcon,
  GaugeCircleIcon,
  LandmarkIcon,
  LayoutDashboardIcon,
  LayoutGridIcon,
  ListIcon,
  MenuIcon,
  NetworkIcon,
  NewspaperIcon,
  PercentIcon,
  RocketIcon,
  ShieldCheckIcon,
  TerminalIcon,
  UserRoundIcon,
  UsersIcon,
  ZapIcon,
} from "lucide-react";

// Top navbar shell (aligned-site structure 2026-08-24): sticky h-14 frosted
// header over the 1320px rail, grouped hover dropdowns (.navi/.drop from
// globals.css), compact 13px nav type, active item = bg-soft. Replaces the
// shadcn sidebar shell — the aligned site has no sidebar on any route.

type NavItem = {
  title: string;
  sub?: string;
  url: string;
  icon: React.ReactNode;
};
type NavGroup = { label: string; items: NavItem[] };

function icon(cls = "size-[15px]") {
  return cls;
}

export function TopNav() {
  const { t } = useI18n();
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);

  // Argument-chain IA preserved (Context → Evidence → Validity, Guard
  // spanning), regrouped for a top bar: direct links + grouped dropdowns.
  const direct: NavItem[] = [
    { title: t("nav.overview"), url: "/dashboard", icon: <LayoutDashboardIcon className={icon()} /> },
    { title: t("nav.newsfeed"), url: "/news", icon: <NewspaperIcon className={icon()} /> },
  ];
  const groups: NavGroup[] = [
    {
      label: t("nav.group.context"),
      items: [
        { title: t("nav.group.regime"), sub: t("nav.sub.regime"), url: "/regime", icon: <LayoutDashboardIcon className={icon()} /> },
      ],
    },
    {
      label: t("nav.group.model"),
      items: [
        { title: t("nav.group.picks"), url: "/picks", icon: <FlaskConicalIcon className={icon()} /> },
        { title: t("nav.heatmap"), url: "/heatmap", icon: <LayoutGridIcon className={icon()} /> },
        { title: t("nav.group.confirm"), url: "/confirmation", icon: <UsersIcon className={icon()} /> },
      ],
    },
    {
      label: t("nav.group.institution"),
      items: [
        { title: t("nav.institutions"), sub: t("nav.sub.institutions"), url: "/institutions", icon: <LandmarkIcon className={icon()} /> },
        { title: t("nav.filers"), sub: t("nav.sub.filers"), url: "/filers", icon: <ListIcon className={icon()} /> },
        { title: t("nav.quarterly"), sub: t("nav.sub.quarterly"), url: "/quarterly", icon: <CalendarDaysIcon className={icon()} /> },
        { title: t("nav.annual"), sub: t("nav.sub.annual"), url: "/annual", icon: <FileClockIcon className={icon()} /> },
        { title: t("nav.executives"), sub: t("nav.sub.executives"), url: "/executives", icon: <UserRoundIcon className={icon()} /> },
        { title: t("nav.forcecamp"), sub: t("nav.sub.forcecamp"), url: "/force-camp", icon: <NetworkIcon className={icon()} /> },
      ],
    },
    {
      label: t("nav.group.stream"),
      items: [
        { title: t("nav.events"), sub: t("nav.sub.events"), url: "/events", icon: <ZapIcon className={icon()} /> },
        { title: t("nav.stakes"), sub: t("nav.sub.stakes"), url: "/stakes", icon: <PercentIcon className={icon()} /> },
        { title: t("nav.ipo"), sub: t("nav.sub.ipo"), url: "/ipo", icon: <RocketIcon className={icon()} /> },
        { title: t("nav.congress"), sub: t("nav.sub.congress"), url: "/congress", icon: <LandmarkIcon className={icon()} /> },
      ],
    },
    {
      label: t("nav.group.verify"),
      items: [
        { title: t("nav.group.track"), url: "/track", icon: <GaugeCircleIcon className={icon()} /> },
        { title: t("nav.group.discipline"), url: "/discipline", icon: <ShieldCheckIcon className={icon()} /> },
        { title: t("nav.datahealth"), url: "/data-health", icon: <ActivityIcon className={icon()} /> },
      ],
    },
    {
      label: t("nav.group.reference"),
      items: [
        { title: t("nav.companies"), sub: t("nav.sub.companies"), url: "/companies", icon: <BuildingIcon className={icon()} /> },
        { title: t("nav.shelf"), sub: t("nav.sub.shelf"), url: "/shelf", icon: <BookOpenIcon className={icon()} /> },
        { title: t("nav.apidocs"), sub: t("nav.sub.apidocs"), url: "/api-docs", icon: <TerminalIcon className={icon()} /> },
      ],
    },
  ];

  const isActive = (url: string) =>
    url === "/dashboard" ? pathname === "/dashboard" : pathname.startsWith(url);

  const itemNode = (item: NavItem, onClick?: () => void) => (
    <Link
      key={item.url}
      href={item.url}
      onClick={onClick}
      className={`flex items-center gap-3 rounded-md px-2.5 py-2 transition-colors hover:bg-soft ${
        isActive(item.url) ? "bg-soft" : ""
      }`}
    >
      <span className="flex h-7 w-7 flex-none items-center justify-center rounded-md border border-line bg-soft text-sub">
        {item.icon}
      </span>
      <span className="min-w-0 flex flex-col">
        <span className="block truncate text-[13px] font-medium text-ink">{item.title}</span>
        {item.sub ? (
          <span className="block truncate text-[11px] font-normal text-mute">{item.sub}</span>
        ) : null}
      </span>
    </Link>
  );

  return (
    <header className="sticky top-0 z-20 border-b border-line bg-card/80 backdrop-blur-md">
      <div className="mx-auto flex h-14 max-w-[1320px] items-center gap-2 px-5 md:px-6">
        <Link href="/dashboard" className="flex flex-none items-center gap-2.5">
          <span className="flex size-[26px] flex-none items-center justify-center rounded-md bg-brand text-[13px] font-bold text-black">
            A
          </span>
          <span className="text-[14px] font-semibold tracking-[-0.015em]">{t("brand.name")}</span>
        </Link>
        <span
          aria-hidden="true"
          className="mx-2 hidden h-4 w-px flex-none rotate-[18deg] bg-line md:block"
        />
        <nav className="hidden items-center gap-px md:flex">
          {direct.map((item) => (
            <Link
              key={item.url}
              href={item.url}
              className={`flex items-center gap-[3px] rounded-md px-2.5 py-1.5 text-[13px] font-medium whitespace-nowrap transition-colors ${
                isActive(item.url) ? "text-ink" : "text-sub hover:text-ink"
              }`}
            >
              {item.title}
            </Link>
          ))}
          {groups.map((g) => (
            <div key={g.label} className="navi group">
              <div className="flex cursor-pointer items-center gap-[3px] rounded-md py-1.5 pr-2 pl-2.5 text-[13px] font-medium whitespace-nowrap transition-colors text-sub hover:text-ink">
                {g.label}
                <span
                  aria-hidden="true"
                  className="pointer-events-none transition-transform duration-150 group-hover:rotate-180"
                >
                  <ChevronDownIcon className="size-3.5" />
                </span>
              </div>
              <div className="drop">
                {g.items.map((item) => itemNode(item))}
              </div>
            </div>
          ))}
        </nav>
        <div className="ml-auto hidden items-center gap-1 md:flex">
          <CommandPalette />
          <ColorConvToggle />
          <LangToggle />
          <ThemeToggle />
        </div>
        <a
          href="https://github.com/Rethymus/Aionis/blob/main/docs/RESULTS.md"
          target="_blank"
          rel="noopener noreferrer"
          className="ml-auto hidden items-center gap-[3px] rounded-md px-2.5 py-1.5 text-[13px] font-medium whitespace-nowrap transition-colors text-sub hover:text-ink lg:flex"
        >
          {t("nav.method")}
          <FileTextIcon className="size-3" />
        </a>
        <Sheet open={menuOpen} onOpenChange={setMenuOpen}>
          <SheetTrigger
            className="ml-auto flex h-8 w-8 flex-none items-center justify-center rounded-md text-sub hover:bg-soft hover:text-ink md:hidden"
            aria-label={t("nav.menu.open")}
          >
            <MenuIcon className="size-5" />
          </SheetTrigger>
          <SheetContent side="left" className="w-[280px] overflow-y-auto p-4">
            <SheetTitle className="text-[14px] font-semibold">{t("brand.name")}</SheetTitle>
            <nav className="mt-3 flex flex-col gap-4">
              {groups.map((g) => (
                <div key={g.label} className="flex flex-col gap-0.5">
                  <p className="px-2.5 pb-1 text-[11px] font-medium text-mute">{g.label}</p>
                  {g.items.map((item) => itemNode(item, () => setMenuOpen(false)))}
                </div>
              ))}
              <div className="flex flex-col gap-0.5">
                <p className="px-2.5 pb-1 text-[11px] font-medium text-mute">{t("nav.group.overview")}</p>
                {direct.map((item) => itemNode(item, () => setMenuOpen(false)))}
              </div>
              <div className="mt-2 flex items-center gap-2 border-t border-line2 pt-4">
                <ColorConvToggle />
                <LangToggle />
                <ThemeToggle />
              </div>
            </nav>
          </SheetContent>
        </Sheet>
      </div>
    </header>
  );
}
