"use client";

import { useEffect, useState } from "react";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { CalibrationView } from "@/components/calibration/calibration-view";
import { PowerFloorView } from "@/components/powerfloor/power-floor-view";
import { ModelHealthView } from "@/components/model-health/model-health-view";
import { DisciplineView } from "@/components/discipline/discipline-view";
import { EvidenceView } from "@/components/evidence/evidence-view";
import { ThemeSlice } from "@/components/themes/theme-slice";
import { SegmentHeader } from "@/components/segment-header";
import { useI18n } from "@/i18n/provider";

const hashToTabMap: Record<string, string> = {
  "#calibration": "calibration",
  "#power-floor": "power-floor",
  "#model-health": "model-health",
  "#cost": "cost",
  "#discipline": "discipline",
  "#evidence": "evidence",
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
      <SegmentHeader segment="validity" introKey="track_hub.intro" />

      <Tabs value={activeTab} onValueChange={handleTabChange}>
        <TabsList>
          <TabsTrigger value="calibration">{t("nav.calibration")}</TabsTrigger>
          <TabsTrigger value="power-floor">{t("nav.powerfloor")}</TabsTrigger>
          <TabsTrigger value="model-health">{t("nav.modelhealth")}</TabsTrigger>
          <TabsTrigger value="cost">{t("nav.cost")}</TabsTrigger>
          <TabsTrigger value="discipline">{t("nav.discipline")}</TabsTrigger>
          <TabsTrigger value="evidence">{t("nav.evidence")}</TabsTrigger>
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
        <TabsContent value="discipline">
          <DisciplineView />
        </TabsContent>
        <TabsContent value="evidence">
          <EvidenceView />
        </TabsContent>
      </Tabs>
    </div>
  );
}
