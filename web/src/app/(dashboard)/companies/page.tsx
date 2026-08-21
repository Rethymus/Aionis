"use client";

import { SegmentHeader } from "@/components/segment-header";
import { CompaniesView } from "@/components/companies/companies-view";

// Company directory — A-Z index over the frozen OOS universe (display layer
// only; same frozen per-stock readouts the /stock pages render, zero network).
export default function CompaniesPage() {
  return (
    <div className="space-y-6 p-4 md:p-6">
      <SegmentHeader segment="evidence" introKey="companies.intro" />
      <CompaniesView />
    </div>
  );
}
