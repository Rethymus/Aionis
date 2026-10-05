// Dedicated module — deliberately NOT merged into the barrel `aionis` object.
// The House PTR transaction stream is the heaviest panel still riding the
// barrel (~1.3MB, thousands of parsed PDF rows); every route — even 404 —
// was paying for it in the shared data chunk (found in the round-192
// site-wide weight profile). Only congress / overview / stock views consume
// it, so Turbopack can now put it in a those-pages-only chunk.
//
// Contract mirrors scripts/export_terminal_data.py::export_politician_trades_tx.

import politicianTradesTxJson from "./politician_trades_tx.json";

export type PoliticianTx = {
  member: string;
  // house.gov directory join (district + last name); null for
  // candidates/former members.
  party: string | null;
  office: string;
  // Ticker as filed in the PDF; "" when the PDF carries none (bonds etc.).
  ticker: string;
  asset: string;
  // PTR asset-class code as bracketed in the PDF ("ST" = stock).
  type: string;
  direction: "buy" | "sell_partial" | "sell_full";
  // Statutory disclosure band text ("$15,001 - $50,000" / "$50,000,001+").
  amount_range: string;
  transaction_date: string;
  filing_date: string | null;
  // filing - transacted, whole days (STOCK Act clock; >45 = late).
  days_late: number | null;
  doc_url: string;
};

export type PoliticianTradesTx = {
  status: string;
  as_of: string | null;
  year: number;
  total: number;
  n_members: number;
  n_tickered: number;
  by_party: Record<string, {
    n_trades: number;
    n_buy: number;
    n_sell_partial: number;
    n_sell_full: number;
  }>;
  late_filings: number;
  party_coverage: string;
  transactions: PoliticianTx[];
  parse: {
    filings_total: number;
    filings_processed: number;
    fetch_errors: number;
    no_text_pdfs: number;
    row_candidates: number;
    rows_parsed: number;
    rows_exchanged: number;
    parse_failures: number;
    complete: boolean;
  };
  senate: { status: string; note: string };
  methodology: string;
  snapshot_ts?: string;
};

export const politicianTradesTx = politicianTradesTxJson as PoliticianTradesTx;
