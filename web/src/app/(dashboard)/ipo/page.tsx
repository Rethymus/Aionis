"use client";

import { SegmentHeader } from "@/components/segment-header";
import { IpoView } from "@/components/ipo/ipo-view";
import { formIpo } from "@/data/aionis/form-ipo";

export default function IpoPage() {
  return (
    <div className="space-y-6 p-4 md:p-6">
      <SegmentHeader
        segment="evidence"
        introKey="ipo.intro"
        asOf={formIpo.as_of ?? undefined}
        countHint={
          formIpo.status === "ok"
            ? `${formIpo.total} · ${formIpo.window.start} → ${formIpo.window.end} · ${formIpo.issuers} issuers`
            : undefined
        }
      />
      <IpoView />
    </div>
  );
}
