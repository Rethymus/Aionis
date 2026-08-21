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
      />
      <EventsView />
    </div>
  );
}
