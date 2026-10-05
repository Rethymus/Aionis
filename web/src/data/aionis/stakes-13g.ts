// Dedicated module — deliberately NOT merged into the barrel `aionis` object
// (round 198 barrel diet, same pattern as stock-universe.ts): the SC 13G
// stream (~147KB) rode the shared chunk every route loads; the stakes /
// smart-money / overview views consume it.
//
// Contract mirrors scripts/export_terminal_data.py::export_stakes_13g.

import stakes13gJson from "./stakes_13g.json";

export type StakesPct = {
  pct_now?: number | null;
  // Previous percent — /A amendments only ("previous X%"-style narrative).
  pct_prev?: number | null;
  // DERIVED from pct_now ONLY: "exited" (parsed 0) | "below_5" (parsed <5) |
  // null. No parsed value → no status. Active/passive is the form type.
  pct_status?: "exited" | "below_5" | null;
};

export type Stakes13GFiling = {
  filer: string;
  target: string;
  // Offline backfill from the cached SEC company_tickers snapshot (a
  // CURRENT-snapshot display label, not as-of-filing); null = unresolved
  // (unlisted target / ambiguous accession group) — honest, never guessed.
  ticker: string | null;
  date: string;
  // SC 13G | SC 13G/A (immutable form type — one row per accession filing).
  form: string;
  doc_url: string;
} & StakesPct;

export type Stakes13G = {
  status: string;
  as_of: string | null;
  window: { start: string; end: string };
  total: number;
  by_form: Record<string, number>;
  filings: Stakes13GFiling[];
  methodology: string;
  snapshot_ts?: string;
};

export const stakes13g = stakes13gJson as Stakes13G;
