"use client";

import { SegmentHeader } from "@/components/segment-header";
import { CongressView } from "@/components/congress/congress-view";

export default function CongressPage() {
  return (
    <div className="space-y-6 p-4 md:p-6">
      <SegmentHeader segment="evidence" introKey="congress.intro" />
      <CongressView />
    </div>
  );
}
