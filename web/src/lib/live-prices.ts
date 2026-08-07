/**
 * Live price overlay for the fintech terminal.
 *
 * Fetches real-time prices from the Aionis Cloudflare Worker (display-only).
 * Gracefully degrades: if WORKER_URL is empty or fetch fails, returns empty
 * prices and the terminal renders score-only (no visual breakage).
 *
 * Anti-leakage boundary: prices from this hook are DISPLAY ONLY. They must
 * never be consumed by any research module. See CLAUDE.md guardrail.
 *
 * Deploy the Worker first: see workers/prices/README.md, then set WORKER_URL.
 */

import { useEffect, useState } from "react";

// ─── Set this after deploying the Worker ───────────────────────
// Example: "https://aionis-prices.your-subdomain.workers.dev"
// Leave empty to disable live prices (terminal renders score-only).
const WORKER_URL = "https://api.aionis-prices.workers.dev";
// ───────────────────────────────────────────────────────────────

export type LivePrice = {
  price: number | null;
  change_pct: number | null;
  name?: string;
  as_of?: string;
};

export type PriceStatus = "idle" | "loading" | "ok" | "error" | "disabled";

export type PriceMap = Record<string, LivePrice>;

/**
 * Fetch live prices for a list of tickers. Splits US / CN and fetches in
 * parallel. Re-fetches every 60s while the component is mounted (for
 * real-time feel during market hours).
 *
 * Usage:
 *   const { prices, status } = useLivePrices(picks);
 *   // prices["COIN"]?.change_pct → +2.34
 */
export function useLivePrices(
  tickers: { ticker: string; region: string }[],
): { prices: PriceMap; status: PriceStatus } {
  const [prices, setPrices] = useState<PriceMap>({});
  const [status, setStatus] = useState<PriceStatus>(
    WORKER_URL ? "loading" : "disabled",
  );

  useEffect(() => {
    if (!WORKER_URL) {
      setStatus("disabled");
      return;
    }

    let cancelled = false;

    async function fetchPrices() {
      const us = tickers
        .filter((t) => t.region === "us")
        .map((t) => t.ticker)
        .join(",");
      const cn = tickers
        .filter((t) => t.region === "cn")
        .map((t) => t.ticker)
        .join(",");

      const fetches: Promise<Response>[] = [];
      if (us) fetches.push(fetch(`${WORKER_URL}/api/prices/us?tickers=${us}`));
      if (cn) fetches.push(fetch(`${WORKER_URL}/api/prices/cn?tickers=${cn}`));

      if (fetches.length === 0) {
        setStatus("idle");
        return;
      }

      try {
        const responses = await Promise.all(fetches);
        const bodies = await Promise.all(responses.map((r) => r.json()));
        const merged: PriceMap = Object.assign({}, ...bodies);
        if (!cancelled) {
          setPrices(merged);
          setStatus("ok");
        }
      } catch {
        if (!cancelled) setStatus("error");
      }
    }

    fetchPrices();
    // Re-fetch every 60s for near-real-time during market hours.
    const interval = setInterval(fetchPrices, 60_000);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [tickers]);

  return { prices, status };
}
