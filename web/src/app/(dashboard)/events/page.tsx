"use client";

import { SegmentHeader } from "@/components/segment-header";
import { EventsView } from "@/components/events/events-view";
import form8k from "@/data/aionis/form8k";
import { aionis } from "@/data/aionis";

export default function EventsPage() {
  return (
    <div className="space-y-6 p-4 md:p-6">
      <SegmentHeader
        segment="evidence"
        introKey="events.intro"
        asOf={form8k.as_of ?? undefined}
        countHint={
          form8k.status === "ok"
            ? `${form8k.total} · ${form8k.window.start} → ${form8k.window.end} · ${form8k.issuers} issuers`
            : undefined
        }
      />
      <EventsView />
    </div>
  );
}
