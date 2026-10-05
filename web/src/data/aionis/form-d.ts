// Dedicated module — deliberately NOT merged into the barrel `aionis` object
// (round 195 barrel diet, same pattern as stock-universe.ts): the Form D
// rolling window (~176KB) rode the shared chunk every route loads; only the
// IPO view's private-fundraising lane consumes it.
//
// Contract mirrors scripts/export_terminal_data.py::export_form_d.

import formDJson from "./form_d.json";

export type FormDFiling = {
  company: string;
  // Almost always empty — Form D filers are private companies by definition
  // (the EDGAR display name carries no symbol); honest, never guessed.
  ticker: string;
  filed_date: string;
  // "D" (new notice) | "D/A" (amendment).
  form: string;
  // "new" | "amendment" — derived from the immutable form type.
  status: string;
  doc_url: string;
};

export type FormD = {
  status: string;
  as_of: string;
  window: { start: string; end: string };
  issuers: number;
  total: number;
  by_form: Record<string, number>;
  filings: FormDFiling[];
  methodology: string;
  snapshot_ts?: string;
};

export const formD = formDJson as FormD;
