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
import {
  diagram,
  divergingColor,
  divergingIndex,
  divergingScale,
} from "@/components/diagram/tokens";
import {
  DiagramFigure,
  niceTicks,
  scaleLinear,
} from "@/components/diagram/primitives";

// ---------------------------------------------------------------------------
// Deterministic helpers
// ---------------------------------------------------------------------------

// The committed panel types IC cells as `number`, but the exporter can emit
// `null` for months a region has not scored yet (e.g. 2026-06 US). Treat any
// non-finite value as honestly missing — never coerce, never fabricate.
// (`v is number` keeps the guard usable as a filter/narrower for the
// number-or-null aggregates produced by the stability strip below.)
const isNum = (v: number | null | undefined): v is number =>
  typeof v === "number" && Number.isFinite(v);

const fmt = (v: number | null | undefined, dp: number): string =>
  isNum(v) ? v.toFixed(dp) : "—";

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
function tf(template: string, params: Record<string, string>): string {
  let out = template;
  for (const [k, v] of Object.entries(params)) {
    out = out.split(`{${k}}`).join(v);
  }
  return out;
}

// ---------------------------------------------------------------------------
// Block A — monthly rank-IC pivot heatmap (two deterministic columns of rows)
// ---------------------------------------------------------------------------

const SYM_MAX = 0.3; // |IC| that maps to the strongest diverging bucket
const PIVOT_W = 1000;
const P_PAD = 8;
const P_COL_GAP = 16;
const P_COL_W = (PIVOT_W - P_PAD * 2 - P_COL_GAP) / 2; // 484
const P_LABEL_W = 64;
const P_CELL_GAP = 4;
const P_CELL_W = (P_COL_W - P_LABEL_W - P_CELL_GAP * 2) / 3; // ≈137.3
const P_HEAD_H = 20;
const P_ROW_H = 18; // spec: 18–20px compressed rows for a 66-month series
const P_ROW_PITCH = 20;

const P_SERIES: { key: "us" | "cn" | "combined"; label: string }[] = [
  { key: "us", label: "US" },
  { key: "cn", label: "CN" },
  { key: "combined", label: "US+CN" },
];

// Cell fills are fixed oklch values (theme-independent by design), so cell
// text must be fixed too. White on the three darkest buckets, near-black on
// the light ones (contrast-checked against the token scale), and a muted warm
// ink on bucket 4 (~zero) so dead months read quietly instead of loudly.
const CELL_TEXT_LIGHT = "oklch(0.98 0.01 80)";
const CELL_TEXT_DARK = "oklch(0.25 0.02 259)";
const CELL_TEXT_MUTED = "oklch(0.38 0.03 75)";

function cellTextFill(v: number): string {
  const bucket = divergingIndex(v, SYM_MAX);
  if (bucket === 0 || bucket === 1 || bucket === 8) return CELL_TEXT_LIGHT;
  if (bucket === 4) return CELL_TEXT_MUTED;
  return CELL_TEXT_DARK;
}

