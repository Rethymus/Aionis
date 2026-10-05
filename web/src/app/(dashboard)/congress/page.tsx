"use client";

import { SegmentHeader } from "@/components/segment-header";
import { CongressView } from "@/components/congress/congress-view";
import { politicianTrades } from "@/data/aionis/politician-trades";

export default function CongressPage() {
  return (
    <div className="space-y-6 p-4 md:p-6">
      <SegmentHeader
        segment="evidence"
        introKey="congress.intro"
        asOf={politicianTrades.as_of ?? undefined}
        countHint={
          politicianTrades.status === "ok"
            ? `${politicianTrades.house.total} · ${politicianTrades.window_years.join("–")} · ${politicianTrades.house.members} members`
            : undefined
        }
      />
      <CongressView />
    </div>
  );
}
