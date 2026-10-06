// Dedicated module — deliberately NOT merged into the barrel `aionis` object.
// The universe carries ~1,421 per-stock rows with trailing score series
// (~550KB compact); keeping it out of index.ts keeps the shared data chunk
// every page loads lean (the barrel lesson in index.ts). Only /stock/[ticker]
// pages import this, so Turbopack puts it in a stock-pages-only chunk.
//
// Contract mirrors scripts/export_terminal_data.py::export_stock_universe.

import stockUniverseJson from "./stock_universe.json";

export type StockRow = {
  ticker: string;
  region: "us" | "cn";
  name: string | "";
  sector: string | "";
  score: number;
  prob_up: number;
  rank: number;
  n_region: number;
  rank_change: number | null;
  // Aligned to `months` (shared union grid); null = month outside this
  // region's calendar or ticker absent that month.
  scores: (number | null)[];
  smart_money_n: number | null;
  smart_money_latest: string | null;
  form4_n: number | null;
  form4_latest: string | null;
  reddit_mentions: number | null;
  // Round 205: pre-aggregated PTR corroboration — count + latest + a newest
  // ≤8-row sample with exactly the card-rendered fields (the full stream
  // stays on /congress; stock pages no longer load the ~1MB dedicated module).
  politician_n: number | null;
  politician_latest: string | null;
  politician_sample: {
    member: string;
    party: string | null;
    direction: "buy" | "sell_partial" | "sell_full";
    amount_range: string;
    transaction_date: string;
    days_late: number | null;
    doc_url: string;
  }[] | null;
};

export type StockUniverse = {
  status: string;
  as_of: { [region: string]: string };
  n_stocks: number;
  months: string[];
  // PTR panel year the corroboration sample derives from (round 205).
  politician_year: number | null;
  stocks: StockRow[];
  methodology: string;
  snapshot_ts?: string;
};

export const stockUniverse = stockUniverseJson as StockUniverse;
