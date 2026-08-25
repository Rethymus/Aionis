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
import freightTacoJson from "./freight_taco.json";
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
import koreaProxyJson from "./korea_proxy.json";
import themesJson from "./themes.json";
import ledgerAuditJson from "./ledger_audit.json";
import headlineProvenanceJson from "./headline_provenance.json";
import dataHealthJson from "./data_health.json";
import apiCatalogJson from "./api_catalog.json";
import form8kJson from "./form8k.json";
import ipoJson from "./ipo.json";
import politicianTradesJson from "./politician_trades.json";
import politicianTradesTxJson from "./politician_trades_tx.json";
import partyIndexJson from "./party_index.json";
import arkJson from "./ark.json";
import themeEtfsJson from "./theme_etfs.json";
import redditTrendingJson from "./reddit_trending.json";
import formDJson from "./form_d.json";
import def14aJson from "./def14a.json";
import def14aPersonsJson from "./def14a_persons.json";
import filingStreamJson from "./filing_stream.json";
import executivesJson from "./executives.json";
import newsFeedJson from "./news_feed.json";
import knowledgeShelfJson from "./knowledge_shelf.json";

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

// Freight TACO equivalent — a DISCLOSED degraded proxy (BTS TSI public-domain
// monthly index replacing commercial satellite truck counts; see the amber
// caliber card on /taco). truck_employment = BLS CES via FRED, null = honest gap.
export type FreightTaco = {
  status: string;
  as_of: string;
  source: string;
  source_url: string;
  license: string;
  methodology: string;
  degradation: {
    proxy: string;
    granularity_lost: string;
    commercial_original: string;
  };
  latest: {
    month: string;
    tsi: number;
    mom_pct: number;
    yoy_pct: number;
  };
  history: { n_months_total: number; first_month: string };
  series_24m: { month: string; tsi: number; mom_pct: number }[];
  truck_employment: {
    series_id: string;
    title: string;
    latest_month: string;
    latest_k: number;
    yoy_pct: number;
    series_24m: { month: string; k: number }[];
  } | null;
  snapshot_ts?: string;
};

export type RedditPick = {
  ticker: string;
  mentions: number;
  sentiment: number;
  score_sum: number;
  bull_ratio: number | null;
};

// Percent-of-class parsed from the filing's primary document (bounded second
// stage; visible rows only). null = honest miss (not extracted / not walked /
// EFTS-era row without an archive url) — never a guess.
export type StakesPct = {
  pct_now?: number | null;
  // Previous percent — /A amendments only ("previous X%"-style narrative).
  pct_prev?: number | null;
  // DERIVED from pct_now ONLY: "exited" (parsed 0) | "below_5" (parsed <5) |
  // null. No parsed value → no status. Active/passive is the form type.
  pct_status?: "exited" | "below_5" | null;
};

export type SmartMoney = {
  methodology?: string;
  recent_filings: ({
    filer: string;
    target: string;
    ticker: string;
    date: string;
    form: string;
    is_amendment: boolean;
    url?: string;
  } & StakesPct)[];  active_filers: { filer: string; count: number }[];
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
} & StakesPct;

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

