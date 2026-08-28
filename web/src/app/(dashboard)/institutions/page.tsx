"use client";

import { SegmentHeader } from "@/components/segment-header";
import { InstitutionsView } from "@/components/institutions/institutions-view";
import { ProvenanceBadge } from "@/components/provenance-badge";
import { form13f } from "@/data/aionis/form13f";
import { filers13f } from "@/data/aionis/filers13f";
import { useI18n } from "@/i18n/provider";

export default function InstitutionsPage() {
  const { t } = useI18n();
  return (
    <div className="space-y-6 p-4 md:p-6">
      <SegmentHeader
        segment="evidence"
        introKey="institutions.intro"
        asOf={form13f.as_of ?? undefined}
        extra={
          /* Two distinct waterlines live behind this hub: the curated 13F
             holdings book (quarterly quarter-end) and the all-filer directory
             (rolling filed envelope). Showing only the quarter-end read as a
             stale directory was the r23 audit P3-1 — both chips, labeled. */
          <ProvenanceBadge
            ts={filers13f.as_of ?? undefined}
            source={t("institutions.asof.filers")}
            className="ml-1"
          />
        }
      />
      <InstitutionsView />
    </div>
  );
}
