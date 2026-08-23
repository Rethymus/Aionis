"use client";

import { SegmentHeader } from "@/components/segment-header";
import { FinDeadlineView } from "@/components/filings/fin-deadline-view";
import { aionis } from "@/data/aionis";

export default function QuarterlyPage() {
  return (
    <div className="space-y-6 p-4 md:p-6">
      <SegmentHeader
        segment="context"
        introKey="filings.quarterly.intro"
        asOf={aionis.filingStream.as_of ?? undefined}
        countHint={
          aionis.filingStream.status === "ok"
            ? `${aionis.filingStream.quarterly_total.toLocaleString("en-US")} 10-Q · ${aionis.filingStream.window.start} → ${aionis.filingStream.window.end}`
            : undefined
        }
      />
      <FinDeadlineView variant="quarterly" />
    </div>
  );
}