export type KoreaProxy = {
  status: string;
  as_of: string | null;
  series_id: string;
  title: string;
  latest_rate: number;
  chg_4w_pct: number;
  high_52w: number;
  low_52w: number;
  // 0 = at the 52w low (calm) … 100 = at the 52w high (stress).
  stress_pct_52w: number;
  series_104w: { date: string; rate: number }[];
  methodology: string;
  snapshot_ts?: string;
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
  // len() of the panel's exported row list, computed at export time from the
  // committed payload (never a declared total). null = index/series panel with
  // no natural row table (or panel absent). Directory-scale counts (companies /
  // filers / managers) render from this instead of importing heavy panels.
  rows?: number | null;
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

export type PoliticianTx = {
  member: string;
  // house.gov directory join (district + last name); null for
  // candidates/former members.
  party: string | null;
  office: string;
  // Ticker as filed in the PDF; "" when the PDF carries none (bonds etc.).
  ticker: string;
  asset: string;
  // PTR asset-class code as bracketed in the PDF ("ST" = stock).
  type: string;
  direction: "buy" | "sell_partial" | "sell_full";
  // Statutory disclosure band text ("$15,001 - $50,000" / "$50,000,001+").
  amount_range: string;
  transaction_date: string;
  filing_date: string | null;
  // filing - transacted, whole days (STOCK Act clock; >45 = late).
  days_late: number | null;
  doc_url: string;
};

export type PoliticianTradesTx = {
  status: string;
  as_of: string | null;
  year: number;
  total: number;
  n_members: number;
  n_tickered: number;
  by_party: Record<string, {
    n_trades: number;
    n_buy: number;
    n_sell_partial: number;
    n_sell_full: number;
  }>;
  late_filings: number;
  party_coverage: string;
  transactions: PoliticianTx[];
  parse: {
    filings_total: number;
    filings_processed: number;
    fetch_errors: number;
    no_text_pdfs: number;
    row_candidates: number;
    rows_parsed: number;
    rows_exchanged: number;
    parse_failures: number;
    complete: boolean;
  };
  senate: { status: string; note: string };
  methodology: string;
  snapshot_ts?: string;
};

export type PartyIndexMonth = {
  month: string;
  d_tx: number;
  r_tx: number;
  d_buy: number;
  r_buy: number;
  // Tickers traded by BOTH parties that month.
  n_common: number;
  // Of those, tickers where BOTH parties have a nonzero net direction.
  n_directional: number;
  n_opposed: number;
  // n_opposed / n_directional ∈ [0,1]; null when no directional overlap.
  opposition: number | null;
};

export type PartyIndexTicker = {
  ticker: string;
  // net = buys − sells per party that month (count-weighted).
  d_net: number;
  r_net: number;
  n_d: number;
  n_r: number;
};

export type PartyIndexHolding = {
  ticker: string;
  asset: string;
  n_buy: number;
  n_sell: number;
  net_buy: number;
  n_members: number;
};

export type PartyIndex = {
  status: string;
  as_of: string | null;
  source_panel: string;
  window_anchor: string;
  window_days: number;
  n_source_tx: number;
  months: PartyIndexMonth[];
  latest: {
    month: string;
    opposition: number | null;
    opposed: PartyIndexTicker[];
    consensus: PartyIndexTicker[];
  };
  portfolios: Record<
    "D" | "R",
    { n_tx: number; n_members: number; holdings: PartyIndexHolding[] }
  >;
  methodology: string;
  snapshot_ts?: string;
};

export type ArkPosition = {
  ticker: string;
  company: string;
  // Official published weight (%), e.g. 9.24 = 9.24%.
  weight_pct: number;
  market_value: number;
};

export type ArkFund = {
  ticker: string;
  fund: string;
  as_of: string;
  n_positions: number;
  // Disclaimer footer / no-ticker / CASHX rows — counted, never silent.
  skipped_rows: number;
  top: ArkPosition[];
};

export type ArkOverlap = {
  ticker: string;
  company: string;
  funds: string[];
  max_weight_pct: number;
};

export type Ark = {
  status: string;
  as_of: string;
  n_funds: number;
  n_funds_expected: number;
  funds: ArkFund[];
  family_overlap: ArkOverlap[];
  methodology: string;
  snapshot_ts?: string;
};

export type ThemeEtfPosition = {
  // Official ticker as published (may be a foreign listing, e.g. "6861 JP").
  ticker: string;
  company: string;
  // Official published weight (%), e.g. 9.05 = 9.05%.
  weight_pct: number;
  market_value: number;
};

export type ThemeEtfFund = {
  ticker: string;
  // Issuer of the official file (iShares/BlackRock, Global X/Mirae Asset).
  issuer: string;
  fund: string;
  as_of: string;
  n_positions: number;
  // iShares non-equity legs / Global X no-ticker cash-FX rows — counted.
  skipped_rows: number;
  top: ThemeEtfPosition[];
};

export type ThemeEtfOverlap = {
  ticker: string;
  company: string;
  funds: string[];
  max_weight_pct: number;
};

export type ThemeEtfs = {
  status: string;
  as_of: string;
  n_funds: number;
  n_funds_expected: number;
  funds: ThemeEtfFund[];
  cross_fund_overlap: ThemeEtfOverlap[];
  methodology: string;
  snapshot_ts?: string;
};

export type RedditTrendingRow = {
  rank: number;
  ticker: string;
  name: string;
  mentions: number;
  upvotes: number;
  // First-party nullable 24h lags (null = unranked/unmentioned then).
  rank_24h_ago: number | null;
  mentions_24h_ago: number | null;
};

export type RedditTrending = {
  status: string;
  as_of: string | null;
  source: string;
  count_declared: number;
  n_rows: number;
  // Free API pagination was dead on 2026-08-23: 3 pages declared, page 1
  // only served (current_page echo) — visible board = first 100, disclosed.
  served_pages: number;
  pagination_ok: boolean;
  sibling_filters: Record<string, number>;
  tickers: RedditTrendingRow[];
  methodology: string;
  snapshot_ts?: string;
};

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

export type Def14aFiling = {
  company: string;
  // Empty for ~25% of filers (no symbol in the EDGAR display name) —
  // honest, never guessed.
  ticker: string;
  filed_date: string;
  // "DEF 14A" (new definitive proxy). The "DEF 14A/A" amendment arm exists
  // in the exporter as defense-in-depth; no such row today (amendments are
  // filed as DEFA14A, out of scope).
  form: string;
  // "new" | "amendment" — derived from the immutable form type.
  status: string;
  doc_url: string;
};

export type Def14a = {
  status: string;
  as_of: string;
  window: { start: string; end: string };
  issuers: number;
  total: number;
  by_form: Record<string, number>;
  filings: Def14aFiling[];
  methodology: string;
  snapshot_ts?: string;
};

// One parsed DEF 14A filing = one board card (company + director/officer
// sets). n_directors/n_officers are INDEPENDENT sets: a CEO who sits on the
// board counts in both (sum may exceed n_persons — disclosed).
export type Def14aPersonsBoard = {
  company: string;
  // Empty when the EDGAR display name carries no symbol (honest).
  ticker: string;
  issuer_cik: string;
  n_persons: number;
  n_directors: number;
  n_officers: number;
  filed_date: string;
  // EDGAR primary proxy document (the parse source, full link-out).
  doc_url: string;
};

// Cross-company person aggregate: the "board-seat intersection" cut. Identity
// keys on the normalized full name — same-name merges may join namesakes and
// some name shapes (initials-first, apostrophes) are conservatively missed.
export type Def14aPersonsTop = {
  name: string;
  // Canonical role words witnessed near the person's rows/bios (may include
  // past or external-company titles — text-witnessed hints, not employment
  // records).
  roles: string[];
  n_companies: number;
  n_director_seats: number;
  companies: string[];
};

export type Def14aPersons = {
  status: string;
  as_of: string | null;
  n_filings_target: number;
  n_filings_processed: number;
  n_with_persons: number;
  coverage_pct: number;
  n_persons_distinct: number;
  by_role: Record<string, number>;
  // Parse-confidence distribution: section_age_rows (HIGH, age-anchored
  // roster rows) / section_name_roles (MEDIUM) / unparsed_no_persons (honest
  // nulls) / fetch_or_doc_errors.
  confidence: Record<string, number>;
  boards: Def14aPersonsBoard[];
  top_persons: Def14aPersonsTop[];
  request_accounting: {
    n_http_requests_last_fetch: number;
    budget_seconds: number;
    budget_hit: boolean;
    fetched_at: string;
  };
  methodology: string;
  snapshot_ts?: string;
};

export type FilingStreamRow = {
  // Source form type: 8-K(/A) / 10-K(/A) / 10-Q(/A) / S-1(/A) / 4(/A) /
  // D(/A) / SC 13D(/A) / SC 13G(/A).
  form: string;
  // Company, the reporting person on Form 4, or "FILER → TARGET" on stakes.
  who: string;
  ticker: string;
  filed_date: string;
  doc_url: string;
};

export type FilingStream = {
  status: string;
  as_of: string;
  window: { start: string; end: string };
  // Full direct-query window vs the 800-newest visible cap.
  total_merged: number;
  n_visible: number;
  by_form: Record<string, number>;
  filings: FilingStreamRow[];
  // 10-K(/A) deep cut for /annual — the 800-newest cap squeezes periodic
  // reports out of the visible stream in filing season, so the family rides
  // its OWN newest-first slice (cap 400) from the same parquet.
  annual_filings: FilingStreamRow[];
  // 10-Q(/A) deep cut for /quarterly — same contract as annual_filings.
  quarterly_filings: FilingStreamRow[];
  // Full-window counts for the two deep-cut families (NOT the capped visible
  // length — the KPI shows the window, not the payload cap).
  annual_total: number;
  quarterly_total: number;
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

export type NewsFeedItem = {
  // GDELT first-seen UTC stamp, "YYYY-MM-DDTHH:MM:SSZ" (15-min resolution) —
  // empty string when the source stamp failed to normalize (honest empty).
  seendate: string;
  title: string;
  // Outbound link to the publisher's article — the ONLY way to read it; the
  // panel stores metadata, never article text.
  url: string;
  domain: string;
  language: string;
  // Ingest-resolved language lane: "eng" | "zho" (API language field first,
  // request-provenance fallback — never guessed from title bytes). Carries
  // the row's language tone on the stream (brand vs amber).
  lang: "eng" | "zho";
  sourcecountry: string;
};

export type NewsFeed = {
  status: string;
  // Newest GDELT first-seen stamp in the retained window (= items[0].seendate).
  as_of: string;
  window: { start: string; end: string };
  // The FIXED quoted-phrase queries, one per language lane (displayed
  // verbatim — fixed queries, no editorial tuning possible after the fact).
  query: string;
  // Full retained-window count; items is a capped (<=150) newest prefix.
  total: number;
  // Chinese-lane count over the FULL retained window (bilingual stream).
  n_zho: number;
  n_sources: number;
  by_day: { date: string; count: number }[];
  items: NewsFeedItem[];
  methodology: string;
  snapshot_ts?: string;
};

// Knowledge shelf (/shelf — browsable library over the repo's own method docs
// + curated outbound research bookmarks).
export type KnowledgeShelfCategory =
  | "preregistration"
  | "adr"
  | "results"
  | "rubric"
  | "theory";

export type KnowledgeShelfDoc = {
  title: string;
  // Repo-relative path ("docs/…" | "decisions/…").
  path: string;
  category: KnowledgeShelfCategory;
  // Last-commit date of the file (YYYY-MM-DD) read from LOCAL git at export
  // time; null only outside a repository (honest null, never fabricated).
  date: string | null;
  // Non-whitespace character count of the source file.
  n_chars: number;
  // Safe teaser slice: first 2-3 sentences (<=240 chars) of OUR OWN MIT doc —
  // the body stays on GitHub, this is a catalog, not a copy.
  summary: string;
  // Link-out to the full text on GitHub — the only way to read the body.
  url: string;
};

export type KnowledgeShelfSource = {
  name: string;
  org: string;
  url: string;
  desc_en: string;
  desc_zh: string;
};

export type KnowledgeShelf = {
  status: string;
  // Newest last-commit date among the cataloged docs (repo documentation
  // cadence — the shelf advances on doc commits, never on market data).
  as_of: string | null;
  n_docs: number;
  n_categories: number;
  categories: Record<KnowledgeShelfCategory, number>;
  docs: KnowledgeShelfDoc[];
  // FIXED editorially-curated bookmarks (frozen literals in the exporter —
  // link-out + one static sentence, no fetching/scraping/summary APIs).
  research_sources: KnowledgeShelfSource[];
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
  freightTaco: freightTacoJson as FreightTaco,
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
  koreaProxy: koreaProxyJson as KoreaProxy,
  themes: themesJson as Themes,
  ledgerAudit: ledgerAuditJson as LedgerAudit,
  headlineProvenance: headlineProvenanceJson as HeadlineProvenance,
  dataHealth: dataHealthJson as DataHealth,
  apiCatalog: apiCatalogJson as ApiCatalog,
  form8k: form8kJson as Form8k,
  ipo: ipoJson as FormIpo,
  politicianTrades: politicianTradesJson as PoliticianTrades,
  politicianTradesTx: politicianTradesTxJson as PoliticianTradesTx,
  partyIndex: partyIndexJson as PartyIndex,
  ark: arkJson as Ark,
  themeEtfs: themeEtfsJson as ThemeEtfs,
  redditTrending: redditTrendingJson as RedditTrending,
  formD: formDJson as FormD,
  def14a: def14aJson as Def14a,
  def14aPersons: def14aPersonsJson as Def14aPersons,
  filingStream: filingStreamJson as FilingStream,
  executives: executivesJson as Executives,
  newsFeed: newsFeedJson as NewsFeed,
  knowledgeShelf: knowledgeShelfJson as KnowledgeShelf,
};
