"use client";

import { SegmentHeader } from "@/components/segment-header";
import { InstitutionsView } from "@/components/institutions/institutions-view";
import { form13f } from "@/data/aionis/form13f";

export default function InstitutionsPage() {
  return (
    <div className="space-y-6 p-4 md:p-6">
      <SegmentHeader
        segment="evidence"
        introKey="institutions.intro"
        asOf={form13f.as_of ?? undefined}
      />
      <InstitutionsView />
    </div>
  );
}
