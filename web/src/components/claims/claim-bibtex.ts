"use client";

// Shared claim metadata + deterministic "cite this null" BibTeX generation.
// Numbers come bit-exact from the committed evidence_matrix panel; the
// project-level citation mirrors CITATION.cff at the repo root (a python
// contract test, tests/test_citation_mirror.py, pins the mirror).

import { aionis } from "@/data/aionis";

export const CLAIM_KEYS = ["B", "C", "E1", "D", "track_c"] as const;
export type ClaimKey = (typeof CLAIM_KEYS)[number];

export const CLAIM_STATEMENTS: Record<string, string> = {
  B: "fundamental timing (filed-date PIT vs period-end+lag)",
  C: "world-state surprise bundle (CPI/NFP/VIX/earnings)",
  D: "relationship bundle (SIC peer momentum + 13D events)",
  E1: "cross-firm shock propagation beyond own shocks",
  track_c: "dual-region joint chronological confirmatory OOS (S&P 500 + CSI 300)",
};

// Mirrors CITATION.cff (repo root) — pinned by tests/test_citation_mirror.py.
export const PROJECT_CITATION = {
  authors: "The Aionis Authors",
  title:
    "Aionis: a falsifiable, anti-leakage quantitative-finance research harness",
  version: "0.1.0",
  dateReleased: "2026-09-01",
  repository: "https://github.com/Rethymus/Aionis",
  url: "https://rethymus.github.io/Aionis/",
  license: "PolyForm-Noncommercial-1.0.0",
} as const;

const REPO = "https://github.com/Rethymus/Aionis";

function _bibEscape(s: string): string {
  return s.replace(/([&%$#_{}])/g, "\\$1");
}

export function claimBibtex(key: string): string {
  const c = aionis.evidenceMatrix.claims[key];
  const stmt = CLAIM_STATEMENTS[key] ?? key;
  const estimate = c.mean_diff !== undefined ? c.mean_diff : c.combined_ic;
  const ci = `[${c.ci_lo?.toFixed(4)}, ${c.ci_hi?.toFixed(4)}]`;
  const p = c.dm_p_mbb ?? c.p_hac;
  const label = key === "track_c" ? "track-c" : `phase-${key.toLowerCase()}`;
  const noteBits = [
    `pre-registered two-tailed claim`,
    `ledger row \\#${c.ledger_row}`,
    c.results_sig ? `config sha ${c.results_sig.slice(0, 16)}` : null,
    `differential ${estimate?.toFixed(4)}, 95\\% CI ${ci}`,
    p !== undefined && p !== null ? `p ${Number(p).toFixed(3)}` : null,
    `verdict NULL (CI brackets zero)`,
  ].filter(Boolean);
  return [
    `@misc{aionis-${label}-null,`,
    `  author       = {{${PROJECT_CITATION.authors}}},`,
    `  title        = {Aionis ${_bibEscape(key === "track_c" ? "Track C" : `Phase ${key}`)} claim: no incremental predictability from ${_bibEscape(stmt)} (null result)},`,
    `  year         = {2026},`,
    `  month        = ${c.kind === "confirmatory_oos" ? "aug" : "jul"},`,
    `  howpublished = {\\url{${REPO}}},`,
    `  note         = {${noteBits.join("; ")}}`,
    `}`,
  ].join("\n");
}

export function projectBibtex(): string {
  return [
    `@misc{aionis-research-harness,`,
    `  author       = {{${PROJECT_CITATION.authors}}},`,
    `  title        = {${_bibEscape(PROJECT_CITATION.title)}},`,
    `  year         = {${PROJECT_CITATION.dateReleased.slice(0, 4)}},`,
    `  howpublished = {\\url{${PROJECT_CITATION.repository}}},`,
    `  url          = {${PROJECT_CITATION.url}},`,
    `  version      = {${PROJECT_CITATION.version}},`,
    `  note         = {License: ${PROJECT_CITATION.license}. Four pre-registered incremental-information claims and the first chronological confirmatory OOS all returned NULL with tight CIs — the intended, registered outcome. See docs/RESULTS.md.}`,
    `}`,
  ].join("\n");
}
