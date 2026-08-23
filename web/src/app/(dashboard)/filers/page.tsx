"use client";

import { SegmentHeader } from "@/components/segment-header";
import { FilersView } from "@/components/filers/filers-view";
import { filers13f } from "@/data/aionis/filers13f";

export default function FilersPage() {
  return (
    <div className="space-y-6 p-4 md:p-6">
      <SegmentHeader
        segment="evidence"
        introKey="filers.intro"
        asOf={filers13f.as_of ?? undefined}
      />
      <FilersView />
    </div>
  );
}
