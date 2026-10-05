// Dedicated module — deliberately NOT merged into the barrel `aionis` object
// (round 193 barrel diet, same pattern as stock-universe.ts): the S-1/424B4
// IPO window (~379KB) rode the shared chunk every route loads; only the IPO
// page and the overview consume it.
//
// Contract mirrors scripts/export_terminal_data.py::export_form_ipo.

import formIpoJson from "./ipo.json";

export type FormIpoFiling = {
  company: string;
  // Parsed from the EDGAR display name where the filer carries a symbol;
  // "" for pre-symbol S-1 filers (honest empty, never guessed).
  ticker: string;
  filed_date: string;
  // S-1 | S-1/A | 424B4 (immutable form type — the status is derived from it).
  form: string;
  // filed (registration on file) | priced (statutory 424B4 final prospectus).
  status: "filed" | "priced";
  doc_url: string;
  // Cover-page offer price of the 424B4 final prospectus — bounded second-
  // stage parse (newest ≤80 priced filings only, exact-tier parses only).
  // null everywhere else: older filings beyond the request budget,
  // low-confidence / no-match extractions, unpriced S-1 rows (honest blank,
  // never guessed). TASK-DISP-H3.
  offer_price: number | null;
};

export type FormIpoOfferPriceMeta = {
  target_cap_docs: number;
  priced_filings: number;
  newest_targeted: number;
  attempted: number;
  fetch_failed: number;
  fetch_errors: Record<string, number>;
  // Graded-extraction tiers (aionis.ingest.form_ipo_price): only exact ships
  // a value; low/none are counted but stay honest nulls.
  confidence: { exact: number; low: number; none: number };
  coverage_pct_of_priced: number;
  requests: {
    task_budget: number;
    cumulative_walk: number;
    walk_cap: number | null;
  };
  target_as_of: string | null;
};

export type FormIpo = {
  status: string;
  as_of: string | null;
  window: { start: string; end: string };
  issuers: number;
  total: number;
  by_status: Record<string, number>;
  by_form: Record<string, number>;
  // Count of rows carrying an exact-tier offer_price (≤ by_status.priced ≤
  // total); offer_price_meta carries the bounded-walk disclosure (target cap,
  // confidence tiers, request ledger). TASK-DISP-H3.
  offer_price_parsed: number;
  offer_price_meta: FormIpoOfferPriceMeta;
  filings: FormIpoFiling[];
  methodology: string;
  snapshot_ts?: string;
};

export const formIpo = formIpoJson as FormIpo;
