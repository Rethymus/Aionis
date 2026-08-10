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
  TrendingUpIcon,
  ShieldCheckIcon,
  FileTextIcon,
  BriefcaseIcon,
  LayersIcon,
  TargetIcon,
} from "lucide-react";

export function AppSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
  const { t } = useI18n();

  // Decision funnel: each group answers one question, feeding the next.
  // The role is carried by the group LABEL (i18n nav.group.*), so the nav itself
  // reads as a reasoning chain (regime → themes → picks → confirmation → track → discipline).
  const navHome = [
    { title: t("nav.overview"), url: "/dashboard", icon: <LayoutDashboardIcon /> },
  ];
  // Decision funnel: each stage is ONE hub page (Tabs composing the former
  // standalone panels). Old routes still resolve by URL during the transition;
  // the sidebar now shows the ①→⑥ chain as 6 entries (+ overview) instead of 16.
  const navRegime = [
    { title: t("nav.group.regime"), url: "/regime", icon: <TrendingUpIcon /> },
  ];
  const navThemes = [
    { title: t("nav.themes"), url: "/themes", icon: <LayersIcon /> },
  ];
  const navPicks = [
    { title: t("nav.group.picks"), url: "/picks", icon: <TrendingUpIcon /> },
  ];
  const navConfirm = [
    { title: t("nav.group.confirm"), url: "/confirmation", icon: <BriefcaseIcon /> },
  ];
  const navTrack = [
    { title: t("nav.group.track"), url: "/track", icon: <TargetIcon /> },
  ];
  const navDiscipline = [
    { title: t("nav.group.discipline"), url: "/discipline", icon: <ShieldCheckIcon /> },
  ];
  const navReference = [
    {
      title: t("nav.method"),
      url: "https://github.com/Rethymus/Aionis/blob/main/docs/methods-and-results-draft.md",
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
        <NavMain items={navRegime} label={t("nav.group.regime")} />
        <NavMain items={navThemes} label={t("nav.group.themes")} />
        <NavMain items={navPicks} label={t("nav.group.picks")} />
        <NavMain items={navConfirm} label={t("nav.group.confirm")} />
        <NavMain items={navTrack} label={t("nav.group.track")} />
        <NavMain items={navDiscipline} label={t("nav.group.discipline")} />
        <NavMain items={navReference} label={t("nav.group.reference")} />
      </SidebarContent>
    </Sidebar>
  );
}
