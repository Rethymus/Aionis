"use client";

import { SegmentHeader } from "@/components/segment-header";
import { IpoView } from "@/components/ipo/ipo-view";
import { aionis } from "@/data/aionis";

export default function IpoPage() {
  return (
    <div className="space-y-6 p-4 md:p-6">
      <SegmentHeader
        segment="evidence"
        introKey="ipo.intro"
        asOf={aionis.ipo.as_of ?? undefined}
        countHint={
          aionis.ipo.status === "ok"
            ? `${aionis.ipo.total} · ${aionis.ipo.window.start} → ${aionis.ipo.window.end} · ${aionis.ipo.issuers} issuers`
            : undefined
        }
      />
      <IpoView />
    </div>
  );
}
