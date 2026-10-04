// Sticky tab strip — hub pages run several screens deep (the picks tab alone
// is ~10 screens); without a pinned tab row, switching evidence mid-scroll
// means scrolling all the way back to the top. Pins directly under the frosted
// nav bar (h-14 → top-14, no sliver of content between) with the same Apple
// material, so bar + tabs read as one continuous floating chrome layer.
//
// z-10 — MUST stay BELOW the nav header (z-20): the nav's hover dropdowns
// open downward over this strip, and at z≥20 they were painted behind it
// (owner-reported 2026-08-29). Above scrolling content (z-auto/0) is enough.
//
// Round 176: keyboard hint — the tab hotkeys (1-9 jump, [ ] cycle, round
// 166) are invisible without a discoverability surface. A subtle kbd hint
// rides the right edge of the tab strip (hidden on touch-only widths).
export function StickyTabs({ children }: { children: React.ReactNode }) {
  return (
    <div className="sticky top-14 z-10 -mx-4 border-b border-border/60 bg-background/70 px-4 py-2 backdrop-blur-xl backdrop-saturate-150 md:-mx-6 md:px-6 shadow-[inset_0_1px_0_color-mix(in_srgb,var(--foreground)_14%,transparent)]">
      <div className="flex items-center gap-2">
        {children}
        <span
          className="ml-auto hidden shrink-0 items-center gap-0.5 text-[10px] text-muted-foreground/50 lg:inline-flex"
          title="1–9 jump to tab · [ ] cycle"
        >
          <kbd className="rounded border border-border/60 bg-muted/50 px-1 font-mono">1-9</kbd>
          <kbd className="rounded border border-border/60 bg-muted/50 px-1 font-mono">[</kbd>
          <kbd className="rounded border border-border/60 bg-muted/50 px-1 font-mono">]</kbd>
        </span>
      </div>
    </div>
  );
}
