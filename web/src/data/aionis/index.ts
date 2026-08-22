// Explicit per-panel contracts — never `as typeof json`.
// Why: a daily refresh whose data collapses a JSON literal (e.g. every pick
// carrying bull_ratio: null) narrows the INFERRED type and breaks the Pages
// build at arbitrary use-sites (deploy 31869082383). These types mirror the
// export contracts in scripts/export_terminal_data.py, including its real
// nullability (fields that branch to None on empty/edge data are `| null`).
//
// The panels stay in ONE merged `aionis` object (deliberately): Turbopack's
// static export dedupes a single barrel module into one shared chunk, while
// named re-exports get DUPLICATED across per-page chunks (measured: every page
// +50-280KB with data copied into multiple chunks). Per-route data splitting
// would need webpack manualChunks surgery — out of scope for this lane.

import metricsJson from "./metrics.json";
import picksJson from "./picks.json";
import shortsJson from "./shorts.json";
import picksMetaJson from "./picks_meta.json";
import sectorBreakdownJson from "./sector_breakdown.json";
import picksBacktestJson from "./picks_backtest.json";
import marketContextJson from "./market_context.json";
import evidenceJson from "./evidence.json";
import powerFloorJson from "./power_floor.json";
import icMonthlyJson from "./ic_monthly.json";
import sigmaSurveyJson from "./sigma_survey.json";
import bpsSweepJson from "./bps_sweep.json";
import tacoJson from "./taco.json";
import redditJson from "./reddit.json";
import smartMoneyJson from "./smart_money.json";
import stakes13gJson from "./stakes_13g.json";
import pickConvictionJson from "./pick_conviction.json";
import form4Json from "./form4.json";
import cotJson from "./cot.json";
import modelHealthJson from "./model_health.json";
import calibrationReliabilityJson from "./calibration_reliability.json";
import themeSignalsJson from "./theme_signals.json";
import macroDriversJson from "./macro_drivers.json";
import themesJson from "./themes.json";
import ledgerAuditJson from "./ledger_audit.json";
import headlineProvenanceJson from "./headline_provenance.json";
import dataHealthJson from "./data_health.json";
import apiCatalogJson from "./api_catalog.json";
import form13fJson from "./form13f.json";
import form8kJson from "./form8k.json";
import ipoJson from "./ipo.json";
import politicianTradesJson from "./politician_trades.json";
import executivesJson from "./executives.json";

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

export type Short = Omit<Pick, "rank_change">;

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

export type Metrics = {
  combined_ic: number;
  p: number;
  n_months: number;
  ci_lo: number;
  ci_hi: number;
  verdict: string;
  jt_look1: string;
  h6: string;
  sesoi: number;
  latest_month: string;
  n_picks_total: number;
  // Present only on the live-ledger branch (absent on the committed-literals
  // CI fallback) — export_metrics.
  ledger_row?: number;
  config_sig_short?: string;
  snapshot_ts?: string;
};

export type PicksMeta = {
  latest_date: string;
  method: string;
  walk_forward: boolean;
  regions: { [region: string]: { latest_date: string; meta: CalibrationMeta } };
  disclaimer: string;
};

export type SectorRow = {
  sector: string;
  n_stocks: number;
  mean_score: number;
  mean_prob_up: number;
  regions: ("us" | "cn")[];
};

export type SectorBreakdown = {
  status: string;
  methodology: string;
  // ok branch
  latest_dates?: { [region: string]: string };
  n_sectors?: number;
  top_favored?: SectorRow[];
  least_favored?: SectorRow[];
  all_sectors?: SectorRow[];
  // awaiting_fetch branch writes `sectors: []` instead
  sectors?: SectorRow[];
  snapshot_ts?: string;
};

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

export type MarketEvent = {
  date: string;
  label: string;
  type: string;
  region?: string;
};

export type MarketContext = {
  methodology: string;
  start_label: string;
  vix_series: { month: string; vix: number }[];
  market_series: { month: string; ret: number; index: number }[];
  risk: {
    n_periods: number;
    annual_return: number;
    sharpe: number;
    sortino: number;
    max_drawdown: number;
    calmar: number;
    var_95: number;
    cvar_95: number;
    periods_per_year: number;
  };
  events: MarketEvent[];
  n_months: number;
  date_range: string[];
  snapshot_ts?: string;
};

export type PowerFloor = {
  sesoi: number;
  looks: {
    look: number;
    n: number;
    z: number;
    n_min_months: number;
    n_min_years: number;
    rci_level_pct: number;
  }[];
  sigma_observed_median: number;
  sigma_pure_noise_n462: number;
  n_min_at_pure_noise_look3_months: number;
  n_min_at_observed_look3_months: number;
  verdict: string;
  snapshot_ts?: string;
};

