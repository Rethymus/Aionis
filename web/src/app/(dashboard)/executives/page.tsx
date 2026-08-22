"use client";

import { SegmentHeader } from "@/components/segment-header";
import { ExecutivesView } from "@/components/executives/executives-view";
import { aionis } from "@/data/aionis";

export default function ExecutivesPage() {
  return (
    <div className="space-y-6 p-4 md:p-6">
      <SegmentHeader
        segment="evidence"
        introKey="executives.intro"
        asOf={aionis.executives.as_of ?? undefined}
        countHint={
          aionis.executives.status === "ok" && aionis.executives.total > 0
            ? `${aionis.executives.total} · ${aionis.executives.window.start} → ${aionis.executives.window.end} · ${aionis.executives.issuers} issuers`
            : undefined
        }
      />
      <ExecutivesView />
    </div>
  );
}
