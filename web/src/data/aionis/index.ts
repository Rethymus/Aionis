import metrics from "./metrics.json";
import picks from "./picks.json";
import shorts from "./shorts.json";
import evidence from "./evidence.json";
import powerFloor from "./power_floor.json";
import icMonthly from "./ic_monthly.json";
import sigmaSurvey from "./sigma_survey.json";
import bpsSweep from "./bps_sweep.json";

export type Pick = {
  rank: number;
  ticker: string;
  region: "us" | "cn";
  score: number;
  rank_change: number | null;
};

export type Evidence = {
  n: number;
  result: string;
  estimate: number;
  ci_lo: number | null;
  ci_hi: number | null;
  p: number | null;
  n_months: number;
  grade: "CV-proxy" | "chron./explor." | "explor." | "CONFIRMATORY";
};

export const aionis = {
  metrics: metrics as typeof metrics,
  picks: picks as Pick[],
  shorts: shorts as Pick[],
  evidence: evidence as Evidence[],
  powerFloor: powerFloor as typeof powerFloor,
  icMonthly: icMonthly as { month: string; us: number; cn: number; combined: number }[],
  sigmaSurvey: sigmaSurvey as typeof sigmaSurvey,
  bpsSweep: bpsSweep as { bps: number; net_sharpe: number; gross_sharpe: number; avg_turnover: number }[],
};
