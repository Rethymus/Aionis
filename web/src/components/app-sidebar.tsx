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
  ScaleIcon,
  ActivityIcon,
  GaugeIcon,
  ShieldCheckIcon,
  FileTextIcon,
  MessageCircleIcon,
  FlameIcon,
  BriefcaseIcon,
  UsersIcon,
  BarChartHorizontalIcon,
  BlocksIcon,
  HeartPulseIcon,
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
  const navRegime = [
    { title: t("nav.market"), url: "/market", icon: <TrendingUpIcon /> },
    { title: t("nav.positioning"), url: "/positioning", icon: <BarChartHorizontalIcon /> },
    { title: t("nav.taco"), url: "/taco", icon: <FlameIcon /> },
  ];
  const navThemes = [
    { title: t("nav.themes"), url: "/themes", icon: <LayersIcon /> },
  ];
  const navPicks = [
    { title: t("nav.picks"), url: "/picks", icon: <TrendingUpIcon /> },
    { title: t("nav.sectors"), url: "/sectors", icon: <BlocksIcon /> },
    { title: t("nav.conviction"), url: "/conviction", icon: <ActivityIcon /> },
  ];
  const navConfirm = [
    { title: t("nav.smartmoney"), url: "/smart-money", icon: <BriefcaseIcon /> },
    { title: t("nav.insiders"), url: "/insiders", icon: <UsersIcon /> },
    // Reddit activated via zero-credential Atom RSS (OAuth gated behind the 2026
    // Responsible Builder Policy; unauth .json 403). Live when a snapshot exists.
    { title: t("nav.reddit"), url: "/reddit", icon: <MessageCircleIcon /> },
  ];
  const navTrack = [
    { title: t("nav.calibration"), url: "/calibration", icon: <TargetIcon /> },
    { title: t("nav.powerfloor"), url: "/power-floor", icon: <GaugeIcon /> },
    { title: t("nav.modelhealth"), url: "/model-health", icon: <HeartPulseIcon /> },
  ];
  const navDiscipline = [
    { title: t("nav.discipline"), url: "/discipline", icon: <ShieldCheckIcon /> },
    { title: t("nav.evidence"), url: "/evidence", icon: <ScaleIcon /> },
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
