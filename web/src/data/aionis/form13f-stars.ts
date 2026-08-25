// Home star-investors digest — the ONLY consumer of form13f-stars.json.
// The full 13F book (~650KB) stays in the dedicated form13f.ts module loaded
// by /institutions + /manager; the landing page pays ~2KB for this digest
// instead (derived at export time from the committed panel — see
// scripts/export_terminal_data.py::export_form13f_stars).
import json from "./form13f-stars.json";

export type Form13fStar = {
  cik: string;
  name: string;
  zh_name: string | null;
  quarter: string | null;
  total_value: number | null;
  top_issuer: string | null;
  top_ticker: string | null;
};

export type Form13fStars = {
  status: string;
  as_of: string | null;
  n_managers: number;
  stars: Form13fStar[];
  methodology: string;
  snapshot_ts: string;
};

export const form13fStars = json as Form13fStars;
