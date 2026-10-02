// Shared pure data-prep for the /atlas divergence section (round 118 surgical
// split): lives OUTSIDE the dynamically-imported charts module so the table
// fallbacks (SSR content) keep computing locally without pulling SVG code
// into the initial chunk.
import type { CalibrationReliability } from "@/data/aionis";

export type CalSeries = CalibrationReliability["regions"][string]["series"][number];

// Region labels are literal locale-neutral tokens (spec: "US"/"CN" do not go
// through the dict).
export const REGIONS = ["us", "cn"] as const;

// Deterministic ascending month order (byte compare — ISO-like keys sort
// chronologically; no locale-dependent collation).
export const byMonthAsc = (a: CalSeries, b: CalSeries) =>
  a.month < b.month ? -1 : a.month > b.month ? 1 : 0;

// The i18n provider's t() is a plain key lookup; dict values carry {var}
// placeholders, so interpolation is applied here (dict.ts is untouchable).
export function fmtTpl(
  tpl: string,
  p: Record<string, string | number>,
): string {
  return tpl.replace(/\{(\w+)\}/g, (m, k: string) =>
    k in p ? String(p[k]) : m,
  );
}

export type RegionPrep = {
  label: string;
  series: CalSeries[];
  inBand: boolean[];
  nIn: number;
  m: number;
  pct: number;
  pooled: number;
  start: string;
  end: string;
};

export function prepRegion(
  cal: CalibrationReliability,
  region: (typeof REGIONS)[number],
): RegionPrep {
  const payload = cal.regions[region];
  const series = [...payload.series].sort(byMonthAsc);
  const inBand = series.map(
    (s) => s.base_rate >= s.prob_min && s.base_rate <= s.prob_max,
  );
  const nIn = inBand.filter(Boolean).length;
  const m = series.length;
  return {
    label: region.toUpperCase(),
    series,
    inBand,
    nIn,
    m,
    pct: m > 0 ? Math.round((100 * nIn) / m) : 0,
    pooled: payload.pooled_ece,
    start: series[0]?.month ?? "—",
    end: series.at(-1)?.month ?? "—",
  };
}
