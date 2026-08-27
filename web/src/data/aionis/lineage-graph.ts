// Dedicated module — deliberately NOT merged into the barrel `aionis` object,
// mirroring the form13f / stock-universe precedent. The force-camp graph is a
// ~410KB JSON (146 verbatim-labelled nodes + 772 edges, each carrying up to 8
// shared-detail items); merging it into index.ts would put that weight into
// the shared data chunk every page loads, while named re-exports get
// DUPLICATED across per-page chunks (the deploy-31869082383 lesson). Only the
// /(dashboard)/force-camp route imports it, so Turbopack keeps it in a single
// force-camp chunk.
//
// Contract mirrors scripts/export_terminal_data.py::export_lineage_graph.
// Semantics: every edge is a pairwise projection over as-filed SEC disclosure
// facts; co_hold/co_board/co_target are factual coincidences of separately
// filed statements — NEVER a coordination or consortium claim. Missing values
// render "—" client-side; nothing here invents data.

import lineageJson from "./lineage_graph.json";

export type LineageLane = "13f" | "def14a" | "13dg";
export type LineageNodeType = "institution" | "person" | "staker";
export type LineageEdgeType = "co_hold" | "co_board" | "co_target";

export type LineageNode = {
  // "i:<cik>" | "p:<norm-name>" | "s:<norm-name>"
  id: string;
  type: LineageNodeType;
  label: string;
  zh_label: string | null;
  lanes: LineageLane[];
  cik: string | null;
  manager_routable: boolean;
  degree: { co_hold: number; co_board: number; co_target: number };
};

/** Three shapes by edge type (pinned by the export contract). */
export type LineageSharedItem =
  | { k: string; tk: string | null; issuer: string } // co_hold
  | { company: string; tk: string | null } // co_board
  | { target: string; tk: string | null; forms: string }; // co_target

export type LineageEdge = {
  a: string;
  b: string;
  type: LineageEdgeType;
  /** Positive integer count == shared.length when untruncated. */
  w: number;
  shared: LineageSharedItem[];
  truncated: boolean;
};

export type LineageBridge = {
  tk: string;
  name: string | null;
  in: LineageLane[];
  counts: { managers: number; persons: number; stakers: number };
  /** Export-time gate: only universe tickers may ever emit a /stock link. */
  stock_routable: boolean;
};

export type LineageGraph = {
  status: string;
  as_of: string | null;
  source_panels: string[];
  n_nodes: number;
  n_edges: number;
  nodes: LineageNode[];
  edges: LineageEdge[];
  bridges: LineageBridge[];
  components: { n: number; largest: number };
  windows: {
    form13f_quarter: string;
    stakes_visible_dates: { start: string | null; end: string | null };
    smart_money_visible_dates: { start: string | null; end: string | null };
  };
  coverage: {
    "13f": { basis: string; full_books_larger: boolean; isolated_managers: number };
    def14a: { basis: string; same_name_merges_possible: boolean };
    "13dg": { basis: string; joint_filing_members_not_decomposed: boolean };
  };
  methodology: string;
  snapshot_ts?: string;
};

export const lineageGraph = lineageJson as LineageGraph;
