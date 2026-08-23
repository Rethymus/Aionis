// Dedicated module — deliberately NOT merged into the barrel `aionis` object,
// mirroring the stock-universe precedent. The visible books (up to 50
// positions × 40 managers + changes) push the panel to ~650KB; keeping it out
// of index.ts keeps the shared data chunk every page loads lean. Only
// /institutions, /manager/[cik] and /stock/[ticker] (holders reverse-lookup)
// import this, so Turbopack puts it in a institutions/manager/stock chunk.
//
// Contract mirrors scripts/export_terminal_data.py::export_form13f.

import form13fJson from "./form13f.json";

export type Form13fHolding = {
  issuer: string;
  cusip: string;
  title: string;
  option: string;
  value: number;
  shares: number;
  pct: number;
  // Exact normalized-name match against the US stock universe; null when the
  // CUSIP has no ticker mapping (issuer renders as plain text).
  ticker: string | null;
};

export type Form13fChange = {
  issuer: string;
  cusip: string;
  title: string;
  option: string;
  direction: "new" | "increased" | "reduced" | "exited";
  // Share-count change in percent (+25.3 = +25.3% shares); null for new/exited.
  delta_pct: number | null;
  // Whole-USD value delta (cur − prev, both sides kept by the frame diff):
  // full position value for new/exited, plain difference otherwise (sign may
  // oppose delta_pct on price drift). Optional until the first re-export that
  // carries it.
  delta_value?: number | null;
  ticker: string | null;
};

export type Form13fManager = {
  cik: string;
  name: string;
  zh_name: string | null;
  // Human-curated editorial tag from the fetch registry (value / growth /
  // activist / macro / quant / china_background / other) — display-only,
  // NOT a SEC data-source field (disclosed in the panel methodology).
  category: string;
  quarter: string;
  filed: string;
  n_positions: number;
  total_value: number;
  // Up to 50 latest-quarter positions (the whole book for most filers).
  positions: Form13fHolding[];
  changes: Form13fChange[];
};

export type Form13f = {
  status: string;
  as_of: string | null;
  managers: Form13fManager[];
  ticker_coverage?: string;
  // Managers per category (honest counting at export time; "other" share is
  // allowed to be large — the tag is editorial, not a data-source field).
  category_counts?: Record<string, number>;
  methodology: string;
  snapshot_ts?: string;
};

export const form13f = form13fJson as Form13f;
