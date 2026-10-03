"use client";

// /atlas block 1 — core-claim pivots (display lane, zero fetches): a monthly
// rank-IC pivot heatmap (month × {US, CN, combined}) plus the preregistered
// claim forest plot (point estimate vs 95% CI vs SESOI equivalence zone vs
// the zero line). TASK-DISP-G1 additions keep the same discipline: a
// literature-context line under the forest plot (display-derived t vs the
// Harvey-Liu-Zhu 2016 published-factor threshold — juxtaposition only, no
// pass/fail framing) and a descriptive first/second-half IC stability strip
// under the heatmap (never rendered when either half holds fewer than 12
// months). Every layout coordinate is a fixed constant or derived from
// the committed panels — no Date.now / new Date / Math.random / locale
// formatting — so the SSG output stays byte-stable (H6 spirit). Each SVG
// ships with a full <table> fallback (force-camp precedent: column headers
// always render, honest empty state, never a fabricated number).
//
// Red lines honored: no --up/--down direction hues (the zero-centered
// blue↔orange diverging scale from @/components/diagram/tokens encodes
// magnitude around zero, not price direction), and no investment advice —
// these figures present measurements, including the NULL verdict, as-is.

import { aionis } from "@/data/aionis";
import { useI18n } from "@/i18n/provider";
import { FrostedScrollArea } from "@/components/ui/frosted-scroll-area";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { DiagramFigure } from "@/components/diagram/primitives";
import dynamic from "next/dynamic";
import { isNum, fmt, tf } from "./atlas-claims-prep";

// Surgical split (round 119, divergence round-118 recipe): the two SVG bodies
// hydrate from an async chunk; captions/tables/headers stay SSR above. The
// skeletons carry mobile-first figure heights (audit context) so CLS holds.
const figureSkeleton = (minHeight: number) => {
  const C = function FigureSkeleton() {
    return (
      <div
        aria-hidden="true"
        style={{ minHeight }}
        className="w-full animate-pulse rounded-xl border border-line bg-soft/50"
      />
    );
  };
  return C;
};
const ClaimsPivotChart = dynamic(
  () => import("./atlas-claims-charts").then(m => m.ClaimsPivotChart),
  { ssr: false, loading: figureSkeleton(320) },
);
const ClaimsForestChart = dynamic(
  () => import("./atlas-claims-charts").then(m => m.ClaimsForestChart),
  { ssr: false, loading: figureSkeleton(150) },
);

// ---------------------------------------------------------------------------
// Deterministic helpers
// ---------------------------------------------------------------------------

// The committed panel types IC cells as `number`, but the exporter can emit
// `null` for months a region has not scored yet (e.g. 2026-06 US). Treat any
// non-finite value as honestly missing — never coerce, never fabricate.
// (`v is number` keeps the guard usable as a filter/narrower for the
// number-or-null aggregates produced by the stability strip below.)
// isNum/fmt/tf live in ./atlas-claims-prep (round-119 split).

// Arithmetic mean over the finite values only; honestly null when a series
// contributes nothing usable (renders as "—", never as 0).
function meanOf(values: number[]): number | null {
  const finite = values.filter(isNum);
  return finite.length > 0
    ? finite.reduce((a, b) => a + b, 0) / finite.length
    : null;
}

// The i18n provider's t() takes a bare key; placeholder substitution follows
// the repo-wide `t(key).replace("{x}", …)` convention (companies / congress /
// data-health / audit-timeline views) via this tiny deterministic helper.
// ---------------------------------------------------------------------------
// Block A — monthly rank-IC pivot heatmap (two deterministic columns of rows)
// ---------------------------------------------------------------------------

const P_SERIES: { key: "us" | "cn" | "combined"; label: string }[] = [
  { key: "us", label: "US" },
  { key: "cn", label: "CN" },
  { key: "combined", label: "US+CN" },
];

// Pivot/forest geometry + cell-text fills live in ./atlas-claims-charts
// (round-119 split); P_SERIES stays — the SSR halves strip consumes it.

