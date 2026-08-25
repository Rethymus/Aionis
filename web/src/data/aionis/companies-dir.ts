// Dedicated module — deliberately NOT merged into the barrel `aionis` object
// (the stock-universe precedent): the full ~10.4k-row US directory would
// bloat the shared chunk every page loads. Only /companies imports this.
//
// Contract mirrors scripts/export_terminal_data.py::export_companies_dir.

import companiesDirJson from "./companies_dir.json";

export type CompaniesDirRow = {
  ticker: string;
  name: string;
};

export type CompaniesDir = {
  status: string;
  n: number;
  source: string;
  companies: CompaniesDirRow[];
};

export const companiesDir = companiesDirJson as CompaniesDir;
