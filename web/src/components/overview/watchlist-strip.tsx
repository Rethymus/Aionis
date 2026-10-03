"use client";

// WatchlistStrip (round 158): a compact live-price strip for the user's
// starred tickers, rendered on the dashboard/home page. Renders nothing
// when the watchlist is empty (zero- ceremony empty state). Uses the
// existing Worker price endpoint via useLivePrices.

import Link from "next/link";
import { useMemo } from "react";
import { useLivePrices } from "@/lib/live-prices";
import { useWatchlist } from "@/lib/watchlist";
import { StarIcon } from "lucide-react";
import { cn } from "@/lib/utils";

export function WatchlistStrip() {
  const { watched } = useWatchlist();

  const tickers = useMemo(() => {
    return [...watched].map((ticker) => ({
      ticker,
      region: /^(sh|sz|bj)\./.test(ticker) ? "cn" : "us",
    }));
  }, [watched]);

  const { prices } = useLivePrices(tickers);

  if (tickers.length === 0) return null;

  return (
    <div className="flex flex-wrap items-center gap-2 rounded-xl border border-amber-400/20 bg-amber-400/[0.03] px-3 py-2">
      <span className="inline-flex items-center gap-1 text-[11px] font-medium text-amber-600 dark:text-amber-400">
        <StarIcon className="size-3 fill-amber-400 text-amber-400" />
        Watchlist
      </span>
      <div className="flex flex-wrap items-center gap-1.5">
        {tickers.map(({ ticker, region }) => {
          const p = prices[ticker];
          const positive = (p?.change_pct ?? 0) >= 0;
          return (
            <Link
              key={ticker}
              href={`/stock/${ticker}`}
              className="group inline-flex items-center gap-1.5 rounded-lg border border-line bg-card px-2.5 py-1 text-xs transition-colors hover:border-faint"
            >
              <StarIcon className="size-2.5 fill-amber-400/60 text-amber-400/60" />
              <span className="font-mono font-medium">{ticker}</span>
              {p?.price != null ? (
                <span className="font-mono tabular-nums text-foreground">
                  {region === "cn" ? "¥" : "$"}
                  {p.price.toFixed(2)}
                </span>
              ) : null}
              {p?.change_pct != null ? (
                <span
                  className={cn(
                    "font-mono text-[11px] tabular-nums",
                    positive ? "text-up" : "text-down",
                  )}
                >
                  {positive ? "+" : ""}
                  {p.change_pct.toFixed(2)}%
                </span>
              ) : null}
            </Link>
          );
        })}
      </div>
    </div>
  );
}
