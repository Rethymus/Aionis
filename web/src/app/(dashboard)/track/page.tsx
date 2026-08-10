"use client";

import { useEffect, useState } from "react";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { CalibrationView } from "@/components/calibration/calibration-view";
import { PowerFloorView } from "@/components/powerfloor/power-floor-view";
import { ModelHealthView } from "@/components/model-health/model-health-view";
import { useI18n } from "@/i18n/provider";

const hashToTabMap: Record<string, string> = {
  "#calibration": "calibration",
  "#power-floor": "power-floor",
  "#model-health": "model-health",
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
      <header className="space-y-2">
        <h1 className="text-2xl font-bold">{t("nav.group.track")}</h1>
        <p className="text-muted-foreground">{t("track_hub.intro")}</p>
      </header>

      <Tabs value={activeTab} onValueChange={handleTabChange}>
        <TabsList>
          <TabsTrigger value="calibration">{t("nav.calibration")}</TabsTrigger>
          <TabsTrigger value="power-floor">{t("nav.powerfloor")}</TabsTrigger>
          <TabsTrigger value="model-health">{t("nav.modelhealth")}</TabsTrigger>
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
      </Tabs>
    </div>
  );
}
