"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { PicksView } from "@/components/picks/picks-view";
import { SectorsView } from "@/components/sectors/sectors-view";
import { ThemeSlice } from "@/components/themes/theme-slice";
import { SegmentHeader } from "@/components/segment-header";
import { StickyTabs } from "@/components/sticky-tabs";
import { useI18n } from "@/i18n/provider";
import { aionis } from "@/data/aionis";

// The conviction tab is the only recharts consumer on this route (~376KB);
// Radix keeps inactive tab content unmounted, so deferring it keeps the
// chart library out of the initial payload — it loads on first tab click.
const ConvictionView = dynamic(
  () => import("@/components/conviction/conviction-view").then((m) => m.ConvictionView),
  { ssr: false },
);

const hashToTabMap: Record<string, string> = {
  "#picks": "picks",
  "#sectors": "sectors",
  "#conviction": "conviction",
  "#factors": "factors",
};

const defaultTab = "picks";

export default function PicksPage() {
  const { t } = useI18n();
  const [activeTab, setActiveTab] = useState<string>(() => {
    if (typeof window !== "undefined") {
      const hash = window.location.hash;
      return hashToTabMap[hash] || defaultTab;
    }
    return defaultTab;
  });

  useEffect(() => {
    const handleHashChange = () => {
      const hash = window.location.hash;
      setActiveTab(hashToTabMap[hash] || defaultTab);
    };

    window.addEventListener("hashchange", handleHashChange);
    return () => window.removeEventListener("hashchange", handleHashChange);
  }, []);

  const handleTabChange = (tab: string) => {
    setActiveTab(tab);
    window.location.hash = tab;
  };

  return (
    <div className="space-y-6 p-4 md:p-6">
      <SegmentHeader segment="evidence" introKey="picks_hub.intro" asOf={aionis.picksMeta.latest_date} frozen />

      <Tabs value={activeTab} onValueChange={handleTabChange}>
        <StickyTabs>
        <TabsList>
          <TabsTrigger value="picks">{t("nav.picks")}</TabsTrigger>
          <TabsTrigger value="sectors">{t("nav.sectors")}</TabsTrigger>
          <TabsTrigger value="conviction">{t("nav.conviction")}</TabsTrigger>
          <TabsTrigger value="factors">{t("nav.factors")}</TabsTrigger>
        </TabsList>
        </StickyTabs>


        <TabsContent value="picks">
          <PicksView />
        </TabsContent>
        <TabsContent value="sectors">
          <SectorsView />
        </TabsContent>
        <TabsContent value="conviction">
          <ConvictionView />
        </TabsContent>
        <TabsContent value="factors">
          <ThemeSlice keys={["price", "fundamentals", "risk", "market_structure"]} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