function IcPivotFigure() {
  const { t } = useI18n();

  // Month-ascending regardless of JSON ordering (ISO month strings sort
  // lexicographically) — stable, deterministic, build-time.
  const rows = [...aionis.icMonthly].sort((a, b) =>
    a.month < b.month ? -1 : a.month > b.month ? 1 : 0,
  );
  const half = Math.ceil(rows.length / 2);
  const cols: (typeof rows)[] = [rows.slice(0, half), rows.slice(half)];
  const rowsPerCol = Math.max(cols[0].length, cols[1].length);
  const svgH = P_PAD + P_HEAD_H + rowsPerCol * P_ROW_PITCH + P_PAD;
  const colX0 = [P_PAD, P_PAD + P_COL_W + P_COL_GAP];
  const cellXs = (x0: number): number[] => [
    x0 + P_LABEL_W,
    x0 + P_LABEL_W + P_CELL_W + P_CELL_GAP,
    x0 + P_LABEL_W + (P_CELL_W + P_CELL_GAP) * 2,
  ];

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
      <div className="overflow-hidden rounded-xl border border-line bg-card p-2">
        <svg
          viewBox={`0 0 ${PIVOT_W} ${svgH}`}
          className="h-auto w-full"
          aria-hidden="true"
        >
          {colX0.map((x0, ci) => {
            const xs = cellXs(x0);
            return (
              <g key={ci}>
                <text
                  x={x0 + 2}
                  y={P_PAD + 13}
                  fontSize={10}
                  className="font-mono"
                  fill={diagram.muted}
                >
                  month
                </text>
                {P_SERIES.map((s, si) => (
                  <text
                    key={s.key}
                    x={xs[si] + P_CELL_W / 2}
                    y={P_PAD + 13}
                    textAnchor="middle"
                    fontSize={10}
                    className="font-mono"
                    fill={diagram.muted}
                  >
                    {s.label}
                  </text>
                ))}
                {cols[ci].map((row, ri) => {
                  const y = P_PAD + P_HEAD_H + ri * P_ROW_PITCH;
                  return (
                    <g key={row.month}>
                      <text
                        x={x0 + 2}
                        y={y + 13}
                        fontSize={10.5}
                        className="font-mono tabular-nums"
                        fill={diagram.muted}
                      >
                        {row.month}
                      </text>
                      {P_SERIES.map((s, si) => {
                        const v = row[s.key];
                        return (
                          <g key={s.key}>
                            <rect
                              x={xs[si]}
                              y={y}
                              width={P_CELL_W}
                              height={P_ROW_H}
                              rx={3}
                              fill={
                                isNum(v)
                                  ? divergingColor(v, SYM_MAX)
                                  : diagram.mutedBg
                              }
                              stroke={isNum(v) ? "none" : diagram.border}
                            />
                            <text
                              x={xs[si] + P_CELL_W / 2}
                              y={y + 13}
                              textAnchor="middle"
                              fontSize={10.5}
                              className="font-mono tabular-nums"
                              fill={
                                isNum(v) ? cellTextFill(v) : diagram.muted
                              }
                            >
                              {fmt(v, 2)}
                            </text>
                          </g>
                        );
                      })}
                    </g>
                  );
                })}
              </g>
            );
          })}
        </svg>
        {/* Diverging-scale legend: the 9 fixed buckets of the shared token
            scale, from strongest negative (left) to strongest positive. */}
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 px-2 pb-1 pt-2 text-[11px] text-mute">
          <span className="inline-flex items-center gap-1.5">
            <span className="font-mono tabular-nums">−{SYM_MAX.toFixed(2)}</span>
            <span className="inline-flex overflow-hidden rounded-sm">
              {divergingScale.map((c) => (
                <span
                  key={c}
                  className="inline-block h-3 w-5"
                  style={{ background: c }}
                />
              ))}
            </span>
            <span className="font-mono tabular-nums">+{SYM_MAX.toFixed(2)}</span>
          </span>
          <span>{t("atlas.icpivot.legend")}</span>
        </div>
      </div>
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

const F_W = 1000;
const F_ML = 16;
const F_MR = 16;
const F_H = 184;
const F_BAND_Y = 52;
const F_BAND_H = 76;
const F_CI_Y = 90;
const F_LABEL_Y = 40;
const F_AXIS_Y = 152;
const F_TICK_LABEL_Y = 170;
const F_DOMAIN: readonly [number, number] = [-0.06, 0.06];

function ForestFigure() {
  const { t } = useI18n();
  const m = aionis.metrics;

  const x = scaleLinear(F_DOMAIN, [F_ML, F_W - F_MR]);
  const hasPoint = isNum(m.combined_ic);
  const hasCi = isNum(m.ci_lo) && isNum(m.ci_hi);
  const hasSesoi = isNum(m.sesoi);

  const sesoiLabel = tf(t("atlas.forest.sesoi"), { v: fmt(m.sesoi, 2) });
  const verdictLine = tf(t("atlas.forest.verdict"), {
    v: m.verdict || "—",
    p: fmt(m.p, 3),
    n: isNum(m.n_months) ? String(m.n_months) : "—",
  });

  // TASK-DISP-G1 — display-derived t for the literature-context line. Pure
  // arithmetic over the committed panel, NOT a model output and NOT a test
  // statistic. Fixed formula: se ≈ (ci_hi − ci_lo) / (2 × 1.96), then
  // t = combined_ic / se. Rendered only when both CI bounds exist and the
  // implied width gives se > 0 — no CI → the line honestly does not render.
  const se = hasCi ? (m.ci_hi - m.ci_lo) / (2 * 1.96) : null;
  const derivedT =
    se !== null && se > 0 && hasPoint ? m.combined_ic / se : null;
  const contextLine =
    derivedT !== null
      ? tf(t("atlas.forest.context"), { t: fmt(derivedT, 2) })
      : null;

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
      <div className="overflow-hidden rounded-xl border border-line bg-card p-2">
        <svg
          viewBox={`0 0 ${F_W} ${F_H}`}
          className="h-auto w-full"
          aria-hidden="true"
        >
          {/* SESOI equivalence zone */}
          {hasSesoi ? (
            <rect
              x={x(-m.sesoi)}
              y={F_BAND_Y}
              width={x(m.sesoi) - x(-m.sesoi)}
              height={F_BAND_H}
              fill={diagram.mutedBg}
              stroke={diagram.border}
              strokeDasharray="4 3"
            />
          ) : null}
          {/* Zero (no-effect) line — the preregistered two-tailed anchor */}
          <line
            x1={x(0)}
            x2={x(0)}
            y1={F_BAND_Y}
            y2={F_BAND_Y + F_BAND_H}
            stroke={diagram.ink}
            strokeWidth={2.5}
          />
          <text
            x={x(0) - 8}
            y={F_LABEL_Y}
            textAnchor="end"
            fontSize={11}
            fill={diagram.muted}
          >
            {t("atlas.forest.zeroLine")}
          </text>
          {hasSesoi ? (
            <text
              x={x(m.sesoi) + 8}
              y={F_LABEL_Y}
              fontSize={11}
              fill={diagram.muted}
            >
              {sesoiLabel}
            </text>
          ) : null}
          {/* 95% CI bar + point estimate */}
          {hasCi ? (
            <g stroke={diagram.ink}>
              <line
                x1={x(m.ci_lo)}
                x2={x(m.ci_hi)}
                y1={F_CI_Y}
                y2={F_CI_Y}
                strokeWidth={3}
              />
              <line
                x1={x(m.ci_lo)}
                x2={x(m.ci_lo)}
                y1={F_CI_Y - 8}
                y2={F_CI_Y + 8}
                strokeWidth={2}
              />
              <line
                x1={x(m.ci_hi)}
                x2={x(m.ci_hi)}
                y1={F_CI_Y - 8}
                y2={F_CI_Y + 8}
                strokeWidth={2}
              />
            </g>
          ) : null}
          {hasPoint ? (
            <circle
              cx={x(m.combined_ic)}
              cy={F_CI_Y}
              r={6}
              fill={diagram.primary}
              stroke={diagram.card}
              strokeWidth={1.5}
            />
          ) : null}
          {/* Axis */}
          <line
            x1={F_ML}
            x2={F_W - F_MR}
            y1={F_AXIS_Y}
            y2={F_AXIS_Y}
            stroke={diagram.border}
          />
          {niceTicks(F_DOMAIN[0], F_DOMAIN[1], 7).map((tick) => (
            <g key={tick}>
              <line
                x1={x(tick)}
                x2={x(tick)}
                y1={F_AXIS_Y}
                y2={F_AXIS_Y + 5}
                stroke={diagram.border}
              />
              <text
                x={x(tick)}
                y={F_TICK_LABEL_Y}
                textAnchor="middle"
                fontSize={10}
                className="font-mono tabular-nums"
                fill={diagram.muted}
              >
                {tick.toFixed(2)}
              </text>
            </g>
          ))}
        </svg>
        {/* Legend: point / CI / SESOI band / zero line */}
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 px-2 pb-1 pt-2 text-[11px] text-mute">
          <span className="inline-flex items-center gap-1.5">
            <span
              className="inline-block size-2.5 rounded-full"
              style={{ background: "var(--primary)" }}
            />
            {t("atlas.forest.point")}
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="inline-block h-[3px] w-6 rounded bg-ink" />
            {t("atlas.forest.ci")}
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="inline-block h-3 w-6 rounded-sm border border-dashed border-line bg-muted" />
            {sesoiLabel}
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="inline-block h-3 w-[3px] bg-ink" />
            {t("atlas.forest.zeroLine")}
          </span>
        </div>
        {/* Literature context (TASK-DISP-G1): the derived t is juxtaposed
            with the Harvey-Liu-Zhu (2016 RFS) published-factor threshold —
            context only. No pass/fail framing in either direction: the NULL
            verdict stands as preregistered regardless of the comparison. */}
        {contextLine ? (
          <div className="border-t border-line2 px-2 pb-1 pt-2 text-[11px] leading-relaxed text-mute">
            <span className="font-medium text-sub">
              {t("atlas.forest.context.source")}
            </span>
            <span className="mx-1.5">·</span>
            <span>{contextLine}</span>
          </div>
        ) : null}
      </div>
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
