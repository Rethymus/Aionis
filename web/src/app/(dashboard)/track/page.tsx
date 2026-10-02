"use client";

import { useEffect, useState } from "react";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import dynamic from "next/dynamic";
import { CalibrationView } from "@/components/calibration/calibration-view";
// Round 121: only the ACTIVE tab renders into the DOM (Radix TabsContent),
// but every view's module graph still shipped in the initial bundle. The
// default tab keeps its static import (SSR content intact); the rest split
// into per-tab chunks loaded on first activation — SSR loses nothing
// (inactive tabs never had SSR output). Same for /regime.
const PowerFloorView = dynamic(() => import("@/components/powerfloor/power-floor-view").then(m => m.PowerFloorView));
const ModelHealthView = dynamic(() => import("@/components/model-health/model-health-view").then(m => m.ModelHealthView));
const DisciplineView = dynamic(() => import("@/components/discipline/discipline-view").then(m => m.DisciplineView));
const EvidenceView = dynamic(() => import("@/components/evidence/evidence-view").then(m => m.EvidenceView));
const ThemeSlice = dynamic(() => import("@/components/themes/theme-slice").then(m => m.ThemeSlice));
import { SegmentHeader } from "@/components/segment-header";
import { StickyTabs } from "@/components/sticky-tabs";
import { AiAttributionCard } from "@/components/ai/attribution-card";
import { aionis } from "@/data/aionis";
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
      <SegmentHeader segment="validity" introKey="track_hub.intro" asOf={aionis.metrics.latest_month} frozen />
      <AiAttributionCard />

      <Tabs value={activeTab} onValueChange={handleTabChange}>
        <StickyTabs>
        <TabsList>
          <TabsTrigger value="calibration">{t("nav.calibration")}</TabsTrigger>
          <TabsTrigger value="power-floor">{t("nav.powerfloor")}</TabsTrigger>
          <TabsTrigger value="model-health">{t("nav.modelhealth")}</TabsTrigger>
          <TabsTrigger value="cost">{t("nav.cost")}</TabsTrigger>
          <TabsTrigger value="discipline">{t("nav.discipline")}</TabsTrigger>
          <TabsTrigger value="evidence">{t("nav.evidence")}</TabsTrigger>
        </TabsList>
        </StickyTabs>


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
