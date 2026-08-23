"use client";

import { SegmentHeader } from "@/components/segment-header";
import { ShelfView } from "@/components/shelf/shelf-view";

// Method shelf — browsable catalog over the repo's own method docs + curated
// outbound research bookmarks (display/reference layer only, zero network).
export default function ShelfPage() {
  return (
    <div className="space-y-6 p-4 md:p-6">
      <SegmentHeader segment="guard" introKey="shelf.intro" />
      <ShelfView />
    </div>
  );
}