function IcPivotFigure() {
  const { t } = useI18n();

  // Month-ascending regardless of JSON ordering (ISO month strings sort
  // lexicographically) — stable, deterministic, build-time.
  const rows = [...aionis.icMonthly].sort((a, b) =>
    a.month < b.month ? -1 : a.month > b.month ? 1 : 0,
  );
  const countLine = tf(t("atlas.icpivot.n"), {
    n: String(rows.length),
    start: rows.length > 0 ? rows[0].month : "—",
    end: rows.length > 0 ? rows[rows.length - 1].month : "—",
  });

  return (
    <DiagramFigure
      title={t("atlas.icpivot.title")}
      desc={t("atlas.icpivot.desc")}
      caption={countLine}
      table={
        <FrostedScrollArea maxHeight={360} label={t("atlas.claims.table")}>
        <div className="overflow-hidden rounded-xl border border-line">
          <table className="w-full text-left text-[12px]">
            <caption className="border-b border-line2 bg-soft px-4 py-2 text-left text-[13px] font-semibold">
              {t("atlas.claims.table")}
            </caption>
            <thead>
              <tr className="text-mute">
                <th className="px-4 py-1.5 font-mono font-medium">month</th>
                {P_SERIES.map((s) => (
                  <th
                    key={s.key}
                    className="px-2 py-1.5 text-right font-mono font-medium"
                  >
                    {s.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.month} className="border-t border-line2">
                  <td className="px-4 py-1.5 font-mono tabular-nums text-sub">
                    {row.month}
                  </td>
                  {P_SERIES.map((s) => (
                    <td
                      key={s.key}
                      className="px-2 py-1.5 text-right font-mono tabular-nums"
                    >
                      {fmt(row[s.key], 4)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        </FrostedScrollArea>
      }
    >
      <ClaimsPivotChart />
    </DiagramFigure>
  );
}

// ---------------------------------------------------------------------------
// Block A2 — sample-period stability strip (descriptive): first vs second half
// of the month-ordered IC series per region, plus Δ. TASK-DISP-G1.
// ---------------------------------------------------------------------------

// Honesty gate: if either half holds fewer than 12 months the whole strip is
// not rendered (too little sample to even describe — never fabricate a row).
const HALVES_MIN_MONTHS = 12;

// Fixed split rule, not tunable: sort months ascending (ISO month strings
// compare lexicographically), split by count; with an odd total the FIRST
// half keeps the extra month.
function monthHalves() {
  const rows = [...aionis.icMonthly].sort((a, b) =>
    a.month < b.month ? -1 : a.month > b.month ? 1 : 0,
  );
  const half = Math.ceil(rows.length / 2);
  return [rows.slice(0, half), rows.slice(half)] as const;
}

function HalvesStabilityStrip() {
  const { t } = useI18n();

  const [firstHalf, secondHalf] = monthHalves();
  if (
    firstHalf.length < HALVES_MIN_MONTHS ||
    secondHalf.length < HALVES_MIN_MONTHS
  ) {
    return null;
  }

  // Per region: mean of with-data months per half, then Δ = second − first.
  // Any half missing all values for a region stays honestly "—"; Δ needs
  // both halves to exist and is never coerced from blanks.
  const stats = P_SERIES.map((s) => {
    const first = meanOf(firstHalf.map((r) => r[s.key]));
    const second = meanOf(secondHalf.map((r) => r[s.key]));
    const delta = first !== null && second !== null ? second - first : null;
    return { key: s.key, label: s.label, first, second, delta };
  });

  const range = (h: (typeof firstHalf)[number][]): string =>
    h.length > 0 ? `${h[0].month} → ${h[h.length - 1].month}` : "—";
  const noteLine = tf(t("atlas.icpivot.halves.note"), {
    n1: String(firstHalf.length),
    r1: range(firstHalf),
    n2: String(secondHalf.length),
    r2: range(secondHalf),
  });

  return (
    <div className="overflow-hidden rounded-xl border border-line bg-card">
      <div className="border-b border-line2 bg-soft px-4 py-2 text-[13px] font-semibold">
        {t("atlas.icpivot.halves.title")}
      </div>
      <table className="w-full text-left text-[12px]">
        <thead>
          <tr className="text-mute">
            <th className="w-[34%] px-4 py-1.5 font-mono font-medium">series</th>
            <th className="px-2 py-1.5 text-right font-mono font-medium">
              {t("atlas.icpivot.halves.first")}
            </th>
            <th className="px-2 py-1.5 text-right font-mono font-medium">
              {t("atlas.icpivot.halves.second")}
            </th>
            <th className="px-2 py-1.5 text-right font-mono font-medium">
              {t("atlas.icpivot.halves.delta")}
            </th>
          </tr>
        </thead>
        <tbody>
          {stats.map((s) => (
            <tr key={s.key} className="border-t border-line2">
              <td className="px-4 py-1.5 font-mono text-sub">{s.label}</td>
              <td className="px-2 py-1.5 text-right font-mono tabular-nums">
                {fmt(s.first, 4)}
              </td>
              <td className="px-2 py-1.5 text-right font-mono tabular-nums">
                {fmt(s.second, 4)}
              </td>
              <td className="px-2 py-1.5 text-right font-mono tabular-nums">
                {fmt(s.delta, 4)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="border-t border-line2 px-4 py-2 text-[11px] text-mute">
        {noteLine}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Block B — claim forest plot: point estimate vs 95% CI vs SESOI zone
// ---------------------------------------------------------------------------

function ForestFigure() {
  const { t } = useI18n();
  const m = aionis.metrics;


  const sesoiLabel = tf(t("atlas.forest.sesoi"), { v: fmt(m.sesoi, 2) });
  const verdictLine = tf(t("atlas.forest.verdict"), {
    v: m.verdict || "—",
    p: fmt(m.p, 3),
    n: isNum(m.n_months) ? String(m.n_months) : "—",
  });

  const forestRows: { label: string; value: string }[] = [
    { label: t("atlas.forest.point"), value: fmt(m.combined_ic, 4) },
    {
      label: t("atlas.forest.ci"),
      value: `[${fmt(m.ci_lo, 4)}, ${fmt(m.ci_hi, 4)}]`,
    },
    { label: sesoiLabel, value: fmt(m.sesoi, 4) },
    { label: t("audit.col.verdict"), value: m.verdict || "—" },
    { label: "p", value: fmt(m.p, 3) },
    {
      label: t("kpi.n_months"),
      value: isNum(m.n_months) ? String(m.n_months) : "—",
    },
  ];

  return (
    <DiagramFigure
      title={t("atlas.forest.title")}
      desc={t("atlas.forest.desc")}
      caption={verdictLine}
      table={
        <div className="overflow-hidden rounded-xl border border-line">
          <table className="w-full text-left text-[12px]">
            <caption className="border-b border-line2 bg-soft px-4 py-2 text-left text-[13px] font-semibold">
              {t("atlas.claims.table")}
            </caption>
            <thead>
              <tr className="text-mute">
                {/* Column labels are descriptive (i18n); row labels are the
                    schema names of the committed panel (metric/verdict/p/n)
                    and stay literal for traceability to the JSON keys. */}
                <th className="w-[40%] px-4 py-1.5 font-mono font-medium">
                  {t("atlas.forest.col_metric")}
                </th>
                <th className="px-4 py-1.5 text-right font-mono font-medium">
                  {t("atlas.forest.col_value")}
                </th>
              </tr>
            </thead>
            <tbody>
              {forestRows.map((row) => (
                <tr key={row.label} className="border-t border-line2">
                  <td className="px-4 py-1.5 text-sub">{row.label}</td>
                  <td className="px-4 py-1.5 text-right font-mono tabular-nums">
                    {row.value}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      }
    >
      <ClaimsForestChart />
    </DiagramFigure>
  );
}

// ---------------------------------------------------------------------------
// Section card
// ---------------------------------------------------------------------------

export default function AtlasClaims() {
  const { t } = useI18n();
  return (
    <Card>
      <CardHeader>
        <CardTitle as="h2">{t("atlas.claims.title")}</CardTitle>
        <CardDescription>{t("atlas.claims.desc")}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-8">
        <IcPivotFigure />
        <HalvesStabilityStrip />
        <ForestFigure />
      </CardContent>
    </Card>
  );
}
