"use client";

import { useEffect, useState } from "react";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { CalibrationView } from "@/components/calibration/calibration-view";
import { PowerFloorView } from "@/components/powerfloor/power-floor-view";
import { ModelHealthView } from "@/components/model-health/model-health-view";
import { ThemeSlice } from "@/components/themes/theme-slice";
import { useI18n } from "@/i18n/provider";

const hashToTabMap: Record<string, string> = {
  "#calibration": "calibration",
  "#power-floor": "power-floor",
  "#model-health": "model-health",
  "#cost": "cost",
};

const defaultTab = "calibration";

export default function TrackPage() {
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
      <header className="space-y-1">
        <p className="text-xs font-medium text-primary">{t("nav.group.track")}</p>
        <p className="text-sm text-muted-foreground">{t("track_hub.intro")}</p>
      </header>

      <Tabs value={activeTab} onValueChange={handleTabChange}>
        <TabsList>
          <TabsTrigger value="calibration">{t("nav.calibration")}</TabsTrigger>
          <TabsTrigger value="power-floor">{t("nav.powerfloor")}</TabsTrigger>
          <TabsTrigger value="model-health">{t("nav.modelhealth")}</TabsTrigger>
          <TabsTrigger value="cost">{t("nav.cost")}</TabsTrigger>
        </TabsList>

        <TabsContent value="calibration">
          <CalibrationView />
        </TabsContent>
        <TabsContent value="power-floor">
          <PowerFloorView />
        </TabsContent>
        <TabsContent value="model-health">
          <ModelHealthView />
        </TabsContent>
        <TabsContent value="cost">
          <ThemeSlice keys={["net_cost"]} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
