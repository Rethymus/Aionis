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
} from "lucide-react";

export function AppSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
  const { t } = useI18n();

  const navInsights = [
    { title: t("nav.overview"), url: "/dashboard", icon: <LayoutDashboardIcon /> },
    { title: t("nav.picks"), url: "/picks", icon: <TrendingUpIcon /> },
    { title: t("nav.sectors"), url: "/sectors", icon: <BlocksIcon /> },
    { title: t("nav.market"), url: "/market", icon: <TrendingUpIcon /> },
    { title: t("nav.evidence"), url: "/evidence", icon: <ScaleIcon /> },
    { title: t("nav.conviction"), url: "/conviction", icon: <ActivityIcon /> },
  ];
  const navAlternative = [
    { title: t("nav.positioning"), url: "/positioning", icon: <BarChartHorizontalIcon /> },
    { title: t("nav.smartmoney"), url: "/smart-money", icon: <BriefcaseIcon /> },
    { title: t("nav.insiders"), url: "/insiders", icon: <UsersIcon /> },
    { title: t("nav.taco"), url: "/taco", icon: <FlameIcon /> },
    // Reddit temporarily hidden — API access blocked (2025-11 self-service closure).
    // Page still exists at /reddit; restore nav when API is reactivated.
    // { title: t("nav.reddit"), url: "/reddit", icon: <MessageCircleIcon /> },
  ];
  const navMonitor = [
    { title: t("nav.powerfloor"), url: "/power-floor", icon: <GaugeIcon /> },
    { title: t("nav.discipline"), url: "/discipline", icon: <ShieldCheckIcon /> },
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
        <NavMain items={navInsights} label={t("nav.group.insights")} />
        <NavMain items={navAlternative} label={t("nav.group.alternative")} />
        <NavMain items={navMonitor} label={t("nav.group.monitor")} />
        <NavMain items={navReference} label={t("nav.group.reference")} />
      </SidebarContent>
    </Sidebar>
  );
}
