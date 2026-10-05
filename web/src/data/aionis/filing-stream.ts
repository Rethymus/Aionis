// Dedicated module — deliberately NOT merged into the barrel `aionis` object
// (round 194 barrel diet, same pattern as stock-universe.ts): the unified
// filing stream (~249KB visible + deep cuts) rode the shared chunk every
// route loads; only annual / quarterly / events / filings-deadline views
// consume it.
//
// Contract mirrors scripts/export_terminal_data.py::export_filing_stream.

import filingStreamJson from "./filing_stream.json";

export type FilingStreamRow = {
  // Source form type: 8-K(/A) / 10-K(/A) / 10-Q(/A) / S-1(/A) / 4(/A) /
  // D(/A) / SC 13D(/A) / SC 13G(/A).
  form: string;
  // Company, the reporting person on Form 4, or "FILER → TARGET" on stakes.
  who: string;
  ticker: string;
  filed_date: string;
  doc_url: string;
};

export type FilingStream = {
  status: string;
  as_of: string;
  window: { start: string; end: string };
  // Full direct-query window vs the 800-newest visible cap.
  total_merged: number;
  n_visible: number;
  by_form: Record<string, number>;
  filings: FilingStreamRow[];
  // 10-K(/A) deep cut for /annual — the 800-newest cap squeezes periodic
  // reports out of the visible stream in filing season, so the family rides
  // its OWN newest-first slice (cap 400) from the same parquet.
  annual_filings: FilingStreamRow[];
  // 10-Q(/A) deep cut for /quarterly — same contract as annual_filings.
  quarterly_filings: FilingStreamRow[];
  // Full-window counts for the two deep-cut families (NOT the capped visible
  // length — the KPI shows the window, not the payload cap).
  annual_total: number;
  quarterly_total: number;
  methodology: string;
  snapshot_ts?: string;
};

export const filingStream = filingStreamJson as FilingStream;
