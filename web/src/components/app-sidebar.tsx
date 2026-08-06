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
  GaugeIcon,
  ShieldCheckIcon,
  FileTextIcon,
} from "lucide-react";

export function AppSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
  const { t } = useI18n();

  const navInsights = [
    { title: t("nav.overview"), url: "/dashboard", icon: <LayoutDashboardIcon /> },
    { title: t("nav.picks"), url: "/picks", icon: <TrendingUpIcon /> },
    { title: t("nav.evidence"), url: "/evidence", icon: <ScaleIcon /> },
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
        <NavMain items={navMonitor} label={t("nav.group.monitor")} />
        <NavMain items={navReference} label={t("nav.group.reference")} />
      </SidebarContent>
    </Sidebar>
  );
}
