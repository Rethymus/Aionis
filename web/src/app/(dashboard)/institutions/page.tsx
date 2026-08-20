"use client";

import { SegmentHeader } from "@/components/segment-header";
import { InstitutionsView } from "@/components/institutions/institutions-view";
import { aionis } from "@/data/aionis";

export default function InstitutionsPage() {
  return (
    <div className="space-y-6 p-4 md:p-6">
      <SegmentHeader
        segment="evidence"
        introKey="institutions.intro"
        asOf={aionis.form13f.as_of ?? undefined}
      />
      <InstitutionsView />
    </div>
  );
}
