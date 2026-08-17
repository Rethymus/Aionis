// Sticky tab strip — hub pages run several screens deep (the picks tab alone
// is ~10 screens); without a pinned tab row, switching evidence mid-scroll
// means scrolling all the way back to the top. Pins directly under the
// frosted nav bar (h-16) with the same Apple material, so bar + tabs read as
// one continuous floating chrome layer over the scrolling content.
export function StickyTabs({ children }: { children: React.ReactNode }) {
  return (
    <div className="sticky top-16 z-30 -mx-4 border-b border-border/60 bg-background/70 px-4 py-2 backdrop-blur-xl backdrop-saturate-150 md:-mx-6 md:px-6">
      {children}
    </div>
  );
}
