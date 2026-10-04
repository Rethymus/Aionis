"use client";

// WatchlistStrip (round 158): a compact live-price strip for the user's
// starred tickers, rendered on the dashboard/home page. Renders nothing
// when the watchlist is empty (zero- ceremony empty state). Uses the
// existing Worker price endpoint via useLivePrices.

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useLivePrices } from "@/lib/live-prices";
import { getLastSeenRanks, saveCurrentRanks, useWatchlist } from "@/lib/watchlist";
import { StarIcon, TrendingDownIcon, TrendingUpIcon } from "lucide-react";
import { aionis } from "@/data/aionis";
import { cn } from "@/lib/utils";

export function WatchlistStrip() {
  const { watched } = useWatchlist();
  const [rankDeltas, setRankDeltas] = useState<Record<string, number | null>>({});

  const tickers = useMemo(() => {
    return [...watched].map((ticker) => ({
      ticker,
      region: /^(sh|sz|bj)\./.test(ticker) ? "cn" : "us",
    }));
  }, [watched]);

  const { prices } = useLivePrices(tickers);

  // Rank-change tracking (round 165): compare the frozen picks ranks against
  // the last-seen snapshot in localStorage, show ↑N/↓N per watched ticker,
  // then persist the current ranks as the new baseline. Client-only (SSR
  // renders no badges — the strip itself renders null until mounted anyway).
  useEffect(() => {
    if (tickers.length === 0) return;
    const picksMap = new Map<string, number>(
      [...(aionis.picks ?? []), ...(aionis.shorts ?? [])].map(
        (p) => [p.ticker, p.rank] as const,
      ),
    );
    const last = getLastSeenRanks();
    const deltas: Record<string, number | null> = {};
    const next: Record<string, number> = {};
    for (const { ticker } of tickers) {
      const cur = picksMap.get(ticker);
      if (cur != null) next[ticker] = cur;
      const prev = last[ticker];
      deltas[ticker] = prev != null && cur != null ? prev - cur : null; // rank improved => positive
    }
    setRankDeltas(deltas);
    saveCurrentRanks(next);
  }, [tickers]);

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
              {(() => {
                const d = rankDeltas[ticker];
                if (d == null || d === 0) return null;
                const up = d > 0;
                return (
                  <span
                    className={cn(
                      "inline-flex items-center gap-0.5 font-mono text-[10px] tabular-nums",
                      up ? "text-up" : "text-down",
                    )}
                    title={up ? `Rank improved by ${d}` : `Rank dropped by ${-d}`}
                  >
                    {up ? <TrendingUpIcon className="size-2.5" /> : <TrendingDownIcon className="size-2.5" />}
                    {up ? `↑${d}` : `↓${-d}`}
                  </span>
                );
              })()}
            </Link>
          );
        })}
      </div>
    </div>
  );
}
