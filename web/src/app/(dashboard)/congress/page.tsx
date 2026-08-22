"use client";

import { SegmentHeader } from "@/components/segment-header";
import { CongressView } from "@/components/congress/congress-view";
import { aionis } from "@/data/aionis";

export default function CongressPage() {
  return (
    <div className="space-y-6 p-4 md:p-6">
      <SegmentHeader
        segment="evidence"
        introKey="congress.intro"
        asOf={aionis.politicianTrades.as_of ?? undefined}
        countHint={
          aionis.politicianTrades.status === "ok"
            ? `${aionis.politicianTrades.house.total} · ${aionis.politicianTrades.window_years.join("–")} · ${aionis.politicianTrades.house.members} members`
            : undefined
        }
      />
      <CongressView />
    </div>
  );
}
