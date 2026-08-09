import metrics from "./metrics.json";
import picks from "./picks.json";
import shorts from "./shorts.json";
import picksMeta from "./picks_meta.json";
import sectorBreakdown from "./sector_breakdown.json";
import picksBacktest from "./picks_backtest.json";
import marketContext from "./market_context.json";
import evidence from "./evidence.json";
import powerFloor from "./power_floor.json";
import icMonthly from "./ic_monthly.json";
import sigmaSurvey from "./sigma_survey.json";
import bpsSweep from "./bps_sweep.json";
import taco from "./taco.json";
import reddit from "./reddit.json";
import smartMoney from "./smart_money.json";
import pickConviction from "./pick_conviction.json";
import form4 from "./form4.json";
import cot from "./cot.json";
import modelHealth from "./model_health.json";
import calibrationReliability from "./calibration_reliability.json";
import themes from "./themes.json";

export type Pick = {
  rank: number;
  ticker: string;
  region: "us" | "cn";
  name: string | "";
  sector: string | "";
  score: number;
  prob_up: number;
  rank_change: number | null;
};

export type CalibrationMeta = {
  region: string;
  n_pairs: number;
  base_rate: number;
  ece: number;
  brier: number;
  score_min: number;
  score_max: number;
  prob_min: number;
  prob_max: number;
  method: "platt" | "isotonic";
  walk_forward: boolean;
};

export type SectorRow = {
  sector: string;
  n_stocks: number;
  mean_score: number;
  mean_prob_up: number;
  regions: ("us" | "cn")[];
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

export type CalibrationReliability = {
  status: string;
  method?: string;
  walk_forward?: boolean;
  min_train_months?: number;
  methodology?: string;
  regions: {
    [region: string]: {
      n_months: number;
      series: {
        month: string;
        n_train_pairs: number;
        n_pred: number;
        ece_oos: number;
        base_rate: number;
        prob_min: number;
        prob_max: number;
      }[];
      pooled_ece: number;
      pooled_reliability: {
        bin_lo: number;
        bin_hi: number;
        pred_mean: number | null;
        emp_freq: number | null;
        n: number;
      }[];
    };
  };
};

export const aionis = {
  metrics: metrics as typeof metrics,
  picks: picks as Pick[],
  shorts: shorts as Pick[],
  picksMeta: picksMeta as typeof picksMeta,
  sectorBreakdown: sectorBreakdown as typeof sectorBreakdown,
  picksBacktest: picksBacktest as typeof picksBacktest,
  marketContext: marketContext as typeof marketContext,
  evidence: evidence as Evidence[],
  powerFloor: powerFloor as typeof powerFloor,
  icMonthly: icMonthly as { month: string; us: number; cn: number; combined: number }[],
  sigmaSurvey: sigmaSurvey as typeof sigmaSurvey,
  bpsSweep: bpsSweep as { bps: number; net_sharpe: number; gross_sharpe: number; avg_turnover: number }[],
  taco: taco as typeof taco,
  reddit: reddit as typeof reddit,
  smartMoney: smartMoney as typeof smartMoney,
  pickConviction: pickConviction as typeof pickConviction,
  form4: form4 as typeof form4,
  cot: cot as typeof cot,
  modelHealth: modelHealth as typeof modelHealth,
  calibrationReliability: calibrationReliability as CalibrationReliability,
  themes: themes as typeof themes,
};
