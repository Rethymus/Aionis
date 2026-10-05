// Dedicated module — deliberately NOT merged into the barrel `aionis` object
// (round 193 barrel diet, same pattern as stock-universe.ts): the House PTR
// filing index (~273KB) rode the shared chunk every route loads; only the
// congress page consumes it.
//
// Contract mirrors scripts/export_terminal_data.py::export_politician_trades.

import politicianTradesJson from "./politician_trades.json";

export type PoliticianFiling = {
  member: string;
  office: string;
  filing_type: string;
  // As-filed FilingDate from the bulk FD.xml index (YYYY-MM-DD); null only
  // if the index row carried none.
  filing_date: string | null;
  filing_year: number;
  // From the house.gov current-member directory joined on district + last
  // name; null when the filer is a candidate/former member (office-only
  // match would misattribute the incumbent's party).
  party: string | null;
  doc_url: string;
};

export type PoliticianTopMember = {
  member: string;
  office: string;
  count: number;
};

export type PoliticianTrades = {
  status: string;
  // Latest as-filed FilingDate (bulk FD.xml carries real dates); null only
  // if no row carried one.
  as_of: string | null;
  latest_filing_year: number;
  window_years: number[];
  house: {
    total: number;
    members: number;
    filings: PoliticianFiling[];
    by_year: Record<string, number>;
    top_members: PoliticianTopMember[];
  };
  senate: { status: string; note: string };
  methodology: string;
  snapshot_ts?: string;
};

export const politicianTrades = politicianTradesJson as PoliticianTrades;