export type SigmaSurvey = {
  rows: {
    source: string;
    arm: string;
    sigma_observed: number;
    n_cross: number;
    sigma_pure_noise: number;
    excess_ratio: number;
  }[];
  summary: {
    excess_min: number;
    excess_median: number;
    excess_max: number;
    n_series: number;
  };
};

export type Taco = {
  methodology: string;
  vix_series: { month: string; vix: number }[];
  events: { date: string; label: string; type: string }[];
  climbdowns_count: number;
  escalations_count: number;
  latest_vix: number | null;
  latest_date: string | null;
  snapshot_ts?: string;
};

export type RedditPick = {
  ticker: string;
  mentions: number;
  sentiment: number;
  score_sum: number;
  bull_ratio: number | null;
};

export type SmartMoney = {
  methodology?: string;
  recent_filings: {
    filer: string;
    target: string;
    ticker: string;
    date: string;
    form: string;
    is_amendment: boolean;
    url?: string;
  }[];
  active_filers: { filer: string; count: number }[];
  total_filings: number;
  n_filers: number;
  latest_date: string | null;
  yearly: { year: number; filings: number }[];
};

export type Stakes13GFiling = {
  filer: string;
  target: string;
  // Offline backfill from the cached SEC company_tickers snapshot (a
  // CURRENT-snapshot display label, not as-of-filing); null = unresolved
  // (unlisted target / ambiguous accession group) — honest, never guessed.
  ticker: string | null;
  date: string;
  // SC 13G | SC 13G/A (immutable form type — one row per accession filing).
  form: string;
  doc_url: string;
};

export type Stakes13G = {
  status: string;
  as_of: string | null;
  window: { start: string; end: string };
  total: number;
  by_form: Record<string, number>;
  filings: Stakes13GFiling[];
  methodology: string;
  snapshot_ts?: string;
};

export type ConvictionPoint = {
  date: string;
  n: number;
  std: number;
  decile_spread: number;
  top_q: number;
  bot_q: number;
};

export type PickConviction = {
  methodology: string;
  series: ConvictionPoint[];
  latest: ConvictionPoint | null;
  conviction: string;
  trailing_std_mean: number | null;
};

export type Form4 = {
  status: string;
  methodology: string;
  recent: {
    filer: string;
    ticker: string;
    date: string;
    action: string;
    shares: number | null;
    price: number | null;
    /** EDGAR filing-index link (accession + reporting-owner CIK); "" / absent
     *  on pre-accession aggregates — rendered as "—", never a guessed URL. */
    doc_url?: string | null;
  }[];
  buys: number;
  sells: number;
  n_filers: number;
  top_insiders: { filer: string; count: number }[];
  window: string;
  n_issuers: number;
  yearly: { year: number; buys: number; sells: number }[];
  snapshot_ts?: string;
};

export type Cot = {
  status: string;
  methodology: string;
  markets: { name: string; net: number; z: number; long: number; short: number }[];
  composite: { mean_z: number; crowding: number; n: number };
  composite_series: { date: string; z: number }[];
  latest_date: string;
  snapshot_ts?: string;
};

export type ModelHealthRegion = {
  region: string;
  n_history: number;
  n_recent: number;
  recent_months: number;
  psi: number;
  ic_full: number;
  ic_recent: number;
  base_rate_full: number;
  base_rate_recent: number;
  regime: string;
};

