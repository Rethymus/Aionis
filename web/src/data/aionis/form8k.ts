// Dedicated module — deliberately NOT merged into the barrel `aionis` object
// (stock-universe / lineage-graph precedent): the 8-K stream crossed the
// 100KB barrel rider ceiling at the 2026-11-03..05 growth-guard trip
// (form8k exporter cap 300 -> 600, 312 events, ~105KB). Only the events /
// executives / overview routes import it, so Turbopack keeps it in a
// form8k-pages-only chunk.
//
// Contract mirrors scripts/export_terminal_data.py::export_form8k.

import form8kJson from "./form8k.json";

export type Form8kEvent = {
  ticker: string;
  company: string;
  filing_date: string;
  form: string;
  // Legally mandated 8-K item numbers, e.g. ["2.01", "9.01"] — regex-extracted
  // from the primary document, sorted unique.
  items: string[];
  // ONE category per filing (rare-material-first precedence); "unclassified"
  // when items could not be extracted (counted, never guessed).
  category: string;
  doc_url: string;
};


export type Form8k = {
  status: string;
  as_of: string | null;
  window: { start: string; end: string };
  issuers: number;
  total: number;
  unclassified: number;
  by_category: Record<string, number>;
  events: Form8kEvent[];
  methodology: string;
  snapshot_ts?: string;
};
const form8k = form8kJson as Form8k;
export default form8k;
