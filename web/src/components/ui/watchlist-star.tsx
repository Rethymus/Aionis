"use client";

// Watchlist star toggle (round 156): a compact star button that adds/removes
// a ticker from the localStorage watchlist. Rendered inside Link cards, so
// click propagation is stopped to avoid navigating away on toggle.
//
// Hydration safety: useSyncExternalStore's designed behavior handles the
// SSR→client transition — getServerSnapshot returns "" (empty set, unstarred)
// during hydration, then getSnapshot picks up localStorage on the first
// post-hydration render. No mounted gate needed (round-136 lesson: verify
// with a static-build probe, not just dev).

import { StarIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import { useWatchlist } from "@/lib/watchlist";

export function WatchlistStar({
  ticker,
  className,
}: {
  ticker: string;
  className?: string;
}) {
  const { isWatched, toggle } = useWatchlist();
  const watched = isWatched(ticker);

  return (
    <button
      type="button"
      aria-pressed={watched}
      aria-label={
        watched
          ? `Remove ${ticker} from watchlist`
          : `Add ${ticker} to watchlist`
      }
      className={cn(
        "relative z-10 inline-flex size-6 cursor-pointer items-center justify-center rounded-md transition-colors",
        "hover:bg-soft focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring",
        className,
      )}
      onClick={(e) => {
        e.preventDefault();
        e.stopPropagation();
        toggle(ticker);
      }}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          e.stopPropagation();
          toggle(ticker);
        }
      }}
    >
      <StarIcon
        className={cn(
          "size-3.5 transition-colors",
          watched
            ? "fill-amber-400 text-amber-400"
            : "text-muted-foreground/60 hover:text-amber-400",
        )}
        aria-hidden="true"
      />
    </button>
  );
}
