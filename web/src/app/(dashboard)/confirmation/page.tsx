"use client";

import { useEffect, useState } from "react";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import dynamic from "next/dynamic";
import { SmartMoneyView } from "@/components/smart-money/smart-money-view";
// Round 124: per-tab split (round-121 recipe) — default tab stays static
// (SSR intact); inactive tabs never had SSR output, so nothing is lost.
const InsidersView = dynamic(() => import("@/components/insiders/insiders-view").then(m => m.InsidersView));
const RedditView = dynamic(() => import("@/components/reddit/reddit-view").then(m => m.RedditView));
const ThemeSlice = dynamic(() => import("@/components/themes/theme-slice").then(m => m.ThemeSlice));
import { SegmentHeader } from "@/components/segment-header";
import { StickyTabs } from "@/components/sticky-tabs";
import { useTabHotkeys } from "@/lib/use-tab-hotkeys";
import { aionis } from "@/data/aionis";
import { useI18n } from "@/i18n/provider";

const hashToTabMap: Record<string, string> = {
  "#smart-money": "smart-money",
  "#insiders": "insiders",
  "#reddit": "reddit",
  "#news": "news",
};

const defaultTab = "smart-money";

export default function ConfirmationPage() {
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

  useTabHotkeys(["smart-money", "insiders", "reddit", "news"], activeTab, handleTabChange);

  return (
    <div className="space-y-6 p-4 md:p-6">
      <SegmentHeader segment="evidence" introKey="confirmation_hub.intro" asOf={aionis.smartMoney.latest_date ?? undefined} />

      <Tabs value={activeTab} onValueChange={handleTabChange}>
        <StickyTabs>
        <TabsList>
          <TabsTrigger value="smart-money">{t("nav.smartmoney")}</TabsTrigger>
          <TabsTrigger value="insiders">{t("nav.insiders")}</TabsTrigger>
          <TabsTrigger value="reddit">{t("nav.reddit")}</TabsTrigger>
          <TabsTrigger value="news">{t("nav.news")}</TabsTrigger>
        </TabsList>
        </StickyTabs>


        <TabsContent value="smart-money">
          <SmartMoneyView />
        </TabsContent>
        <TabsContent value="insiders">
          <InsidersView />
        </TabsContent>
        <TabsContent value="reddit">
          <RedditView />
        </TabsContent>
        <TabsContent value="news">
          <ThemeSlice keys={["news_sentiment"]} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
