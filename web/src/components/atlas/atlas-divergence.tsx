"use client";

import { Card, CardContent } from "@/components/ui/card";
import {
  DiagramFigure,
  niceTicks,
  scaleLinear,
} from "@/components/diagram/primitives";
import { diagram, divergingScale } from "@/components/diagram/tokens";
import { aionis, type CalibrationReliability } from "@/data/aionis";
import { useI18n } from "@/i18n/provider";
import { fmtEmpty } from "@/lib/format";

// /atlas section 2 (TASK-DISP-D2) — forecast-vs-realized divergence (display
// lane, zero fetches): Block A renders each month's walk-forward calibrated
// probability band (prob_min–prob_max) as a translucent primary rect with the
// realized base_rate as a dot (in-band = filled primary, out-of-band = warm
// stroked hollow dot); Block B renders monthly OOS ECE bars with the pooled
// ECE as a dashed reference line. US / CN side by side, deterministic layout
// computed from the committed panel at render (SSG build time), full <table>
// fallback per figure (column headers always render, honest empty state).
//
// Red lines honored: no --up/--down or red/green direction encoding, no
// Date.now / Math.random, no investment advice — measurement only.

type CalSeries = CalibrationReliability["regions"][string]["series"][number];

// Region labels are literal locale-neutral tokens (spec: "US"/"CN" do not go
// through the dict).
const REGIONS = ["us", "cn"] as const;

// The out-of-band accent is the warm end of the approved colorblind-safe
// diverging scale (editorial accent orange) — NOT a direction semantic; it
// only flags "this month's realized base rate fell outside its own band".
const OUT_DOT = divergingScale[divergingScale.length - 1];

// Per-panel SVG geometry (viewBox units; ~2.5:1 aspect keeps rendered height
// in the spec's 180–220px band at two-column widths).
const VB_W = 520;
const VB_H = 210;
const M_L = 32;
const M_R = 6;
const PLOT_TOP = 8;
const PLOT_BOTTOM = VB_H - 24;
const PLOT_W = VB_W - M_L - M_R;

// Block A y-axis is fixed [0,1] — its ticks are a module-level constant.
const P_TICKS = niceTicks(0, 1);

// The i18n provider's t() is a plain key lookup; dict values carry {var}
// placeholders, so interpolation is applied here (dict.ts is untouchable).
function fmtTpl(tpl: string, p: Record<string, string | number>): string {
  return tpl.replace(/\{(\w+)\}/g, (m, k: string) => (k in p ? String(p[k]) : m));
}

// Deterministic ascending month order (byte compare — ISO-like keys sort
// chronologically; no locale-dependent collation).
const byMonthAsc = (a: CalSeries, b: CalSeries) =>
  a.month < b.month ? -1 : a.month > b.month ? 1 : 0;

