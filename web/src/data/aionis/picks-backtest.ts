// Dedicated module — deliberately NOT merged into the barrel `aionis` object
// (round 198 barrel diet, same pattern as stock-universe.ts): the frozen
// picks backtest months (~149KB) rode the shared chunk every route loads;
// only the picks view consumes it.
//
// Contract mirrors scripts/export_terminal_data.py::export_picks_backtest.

import picksBacktestJson from "./picks_backtest.json";

export type BacktestPick = {
  ticker: string;
  name: string;
  score: number;
  realized_return: number;
  hit: boolean;
};

export type BacktestMonth = {
  month: string;
  region: "us" | "cn";
  picks: BacktestPick[];
  top_mean_return: number;
  base_mean_return: number;
  excess: number;
};

export type PicksBacktest = {
  methodology: string;
  months: BacktestMonth[];
  summary: {
    n_months: number;
    n_picks: number;
    hit_rate: number;
    avg_top_return: number;
    avg_base_return: number;
    avg_excess: number;
  };
  snapshot_ts?: string;
};

export const picksBacktest = picksBacktestJson as PicksBacktest;