export type ModelHealth = {
  recent_months: number;
  methodology: string;
  regions: { [region: string]: ModelHealthRegion };
  status: string;
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

export type ThemeSignals = {
  status: string;
  as_of_date?: string;
  groups: string[];
  methodology?: string;
  signals: {
    [signal: string]: {
      signal: string;
      polarity: string;
      direction: "bullish" | "bearish" | "neutral";
      strength: number;
      mean: number;
      n: number;
      group: string;
      latest_mean?: number;
      trailing_mean?: number;
      favored: { ticker: string; value: number; name?: string; sector?: string }[];
    };
  };
};

export type MacroDrivers = {
  status: string;
  series: {
    [key: string]: { month: string; value: number }[];
  };
  methodology?: string;
};

export type Theme = {
  key: string;
  status: string;
  as_of: string | null;
  headline: string;
  signals: { name: string; value: number | null }[];
  series: { month: string; value: number | null }[];
};

export type Themes = {
  status: string;
  as_of_date?: string;
  freshness?: { earliest: string; latest: string; mixed: boolean };
  methodology?: string;
  themes: Theme[];
  snapshot_ts?: string;
};

export type LedgerAuditEntry = {
  row: number;
  ts: string;
  event: string;
  phase: string;
  config_sig_short: string;
  verdict: string;
  metric: string;
  h6: boolean | null;
  frozen_before_result: boolean;
};

export type LedgerAudit = {
  entries: LedgerAuditEntry[];
  n_total_rows: number;
  n_claim_rows: number;
  identity_note: string;
  snapshot_ts?: string;
};

export type HeadlineProvenance = {
  status: string;
  ledger_row?: number;
  phase?: string;
  config_sig_short?: string;
  config_sig_source?: string;
  result_ts?: string;
  result_event?: string;
  freeze?: {
    ledger_row: number;
    ts: string;
    event: string;
    config_sig_short: string;
  } | null;
  headline?: {
    combined_ic: number | null;
    p_hac: number | null;
    ci_lo: number | null;
    ci_hi: number | null;
    n_months: number | null;
    jt_look1: string;
    h6_deterministic: boolean;
  };
  contract?: {
    freeze_before_result: boolean;
    note: string;
  };
  snapshot_ts?: string;
};

export type DataHealthPanel = {
  key: string;
  file: string;
  category: "daily" | "cadence" | "frozen";
  as_of: string | null;
  exported_at: string | null;
  present: boolean;
};

export type DataHealth = {
  status: string;
  panels: DataHealthPanel[];
  summary: {
    n_panels: number;
    n_frozen: number;
    n_daily: number;
    n_cadence: number;
  };
  // Field-level quality metrics on panels whose source has known gaps.
  source_health?: {
    smart_money: { ticker_null: number; n_recent: number; days_since_latest: number };
    // 13G passive stream: ticker/filer resolution is offline-heuristic; nulls
    // and placeholder filers are counted, never guessed.
    stakes_13g: {
      ticker_null: number;
      filer_unresolved: number;
      n_filings: number;
      days_since_latest: number;
    };
    reddit: { bull_ratio_null: number; n_picks: number };
    cot: { weeks_since_latest: number };
  };
  // Designed-but-not-built panels (xiaoyinsi x-status:planned imitation) —
  // an honest forward direction, not a commitment.
  planned?: { key: string; note: string }[];
  methodology: string;
  snapshot_ts?: string;
};

export type ApiCatalogEndpoint = {
  key: string;
  file: string;
  path: string;
  method: string;
  status: string;
  freshness: "daily" | "cadence" | "frozen" | "planned";
  as_of: string | null;
  license: string;
  source: string;
};

export type ApiCatalog = {
  status: string;
  base_note: string;
  endpoints: ApiCatalogEndpoint[];
  live_prices: {
    note: string;
    paths: { method: string; path: string }[];
    server: string;
  };
  methodology: string;
  snapshot_ts?: string;
};

export type Form13fHolding = {
  issuer: string;
  cusip: string;
  title: string;
  option: string;
  value: number;
  shares: number;
  pct: number;
  // Exact normalized-name match against the US stock universe; null when the
  // CUSIP has no ticker mapping (issuer renders as plain text).
  ticker: string | null;
};

export type Form13fChange = {
  issuer: string;
  cusip: string;
  title: string;
  option: string;
  direction: "new" | "increased" | "reduced" | "exited";
  // Share-count change in percent (+25.3 = +25.3% shares); null for new/exited.
  delta_pct: number | null;
  // Whole-USD value delta (cur − prev quarter, both sides kept by the frame
  // diff): full position value on new/exited; on increased/reduced the sign
  // may OPPOSE delta_pct (price drift). OPTIONAL only for the transition:
  // the committed JSON predates the key — it becomes always-present after
  // the next mainline re-export; consumers tolerate absence (`?? null`,
  // renders "—").
  delta_value?: number | null;
  ticker: string | null;
};

export type Form13fManager = {
  cik: string;
  name: string;
  zh_name: string | null;
  // Human-curated editorial tag from the fetch registry (value / growth /
  // activist / macro / quant / china_background / other) — display-only,
  // NOT a SEC data-source field (disclosed in the panel methodology).
  category: string;
  quarter: string;
  filed: string;
  n_positions: number;
  total_value: number;
  top10: Form13fHolding[];
  changes: Form13fChange[];
};

export type Form13f = {
  status: string;
  as_of: string | null;
  managers: Form13fManager[];
  ticker_coverage?: string;
  // Managers per category (honest counting at export time; "other" share is
  // allowed to be large — the tag is editorial, not a data-source field).
  category_counts?: Record<string, number>;
  methodology: string;
  snapshot_ts?: string;
};

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

export type FormIpoFiling = {
  company: string;
  // Parsed from the EDGAR display name where the filer carries a symbol;
  // "" for pre-symbol S-1 filers (honest empty, never guessed).
  ticker: string;
  filed_date: string;
  // S-1 | S-1/A | 424B4 (immutable form type — the status is derived from it).
  form: string;
  // filed (registration on file) | priced (statutory 424B4 final prospectus).
  status: "filed" | "priced";
  doc_url: string;
};

export type FormIpo = {
  status: string;
  as_of: string | null;
  window: { start: string; end: string };
  issuers: number;
  total: number;
  by_status: Record<string, number>;
  by_form: Record<string, number>;
  filings: FormIpoFiling[];
  methodology: string;
  snapshot_ts?: string;
};

export type PoliticianFiling = {
  member: string;
  office: string;
  filing_type: string;
  // As-filed FilingDate from the bulk FD.xml index (YYYY-MM-DD); null only
  // if the index row carried none.
  filing_date: string | null;
  filing_year: number;
  // From the house.gov current-member directory joined on district + last
  // name; null when the filer is a candidate/former member (office-only
  // match would misattribute the incumbent's party).
  party: string | null;
  doc_url: string;
};

export type PoliticianTopMember = {
  member: string;
  office: string;
  count: number;
};

export type PoliticianTrades = {
  status: string;
  // Latest as-filed FilingDate (bulk FD.xml carries real dates); null only
  // if no row carried one.
  as_of: string | null;
  latest_filing_year: number;
  window_years: number[];
  house: {
    total: number;
    members: number;
    filings: PoliticianFiling[];
    by_year: Record<string, number>;
    top_members: PoliticianTopMember[];
  };
  senate: { status: string; note: string };
  methodology: string;
  snapshot_ts?: string;
};

export type ExecutivesEvent = {
  company: string;
  ticker: string;
  filing_date: string;
  // Full legally mandated 8-K item list (["5.02", "9.01"]) — the row's
  // Item 5.02 membership comes from the form8k officer_changes category.
  items: string[];
  doc_url: string;
};

export type Executives = {
  status: string;
  // Latest officer_changes filing date in the subset; null on an honest
  // empty window (no Item 5.02 filings yet).
  as_of: string | null;
  total: number;
  issuers: number;
  window: { start: string | null; end: string | null };
  events: ExecutivesEvent[];
  // company name -> filing count (honest counting; sums to total).
  by_company: Record<string, number>;
  methodology: string;
  snapshot_ts?: string;
};

export const aionis = {
  metrics: metricsJson as Metrics,
  picks: picksJson as Pick[],
  shorts: shortsJson as Short[],
  picksMeta: picksMetaJson as PicksMeta,
  sectorBreakdown: sectorBreakdownJson as SectorBreakdown,
  picksBacktest: picksBacktestJson as PicksBacktest,
  marketContext: marketContextJson as MarketContext,
  evidence: evidenceJson as Evidence[],
  powerFloor: powerFloorJson as PowerFloor,
  icMonthly: icMonthlyJson as {
    month: string;
    us: number;
    cn: number;
    combined: number;
  }[],
  sigmaSurvey: sigmaSurveyJson as SigmaSurvey,
  bpsSweep: bpsSweepJson as {
    bps: number;
    net_sharpe: number;
    gross_sharpe: number;
    avg_turnover: number;
  }[],
  taco: tacoJson as Taco,
  reddit: { ...redditJson, picks: redditJson.picks as RedditPick[] },
  smartMoney: smartMoneyJson as SmartMoney,
  stakes13g: stakes13gJson as Stakes13G,
  pickConviction: pickConvictionJson as PickConviction,
  form4: form4Json as Form4,
  cot: cotJson as Cot,
  modelHealth: modelHealthJson as ModelHealth,
  calibrationReliability: calibrationReliabilityJson as CalibrationReliability,
  themeSignals: themeSignalsJson as ThemeSignals,
  macroDrivers: macroDriversJson as MacroDrivers,
  themes: themesJson as Themes,
  ledgerAudit: ledgerAuditJson as LedgerAudit,
  headlineProvenance: headlineProvenanceJson as HeadlineProvenance,
  dataHealth: dataHealthJson as DataHealth,
  apiCatalog: apiCatalogJson as ApiCatalog,
  form13f: form13fJson as Form13f,
  form8k: form8kJson as Form8k,
  ipo: ipoJson as FormIpo,
  politicianTrades: politicianTradesJson as PoliticianTrades,
  executives: executivesJson as Executives,
};
