"use client";

// SectorPeers (round 164): a compact horizontal strip of same-sector stocks
// on every /stock/[ticker] page — "one jump to discover sector peers".
// Data: stock_universe already carries `sector` per stock; we rank peers by
// frozen |score| descending (top 8, excluding the current ticker) and link
// each chip to its stock page. Renders nothing when no sector or no peers.

import Link from "next/link";
import { useMemo } from "react";
import { stockUniverse } from "@/data/aionis/stock-universe";
import { cn } from "@/lib/utils";

export function SectorPeers({ ticker }: { ticker: string }) {
  const peers = useMemo(() => {
    const self = stockUniverse.stocks.find((s) => s.ticker === ticker);
    if (!self?.sector) return [];
    return stockUniverse.stocks
      .filter((s) => s.sector === self.sector && s.ticker !== ticker)
      .sort((a, b) => Math.abs(b.score ?? 0) - Math.abs(a.score ?? 0))
      .slice(0, 8);
  }, [ticker]);

  if (peers.length === 0) return null;

  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {peers.map((p) => (
        <Link
          key={p.ticker}
          href={`/stock/${p.ticker}`}
          className={cn(
            "inline-flex items-center gap-1 rounded-lg border border-line bg-card px-2 py-1 text-xs transition-colors hover:border-faint",
          )}
          title={`${p.name} · ${p.sector}`}
        >
          <span className="font-mono font-medium">{p.ticker}</span>
          {p.score != null ? (
            <span
              className={cn(
                "font-mono text-[11px] tabular-nums",
                p.score >= 0 ? "text-up" : "text-down",
              )}
            >
              {p.score > 0 ? "+" : ""}
              {p.score.toFixed(2)}
            </span>
          ) : null}
        </Link>
      ))}
    </div>
  );
}
