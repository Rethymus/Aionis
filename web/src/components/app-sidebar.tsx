"use client";

import Link from "next/link";
import { NavMain } from "@/components/nav-main";
import {
  Sidebar,
  SidebarContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";
import { useI18n } from "@/i18n/provider";
import {
  LayoutDashboardIcon,
  GlobeIcon,
  FlaskConicalIcon,
  ShieldCheckIcon,
  GaugeCircleIcon,
  FileTextIcon,
  UsersIcon,
  LandmarkIcon,
  ActivityIcon,
  LayoutGridIcon,
  TerminalIcon,
  ZapIcon,
  RocketIcon,
  BuildingIcon,
  UserRoundIcon,
  ListIcon,
  CalendarDaysIcon,
  FileClockIcon,
  NewspaperIcon,
  BookOpenIcon,
} from "lucide-react";

export function AppSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
  const { t } = useI18n();

  // Validity-argument chain (paradigm α, ECD): the nav IS the chain —
  // Context → Evidence → Validity, with Guard spanning the whole chain.
  // No numbers, no "定调/定标/佐证/问责" role labels: the structure emerges
  // from the falsifiable-claim argument, not an analyst's workflow.
  const navHome = [
    { title: t("nav.overview"), sub: t("nav.sub.overview"), url: "/dashboard", icon: <LayoutDashboardIcon /> },
  ];
  const navContext = [
    { title: t("nav.group.regime"), sub: t("nav.sub.regime"), url: "/regime", icon: <GlobeIcon /> },
    // GDELT headline stream — market CONTEXT (the news the regime sits in),
    // not evidence: link-out metadata only, display lane.
    { title: t("nav.newsfeed"), sub: t("nav.sub.news"), url: "/news", icon: <NewspaperIcon /> },
  ];
  // Evidence segment: core evidence (model picks) + independent corroboration
  // (smart money / insiders / retail) — both feed the same claim, kept as two
  // routes (URLs unchanged) under one nav group.
  const navEvidence = [
    { title: t("nav.group.picks"), url: "/picks", icon: <FlaskConicalIcon /> },
    { title: t("nav.heatmap"), url: "/heatmap", icon: <LayoutGridIcon /> },
    { title: t("nav.group.confirm"), url: "/confirmation", icon: <UsersIcon /> },
    { title: t("nav.institutions"), sub: t("nav.sub.institutions"), url: "/institutions", icon: <LandmarkIcon /> },
    { title: t("nav.filers"), sub: t("nav.sub.filers"), url: "/filers", icon: <ListIcon /> },
    { title: t("nav.events"), sub: t("nav.sub.events"), url: "/events", icon: <ZapIcon /> },
    // Periodic-report deep cuts over the same filing-stream v2 panel (the
    // 10-K/10-Q families get their own routes because the 800-newest visible
    // cap squeezes them out of the unified stream in filing season).
    { title: t("nav.quarterly"), sub: t("nav.sub.quarterly"), url: "/quarterly", icon: <CalendarDaysIcon /> },
    { title: t("nav.annual"), sub: t("nav.sub.annual"), url: "/annual", icon: <FileClockIcon /> },
    { title: t("nav.executives"), sub: t("nav.sub.executives"), url: "/executives", icon: <UserRoundIcon /> },
    { title: t("nav.ipo"), sub: t("nav.sub.ipo"), url: "/ipo", icon: <RocketIcon /> },
    { title: t("nav.congress"), sub: t("nav.sub.congress"), url: "/congress", icon: <LandmarkIcon /> },
  ];
  const navValidity = [
    { title: t("nav.group.track"), url: "/track", icon: <GaugeCircleIcon /> },
  ];
  const navGuard = [
    { title: t("nav.group.discipline"), url: "/discipline", icon: <ShieldCheckIcon /> },
    { title: t("nav.datahealth"), url: "/data-health", icon: <ActivityIcon /> },
  ];
  const navReference = [
    { title: t("nav.companies"), sub: t("nav.sub.companies"), url: "/companies", icon: <BuildingIcon /> },
    // Method shelf — the repo's own method docs as a browsable library plus
    // curated outbound research bookmarks (reference lane, link-out only).
    { title: t("nav.shelf"), sub: t("nav.sub.shelf"), url: "/shelf", icon: <BookOpenIcon /> },
    { title: t("nav.apidocs"), sub: t("nav.sub.apidocs"), url: "/api-docs", icon: <TerminalIcon /> },
    {
      title: t("nav.method"),
      url: "https://github.com/Rethymus/Aionis/blob/main/docs/RESULTS.md",
      icon: <FileTextIcon />,
    },
  ];

  return (
    <Sidebar variant="inset" {...props}>
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" render={<Link href="/dashboard" />}>
              <div className="flex aspect-square size-8 items-center justify-center rounded-lg bg-sidebar-primary text-sidebar-primary-foreground font-bold">
                A
              </div>
              <div className="grid flex-1 text-left text-sm leading-tight">
                <span className="truncate font-semibold">{t("brand.name")}</span>
                <span className="truncate text-xs text-muted-foreground">
                  {t("brand.tagline")}
                </span>
              </div>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>
      <SidebarContent>
        <NavMain items={navHome} label={t("nav.group.overview")} />
        <NavMain items={navContext} label={t("nav.group.context")} />
        <NavMain items={navEvidence} label={t("nav.group.evidence")} />
        <NavMain items={navValidity} label={t("nav.group.validity")} />
        <NavMain items={navGuard} label={t("nav.group.guard")} />
        <NavMain items={navReference} label={t("nav.group.reference")} />
      </SidebarContent>
    </Sidebar>
  );
}
