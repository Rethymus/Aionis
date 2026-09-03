// Sticky tab strip — hub pages run several screens deep (the picks tab alone
// is ~10 screens); without a pinned tab row, switching evidence mid-scroll
// means scrolling all the way back to the top. Pins directly under the frosted
// nav bar (h-14 → top-14, no sliver of content between) with the same Apple
// material, so bar + tabs read as one continuous floating chrome layer.
//
// z-10 — MUST stay BELOW the nav header (z-20): the nav's hover dropdowns
// open downward over this strip, and at z≥20 they were painted behind it
// (owner-reported 2026-08-29). Above scrolling content (z-auto/0) is enough.
export function StickyTabs({ children }: { children: React.ReactNode }) {
  return (
    <div className="sticky top-14 z-10 -mx-4 border-b border-border/60 bg-background/70 px-4 py-2 backdrop-blur-xl backdrop-saturate-150 md:-mx-6 md:px-6 shadow-[inset_0_1px_0_color-mix(in_srgb,var(--foreground)_14%,transparent)]">
      {children}
    </div>
  );
}
