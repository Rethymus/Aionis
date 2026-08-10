"use client";

import { useEffect, useState } from "react";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { MarketView } from "@/components/market/market-view";
import { PositioningView } from "@/components/positioning/positioning-view";
import { TacoView } from "@/components/taco/taco-view";
import { useI18n } from "@/i18n/provider";

const hashToTabMap: Record<string, string> = {
  "#market": "market",
  "#positioning": "positioning",
  "#taco": "taco",
};

const defaultTab = "market";

export default function RegimePage() {
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
      <header className="space-y-2">
        <h1 className="text-2xl font-bold">{t("nav.group.regime")}</h1>
        <p className="text-muted-foreground">{t("regime_hub.intro")}</p>
      </header>

      <Tabs value={activeTab} onValueChange={handleTabChange}>
        <TabsList>
          <TabsTrigger value="market">{t("nav.market")}</TabsTrigger>
          <TabsTrigger value="positioning">{t("nav.positioning")}</TabsTrigger>
          <TabsTrigger value="taco">{t("nav.taco")}</TabsTrigger>
        </TabsList>

        <TabsContent value="market">
          <MarketView />
        </TabsContent>
        <TabsContent value="positioning">
          <PositioningView />
        </TabsContent>
        <TabsContent value="taco">
          <TacoView />
        </TabsContent>
      </Tabs>
    </div>
  );
}
