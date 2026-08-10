"use client";

import { useEffect, useState } from "react";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { DisciplineView } from "@/components/discipline/discipline-view";
import { EvidenceView } from "@/components/evidence/evidence-view";
import { useI18n } from "@/i18n/provider";

const hashToTabMap: Record<string, string> = {
  "#discipline": "discipline",
  "#evidence": "evidence",
};

const defaultTab = "discipline";

export default function DisciplinePage() {
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
        <h1 className="text-2xl font-bold">{t("nav.group.discipline")}</h1>
        <p className="text-muted-foreground">
          Stage ⑥: 反泄漏边界 · PIT 数据纪律、PurgedKFold+Embargo、H6 确定性
        </p>
      </header>

      <Tabs value={activeTab} onValueChange={handleTabChange}>
        <TabsList>
          <TabsTrigger value="discipline">{t("nav.discipline")}</TabsTrigger>
          <TabsTrigger value="evidence">{t("nav.evidence")}</TabsTrigger>
        </TabsList>

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
