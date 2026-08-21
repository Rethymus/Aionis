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
      />
      <IpoView />
    </div>
  );
}
