"use client";

import { SegmentHeader } from "@/components/segment-header";
import { NewsView } from "@/components/news/news-view";
import { aionis } from "@/data/aionis";

export default function NewsPage() {
  const f = aionis.newsFeed;
  return (
    <div className="space-y-6 p-4 md:p-6">
      <SegmentHeader
        segment="context"
        introKey="news.intro"
        asOf={f.as_of || undefined}
        countHint={
          f.status === "ok"
            ? `${f.total} · ${f.window.start} → ${f.window.end} · ${f.n_sources} sources`
            : undefined
        }
      />
      <NewsView />
    </div>
  );
}
