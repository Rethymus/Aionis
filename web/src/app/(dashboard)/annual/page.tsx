"use client";

import { SegmentHeader } from "@/components/segment-header";
import { FinDeadlineView } from "@/components/filings/fin-deadline-view";
import { filingStream } from "@/data/aionis/filing-stream";

export default function AnnualPage() {
  return (
    <div className="space-y-6 p-4 md:p-6">
      <SegmentHeader
        segment="context"
        introKey="filings.annual.intro"
        asOf={filingStream.as_of ?? undefined}
        countHint={
          filingStream.status === "ok"
            ? `${filingStream.annual_total.toLocaleString("en-US")} 10-K · ${filingStream.window.start} → ${filingStream.window.end}`
            : undefined
        }
      />
      <FinDeadlineView variant="annual" />
    </div>
  );
}
