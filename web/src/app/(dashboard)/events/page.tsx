"use client";

import { SegmentHeader } from "@/components/segment-header";
import { EventsView } from "@/components/events/events-view";
import { aionis } from "@/data/aionis";

export default function EventsPage() {
  return (
    <div className="space-y-6 p-4 md:p-6">
      <SegmentHeader
        segment="evidence"
        introKey="events.intro"
        asOf={aionis.form8k.as_of ?? undefined}
        countHint={
          aionis.form8k.status === "ok"
            ? `${aionis.form8k.total} · ${aionis.form8k.window.start} → ${aionis.form8k.window.end} · ${aionis.form8k.issuers} issuers`
            : undefined
        }
      />
      <EventsView />
    </div>
  );
}
