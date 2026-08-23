// Dedicated module — deliberately NOT merged into the barrel `aionis` object,
// mirroring the form13f / stock-universe precedents. The full-year filer
// directory (~8-9k rows) pushes the panel toward ~1MB; keeping it out of
// index.ts keeps the shared data chunk every page loads lean. Only /filers
// imports this, so Turbopack puts it in a filers-only chunk.
//
// Contract mirrors scripts/export_terminal_data.py::export_form13f_dir.

import filers13fJson from "./filers13f.json";

export type Filer13fRow = {
  // Zero-padded 10-digit CIK (the EDGAR browse key).
  cik: string;
  name: string;
  // 13F-HR count in the window (amendments counted separately).
  n_filings: number;
  n_amendments: number;
  latest_filed: string;
};

export type Filers13f = {
  status: string;
  as_of: string | null;
  window: { start: string; end: string };
  n_filers: number;
  n_with_amendments: number;
  total_filings: number;
  filers: Filer13fRow[];
  methodology: string;
  snapshot_ts?: string;
};

export const filers13f = filers13fJson as Filers13f;
