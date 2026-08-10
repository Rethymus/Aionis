"use client";

import { useEffect, useState } from "react";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { SmartMoneyView } from "@/components/smart-money/smart-money-view";
import { InsidersView } from "@/components/insiders/insiders-view";
import { RedditView } from "@/components/reddit/reddit-view";
import { useI18n } from "@/i18n/provider";

const hashToTabMap: Record<string, string> = {
  "#smart-money": "smart-money",
  "#insiders": "insiders",
  "#reddit": "reddit",
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

  return (
    <div className="space-y-6 p-4 md:p-6">
      <header className="space-y-1">
        <p className="text-xs font-medium text-primary">{t("nav.group.confirm")}</p>
        <p className="text-sm text-muted-foreground">{t("confirmation_hub.intro")}</p>
      </header>

      <Tabs value={activeTab} onValueChange={handleTabChange}>
        <TabsList>
          <TabsTrigger value="smart-money">{t("nav.smartmoney")}</TabsTrigger>
          <TabsTrigger value="insiders">{t("nav.insiders")}</TabsTrigger>
          <TabsTrigger value="reddit">{t("nav.reddit")}</TabsTrigger>
        </TabsList>

        <TabsContent value="smart-money">
          <SmartMoneyView />
        </TabsContent>
        <TabsContent value="insiders">
          <InsidersView />
        </TabsContent>
        <TabsContent value="reddit">
          <RedditView />
        </TabsContent>
      </Tabs>
    </div>
  );
}
