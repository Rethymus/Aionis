// Sticky tab strip — hub pages run several screens deep (the picks tab alone
// is ~10 screens); without a pinned tab row, switching evidence mid-scroll
// means scrolling all the way back to the top. The strip bleeds to the page
// edges via negative margins so the pinned bar reads as a full-width rail,
// and uses backdrop-blur so content scrolls legibly beneath it.
export function StickyTabs({ children }: { children: React.ReactNode }) {
  return (
    <div className="sticky top-0 z-30 -mx-4 border-b bg-background/95 px-4 py-2 backdrop-blur md:-mx-6 md:px-6">
      {children}
    </div>
  );
}