type RegionPrep = {
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

function prepRegion(
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

// Shared deterministic frame: horizontal gridlines + y labels + baseline +
// sparse x labels (every 6th month). All coordinates are build-time constants.
function PanelFrame({
  months,
  y,
  yTicks,
  yDecimals,
}: {
  months: string[];
  y: (v: number) => number;
  yTicks: number[];
  yDecimals: number;
}) {
  const n = months.length;
  const step = n > 0 ? PLOT_W / n : PLOT_W;
  return (
    <g>
      {yTicks.map((v) => (
        <g key={`yt-${v}`}>
          <line
            x1={M_L}
            x2={VB_W - M_R}
            y1={y(v)}
            y2={y(v)}
            stroke={diagram.border}
            strokeDasharray="2 4"
          />
          <text
            x={M_L - 4}
            y={y(v) + 3}
            textAnchor="end"
            fontSize={9}
            fill={diagram.muted}
            className="font-mono"
          >
            {v.toFixed(yDecimals)}
          </text>
        </g>
      ))}
      <line
        x1={M_L}
        x2={VB_W - M_R}
        y1={PLOT_BOTTOM}
        y2={PLOT_BOTTOM}
        stroke={diagram.border}
      />
      {months.map((mo, i) =>
        i % 6 === 0 ? (
          <text
            key={`xt-${mo}`}
            x={M_L + (i + 0.5) * step}
            y={VB_H - 8}
            textAnchor="middle"
            fontSize={9}
            fill={diagram.muted}
            className="font-mono"
          >
            {mo}
          </text>
        ) : null,
      )}
    </g>
  );
}

function BandPanel({ p }: { p: RegionPrep }) {
  const { t } = useI18n();
  const n = p.series.length;
  const step = n > 0 ? PLOT_W / n : PLOT_W;
  const bw = Math.min(12, step * 0.62);
  const y = scaleLinear([0, 1], [PLOT_BOTTOM, PLOT_TOP]);
  return (
    <div>
      <div className="flex items-baseline justify-between gap-2">
        <p className="text-[13px] font-semibold">{p.label}</p>
        <p className="font-mono text-[11px] text-muted-foreground">
          {p.m > 0
            ? fmtTpl(t("atlas.div.coverage"), { n: p.nIn, m: p.m, pct: p.pct })
            : fmtEmpty(null)}
        </p>
      </div>
      <svg
        viewBox={`0 0 ${VB_W} ${VB_H}`}
        className="mt-1 h-auto w-full"
        role="img"
        aria-label={p.label}
      >
        <PanelFrame
          months={p.series.map((s) => s.month)}
          y={y}
          yTicks={P_TICKS}
          yDecimals={1}
        />
        <g>
          {p.series.map((s, i) => {
            const top = y(s.prob_max);
            return (
              <rect
                key={`band-${s.month}`}
                x={M_L + (i + 0.5) * step - bw / 2}
                y={top}
                width={bw}
                height={Math.max(1, y(s.prob_min) - top)}
                fill={diagram.primary}
                fillOpacity={0.22}
              />
            );
          })}
        </g>
        <g>
          {p.series.map((s, i) =>
            p.inBand[i] ? (
              <circle
                key={`dot-${s.month}`}
                cx={M_L + (i + 0.5) * step}
                cy={y(s.base_rate)}
                r={2.2}
                fill={diagram.primary}
                stroke={diagram.card}
                strokeWidth={0.8}
              />
            ) : (
              <circle
                key={`dot-${s.month}`}
                cx={M_L + (i + 0.5) * step}
                cy={y(s.base_rate)}
                r={2.8}
                fill={diagram.card}
                stroke={OUT_DOT}
                strokeWidth={1.6}
              />
            ),
          )}
        </g>
      </svg>
    </div>
  );
}

function EcePanel({ p }: { p: RegionPrep }) {
  const n = p.series.length;
  const step = n > 0 ? PLOT_W / n : PLOT_W;
  const bw = Math.min(12, step * 0.62);
  const yMax = Math.max(0.5, ...p.series.map((s) => s.ece_oos));
  const ticks = niceTicks(0, yMax);
  const tickStep = ticks.length > 1 ? ticks[1] - ticks[0] : 0.1;
  const dec = tickStep >= 0.09 ? 1 : tickStep >= 0.009 ? 2 : 3;
  const y = scaleLinear([0, yMax], [PLOT_BOTTOM, PLOT_TOP]);
  return (
    <div>
      <div className="flex items-baseline justify-between gap-2">
        <p className="text-[13px] font-semibold">{p.label}</p>
        <p className="font-mono text-[11px] text-muted-foreground">
          y-max {yMax.toFixed(dec)}
        </p>
      </div>
      <svg
        viewBox={`0 0 ${VB_W} ${VB_H}`}
        className="mt-1 h-auto w-full"
        role="img"
        aria-label={p.label}
      >
        <PanelFrame
          months={p.series.map((s) => s.month)}
          y={y}
          yTicks={ticks}
          yDecimals={dec}
        />
        <g>
          {p.series.map((s, i) => (
            <rect
              key={`ece-${s.month}`}
              x={M_L + (i + 0.5) * step - bw / 2}
              y={y(s.ece_oos)}
              width={bw}
              height={PLOT_BOTTOM - y(s.ece_oos)}
              fill={diagram.primary}
              fillOpacity={0.5}
            />
          ))}
        </g>
        {p.m > 0 ? (
          <g>
            <line
              x1={M_L}
              x2={VB_W - M_R}
              y1={y(p.pooled)}
              y2={y(p.pooled)}
              stroke={diagram.ink}
              strokeDasharray="6 4"
              strokeOpacity={0.7}
            />
            <text
              x={VB_W - M_R}
              y={y(p.pooled) - 3}
              textAnchor="end"
              fontSize={9}
              fill={diagram.muted}
              className="font-mono"
            >
              pooled_ece = {p.pooled.toFixed(3)}
            </text>
          </g>
        ) : null}
      </svg>
    </div>
  );
}

export default function AtlasDivergence() {
  const { t } = useI18n();
  const cal = aionis.calibrationReliability;
  const panels = REGIONS.map((r) => prepRegion(cal, r));

  const countsLine = panels
    .map((p) =>
      p.m > 0
        ? `${p.label} ${fmtTpl(t("atlas.div.n"), {
            n: p.m,
            start: p.start,
            end: p.end,
          })}`
        : `${p.label} ${fmtEmpty(null)}`,
    )
    .join(" · ");

  const tablesA = (
    <div className="space-y-4">
      {panels.map((p) => (
        <div key={`table-a-${p.label}`}>
          <p className="text-xs font-semibold">
            {t("atlas.div.table")} — {p.label}
          </p>
          <table className="mt-1 w-full text-left text-[12px]">
            <thead>
              <tr className="text-muted-foreground">
                <th
                  rowSpan={2}
                  className="border-b border-border px-3 py-1.5 text-left font-medium"
                >
                  month
                </th>
                <th
                  colSpan={2}
                  className="border-b border-border px-3 py-1.5 text-center font-medium"
                >
                  {t("atlas.div.band")}
                </th>
                <th
                  rowSpan={2}
                  className="border-b border-border px-3 py-1.5 text-right font-medium"
                >
                  {t("atlas.div.realized")}
                </th>
                <th
                  rowSpan={2}
                  className="border-b border-border px-3 py-1.5 text-center font-medium"
                >
                  in-band
                </th>
              </tr>
              <tr className="text-muted-foreground">
                <th className="border-b border-border px-3 py-1.5 text-right font-medium">
                  prob_min
                </th>
                <th className="border-b border-border px-3 py-1.5 text-right font-medium">
                  prob_max
                </th>
              </tr>
            </thead>
            <tbody>
              {p.series.map((s, i) => (
                <tr key={s.month} className="border-t border-border">
                  <td className="px-3 py-1 font-mono text-[11px]">{s.month}</td>
                  <td className="px-3 py-1 text-right font-mono tabular-nums text-muted-foreground">
                    {s.prob_min.toFixed(3)}
                  </td>
                  <td className="px-3 py-1 text-right font-mono tabular-nums text-muted-foreground">
                    {s.prob_max.toFixed(3)}
                  </td>
                  <td className="px-3 py-1 text-right font-mono tabular-nums">
                    {s.base_rate.toFixed(3)}
                  </td>
                  <td
                    className={`px-3 py-1 text-center font-mono ${
                      p.inBand[i] ? "" : "text-muted-foreground"
                    }`}
                  >
                    {p.inBand[i] ? "✓" : "✗"}
                  </td>
                </tr>
              ))}
              {p.m === 0 ? (
                <tr className="border-t border-border">
                  <td
                    colSpan={5}
                    className="px-3 py-4 text-center text-muted-foreground"
                  >
                    {fmtEmpty(null)}
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      ))}
    </div>
  );

  const tablesB = (
    <div className="space-y-4">
      {panels.map((p) => (
        <div key={`table-b-${p.label}`}>
          <p className="text-xs font-semibold">
            {t("atlas.div.table")} — {p.label}
          </p>
          <table className="mt-1 w-full text-left text-[12px]">
            <thead>
              <tr className="text-muted-foreground">
                <th className="border-b border-border px-3 py-1.5 text-left font-medium">
                  month
                </th>
                <th className="border-b border-border px-3 py-1.5 text-right font-medium">
                  ece_oos
                </th>
                <th className="border-b border-border px-3 py-1.5 text-center font-medium">
                  ≥ pooled
                </th>
              </tr>
            </thead>
            <tbody>
              {p.series.map((s) => (
                <tr key={s.month} className="border-t border-border">
                  <td className="px-3 py-1 font-mono text-[11px]">{s.month}</td>
                  <td className="px-3 py-1 text-right font-mono tabular-nums">
                    {s.ece_oos.toFixed(3)}
                  </td>
                  <td
                    className={`px-3 py-1 text-center font-mono ${
                      s.ece_oos >= p.pooled ? "" : "text-muted-foreground"
                    }`}
                  >
                    {s.ece_oos >= p.pooled ? "✓" : "✗"}
                  </td>
                </tr>
              ))}
              {p.m === 0 ? (
                <tr className="border-t border-border">
                  <td
                    colSpan={3}
                    className="px-3 py-4 text-center text-muted-foreground"
                  >
                    {fmtEmpty(null)}
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      ))}
    </div>
  );

  return (
    <div className="flex flex-col gap-4">
      {/* Block A — forecast-vs-realized probability bands (US / CN). */}
      <Card>
        <CardContent>
          <DiagramFigure
            title={t("atlas.div.title")}
            desc={t("atlas.div.desc")}
            caption={countsLine}
            table={tablesA}
          >
            <div className="grid gap-6 md:grid-cols-2">
              {panels.map((p) => (
                <BandPanel key={`band-${p.label}`} p={p} />
              ))}
            </div>
            <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-muted-foreground">
              <span className="inline-flex items-center gap-1.5">
                <svg width={18} height={10} aria-hidden="true">
                  <rect
                    x={0}
                    y={1}
                    width={18}
                    height={8}
                    fill={diagram.primary}
                    fillOpacity={0.22}
                  />
                </svg>
                {t("atlas.div.band")}
              </span>
              <span className="inline-flex items-center gap-1.5">
                <svg width={10} height={10} aria-hidden="true">
                  <circle
                    cx={5}
                    cy={5}
                    r={3.2}
                    fill={diagram.primary}
                    stroke={diagram.card}
                    strokeWidth={0.8}
                  />
                </svg>
                {t("atlas.div.realized")}
              </span>
              <span className="inline-flex items-center gap-1.5">
                <svg width={10} height={10} aria-hidden="true">
                  <circle
                    cx={5}
                    cy={5}
                    r={3.2}
                    fill={diagram.card}
                    stroke={OUT_DOT}
                    strokeWidth={1.6}
                  />
                </svg>
                out-of-band
              </span>
            </div>
          </DiagramFigure>
        </CardContent>
      </Card>

      {/* Block B — monthly OOS ECE bars with pooled reference line. */}
      <Card>
        <CardContent>
          <DiagramFigure
            title={t("atlas.div.ece.title")}
            desc={t("atlas.div.ece.desc")}
            table={tablesB}
          >
            <div className="grid gap-6 md:grid-cols-2">
              {panels.map((p) => (
                <EcePanel key={`ece-${p.label}`} p={p} />
              ))}
            </div>
          </DiagramFigure>
        </CardContent>
      </Card>

      {/* Methodology disclosure (from the committed panel, verbatim). */}
      {cal.method || cal.methodology ? (
        <div className="rounded-xl border border-border bg-card px-5 py-4">
          <p className="font-mono text-[11px] text-muted-foreground">
            {cal.method ? `method=${cal.method}` : ""}
            {cal.walk_forward != null
              ? `${cal.method ? " · " : ""}walk_forward=${String(cal.walk_forward)}`
              : ""}
            {cal.min_train_months != null
              ? ` · min_train_months=${cal.min_train_months}`
              : ""}
          </p>
          {cal.methodology ? (
            <p className="mt-1 line-clamp-4 font-mono text-[11px] leading-relaxed text-muted-foreground">
              {cal.methodology}
            </p>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
