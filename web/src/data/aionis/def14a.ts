// Dedicated module — deliberately NOT merged into the barrel `aionis` object
// (round 196 barrel diet, same pattern as stock-universe.ts): the DEF 14A
// proxy window (~174KB) rode the shared chunk every route loads; only the
// executives view consumes it.
//
// Contract mirrors scripts/export_terminal_data.py::export_def14a.

import def14aJson from "./def14a.json";

export type Def14aFiling = {
  company: string;
  // Empty for ~25% of filers (no symbol in the EDGAR display name) —
  // honest, never guessed.
  ticker: string;
  filed_date: string;
  // "DEF 14A" (new definitive proxy). The "DEF 14A/A" amendment arm exists
  // in the exporter as defense-in-depth; no such row today (amendments are
  // filed as DEFA14A, out of scope).
  form: string;
  // "new" | "amendment" — derived from the immutable form type.
  status: string;
  doc_url: string;
};

export type Def14a = {
  status: string;
  as_of: string;
  window: { start: string; end: string };
  issuers: number;
  total: number;
  by_form: Record<string, number>;
  filings: Def14aFiling[];
  methodology: string;
  snapshot_ts?: string;
};

export const def14a = def14aJson as Def14a;
