"use client";

// /atlas section 3 (TASK-DISP-R1A) — score-surface diagnostics (display lane,
// zero fetches): pure descriptive statistics over the frozen confirmatory OOS
// score cross-section (aionis.scoreDiagnostics). Panel A renders each month's
// cross-sectional score std as a primary bar with the IQR as a thin ink line
// (magnitudes, NOT direction semantics); Panel B renders the scored-name
// breadth (n); Panel C renders the monthly Spearman rank autocorrelation of
// scores on overlapping tickers as one line per region on a shared month axis
// (nulls honestly break the line; dashed references at 0 and 0.5). US / CN
// side by side for A/B, deterministic layout computed from the committed panel
// at render (SSG build time), full <table> fallback per figure (column headers
// always render, honest empty state).
//
// Red lines honored: no --up/--down or red/green direction encoding (the
// region accents are the approved blue/orange pair), no Date.now /
// Math.random, no investment advice — measurement only.

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  DiagramFigure,
  niceTicks,
  scaleLinear,
} from "@/components/diagram/primitives";
import { diagram, divergingScale } from "@/components/diagram/tokens";
import { aionis, type ScoreDiagnosticsRow } from "@/data/aionis";
import { useI18n } from "@/i18n/provider";
import { fmtEmpty } from "@/lib/format";

// Region order follows the panel's own sort (month asc, region lexicographic);
// labels are literal locale-neutral tokens (force-camp precedent).
const REGIONS = ["cn", "us"] as const;

// The warm end of the approved colorblind-safe diverging scale (editorial
// accent orange) — used as the CN category accent, NOT as a direction
// semantic. US keeps the primary ink-blue; the pair stays distinguishable in
// both themes (2026-08-16 contrast audit).
const ACCENT_WARM = divergingScale[divergingScale.length - 1];

// Per-panel SVG geometry (viewBox units; ~2.5:1 aspect keeps rendered height
// in the 180–220px band at two-column widths — divergence precedent).
const VB_W = 520;
const VB_WIDE = 1000; // inertia panel: both regions share one month axis
const VB_H = 210;
const M_L = 32;
const M_R = 6;
const PLOT_TOP = 8;
const PLOT_BOTTOM = VB_H - 24;

// The i18n provider's t() is a plain key lookup; dict values carry {var}
// placeholders, so interpolation is applied here (divergence precedent).
function fmtTpl(tpl: string, p: Record<string, string | number>): string {
  return tpl.replace(/\{(\w+)\}/g, (m, k: string) => (k in p ? String(p[k]) : m));
}

// Deterministic ascending month order (byte compare — ISO-like keys sort
// chronologically; no locale-dependent collation).
const byMonthAsc = (a: ScoreDiagnosticsRow, b: ScoreDiagnosticsRow) =>
  a.month < b.month ? -1 : a.month > b.month ? 1 : 0;

type RegionSeries = {
  label: string;
  rows: ScoreDiagnosticsRow[];
  start: string;
  end: string;
};

function prepRegion(rows: ScoreDiagnosticsRow[]): RegionSeries[] {
  return REGIONS.map((region) => {
    const rs = rows.filter((r) => r.region === region).sort(byMonthAsc);
    return {
      label: region.toUpperCase(),
      rows: rs,
      start: rs[0]?.month ?? "—",
      end: rs.at(-1)?.month ?? "—",
    };
  });
}

// Tick label decimals from the tick step (integers for breadth, more for
// dispersion) — deterministic from data.
function tickDecimals(ticks: number[]): number {
  const step = ticks.length > 1 ? ticks[1] - ticks[0] : 1;
  return step >= 1 ? 0 : step >= 0.09 ? 1 : step >= 0.009 ? 2 : 3;
}

// Shared deterministic frame: horizontal gridlines + y labels + baseline +
// sparse x labels (every 6th month). All coordinates are build-time constants.
function PanelFrame({
  months,
  vbW,
  y,
  yTicks,
  yDecimals,
}: {
  months: string[];
  vbW: number;
  y: (v: number) => number;
  yTicks: number[];
  yDecimals: number;
}) {
  const n = months.length;
  const step = n > 0 ? (vbW - M_L - M_R) / n : vbW - M_L - M_R;
  return (
    <g>
      {yTicks.map((v) => (
        <g key={`yt-${v}`}>
          <line
            x1={M_L}
            x2={vbW - M_R}
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
        x2={vbW - M_R}
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

// Panel A — monthly cross-sectional score dispersion: std as a bar, IQR as a
// thin line. Both are magnitudes of spread; no direction color is involved.
function DispersionPanel({ p }: { p: RegionSeries }) {
  const n = p.rows.length;
  const step = n > 0 ? (VB_W - M_L - M_R) / n : VB_W - M_L - M_R;
  const bw = Math.min(12, step * 0.62);
  const yMax = Math.max(0.1, ...p.rows.map((r) => Math.max(r.score_std, r.score_iqr)));
  const ticks = niceTicks(0, yMax);
  const dec = tickDecimals(ticks);
  const y = scaleLinear([0, yMax], [PLOT_BOTTOM, PLOT_TOP]);
  const iqrPath = p.rows
    .map((r, i) => `${i === 0 ? "M" : "L"} ${M_L + (i + 0.5) * step} ${y(r.score_iqr)}`)
    .join(" ");
  return (
    <div>
      <div className="flex items-baseline justify-between gap-2">
        <p className="text-[13px] font-semibold">{p.label}</p>
        <p className="font-mono text-[11px] text-muted-foreground">y-max {yMax.toFixed(dec)}</p>
      </div>
      <svg
        viewBox={`0 0 ${VB_W} ${VB_H}`}
        className="mt-1 h-auto w-full"
        role="img"
        aria-label={p.label}
      >
        <PanelFrame
          months={p.rows.map((r) => r.month)}
          vbW={VB_W}
          y={y}
          yTicks={ticks}
          yDecimals={dec}
        />
        <g>
          {p.rows.map((r, i) => (
            <rect
              key={`std-${r.month}`}
              x={M_L + (i + 0.5) * step - bw / 2}
              y={y(r.score_std)}
              width={bw}
              height={PLOT_BOTTOM - y(r.score_std)}
              fill={diagram.primary}
              fillOpacity={0.5}
            />
          ))}
        </g>
        {n > 0 ? (
          <path d={iqrPath} fill="none" stroke={diagram.ink} strokeWidth={1.1} />
        ) : null}
      </svg>
    </div>
  );
}

// Panel B — universe breadth: scored names per month (n) as bars.
function BreadthPanel({ p }: { p: RegionSeries }) {
  const n = p.rows.length;
  const step = n > 0 ? (VB_W - M_L - M_R) / n : VB_W - M_L - M_R;
  const bw = Math.min(12, step * 0.62);
  const nMax = Math.max(1, ...p.rows.map((r) => r.n));
  const ticks = niceTicks(0, nMax);
  const dec = tickDecimals(ticks);
  const y = scaleLinear([0, nMax], [PLOT_BOTTOM, PLOT_TOP]);
  return (
    <div>
      <div className="flex items-baseline justify-between gap-2">
        <p className="text-[13px] font-semibold">{p.label}</p>
        <p className="font-mono text-[11px] text-muted-foreground">n-max {nMax}</p>
      </div>
      <svg
        viewBox={`0 0 ${VB_W} ${VB_H}`}
        className="mt-1 h-auto w-full"
        role="img"
        aria-label={p.label}
      >
        <PanelFrame
          months={p.rows.map((r) => r.month)}
          vbW={VB_W}
          y={y}
          yTicks={ticks}
          yDecimals={dec}
        />
        <g>
          {p.rows.map((r, i) => (
            <rect
              key={`n-${r.month}`}
              x={M_L + (i + 0.5) * step - bw / 2}
              y={y(r.n)}
              width={bw}
              height={PLOT_BOTTOM - y(r.n)}
              fill={diagram.primary}
              fillOpacity={0.5}
            />
          ))}
        </g>
      </svg>
    </div>
  );
}

// Panel C — score inertia: monthly Spearman rank autocorrelation, one line per
// region on the union month axis. A null (overlap < 30, first month, or a
// degenerate cross-section) honestly breaks the line; dashed references at 0
// and 0.5 make the "how much rank memory" reading direct.
function InertiaPanel({
  series,
  months,
}: {
  series: RegionSeries[];
  months: string[];
}) {
  const plotW = VB_WIDE - M_L - M_R;
  const step = months.length > 0 ? plotW / months.length : plotW;
  const monthIdx = new Map(months.map((m, i) => [m, i]));
  const vals = series.flatMap((s) =>
    s.rows.map((r) => r.rank_autocorr).filter((v): v is number => v !== null),
  );
  const yMin = Math.min(0, ...vals);
  const yMax = Math.max(0.55, ...vals);
  const ticks = niceTicks(yMin, yMax);
  const dec = tickDecimals(ticks);
  const y = scaleLinear([yMin, yMax], [PLOT_BOTTOM, PLOT_TOP]);
  const accents = [ACCENT_WARM, diagram.primary]; // matches REGIONS = [cn, us]
  return (
    <div>
      <svg
        viewBox={`0 0 ${VB_WIDE} ${VB_H}`}
        className="h-auto w-full"
        role="img"
        aria-label="rank autocorrelation"
      >
        <PanelFrame
          months={months}
          vbW={VB_WIDE}
          y={y}
          yTicks={ticks}
          yDecimals={dec}
        />
        {/* 0 and 0.5 dashed references (0 coincides with the baseline when in range) */}
        {[0, 0.5].map((v) =>
          v > yMin && v < yMax ? (
            <g key={`ref-${v}`}>
              <line
                x1={M_L}
                x2={VB_WIDE - M_R}
                y1={y(v)}
                y2={y(v)}
                stroke={diagram.ink}
                strokeDasharray="6 4"
                strokeOpacity={0.55}
              />
              <text
                x={VB_WIDE - M_R}
                y={y(v) - 3}
                textAnchor="end"
                fontSize={9}
                fill={diagram.muted}
                className="font-mono"
              >
                {v.toFixed(1)}
              </text>
            </g>
          ) : null,
        )}
        {series.map((s, si) => {
          const pt = (r: ScoreDiagnosticsRow) => ({
            x: M_L + ((monthIdx.get(r.month) ?? 0) + 0.5) * step,
            y: y(r.rank_autocorr ?? 0),
          });
          const segments: string[] = [];
          let cur: string | null = null;
          s.rows.forEach((r, i) => {
            if (r.rank_autocorr === null) {
              cur = null;
              return;
            }
            const { x, y: py } = pt(r);
            cur = cur === null ? `M ${x} ${py}` : `${cur} L ${x} ${py}`;
            if (i === s.rows.length - 1 || s.rows[i + 1].rank_autocorr === null) {
              segments.push(cur);
              cur = null;
            }
          });
          return (
            <g key={s.label}>
              {segments.map((d, i) => (
                <path
                  key={`seg-${s.label}-${i}`}
                  d={d}
                  fill="none"
                  stroke={accents[si]}
                  strokeWidth={1.6}
                />
              ))}
              {s.rows.map((r) =>
                r.rank_autocorr === null ? null : (
                  <circle
                    key={`dot-${s.label}-${r.month}`}
                    cx={pt(r).x}
                    cy={pt(r).y}
                    r={1.7}
                    fill={accents[si]}
                  />
                ),
              )}
            </g>
          );
        })}
      </svg>
      <div className="mt-1 flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-muted-foreground">
        {series.map((s, si) => (
          <span key={`leg-${s.label}`} className="inline-flex items-center gap-1.5">
            <svg width={18} height={8} aria-hidden="true">
              <line
                x1={0}
                y1={4}
                x2={18}
                y2={4}
                stroke={accents[si]}
                strokeWidth={1.6}
              />
            </svg>
            {s.label}
          </span>
        ))}
      </div>
    </div>
  );
}

// Full data-table fallbacks (headers always render, honest empty state).
function PanelTable({
  title,
  headers,
  rows,
}: {
  title: string;
  headers: string[];
  rows: { key: string; cells: (string | null)[] }[];
}) {
  return (
    <div className="space-y-4">
      <p className="text-xs font-semibold">{title}</p>
      <table className="mt-1 w-full text-left text-[12px]">
        <thead>
          <tr className="text-muted-foreground">
            {headers.map((h, i) => (
              <th
                key={h}
                className={`border-b border-border px-3 py-1.5 font-medium ${
                  i === 0 ? "text-left" : "text-right"
                }`}
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.key} className="border-t border-border">
              {r.cells.map((c, i) => (
                <td
                  key={i}
                  className={`px-3 py-1 font-mono text-[11px] tabular-nums ${
                    i === 0 ? "text-left" : "text-right text-muted-foreground"
                  }`}
                >
                  {c ?? fmtEmpty(null)}
                </td>
              ))}
            </tr>
          ))}
          {rows.length === 0 ? (
            <tr className="border-t border-border">
              <td
                colSpan={headers.length}
                className="px-3 py-4 text-center text-muted-foreground"
              >
                {fmtEmpty(null)}
              </td>
            </tr>
          ) : null}
        </tbody>
      </table>
    </div>
  );
}

export default function AtlasDiagnostics() {
  const { t } = useI18n();
  const series = prepRegion(aionis.scoreDiagnostics);

  // Union month axis (deterministic ascending) for the shared inertia panel.
  const months = [
    ...new Set(aionis.scoreDiagnostics.map((r) => r.month)),
  ].sort((a, b) => (a < b ? -1 : a > b ? 1 : 0));

  const countsLine = series
    .map(
      (p) =>
        `${p.label} ${fmtTpl(t("atlas.diag.n"), { n: p.rows.length, start: p.start, end: p.end })}`,
    )
    .join(" · ");

  const tableDisp = (
    <PanelTable
      title={`${t("atlas.diag.table")} — ${t("atlas.diag.disp.title")}`}
      headers={["month", "region", "n", "score_mean", "score_std", "score_iqr"]}
      rows={aionis.scoreDiagnostics.map((r) => ({
        key: `${r.month}-${r.region}`,
        cells: [
          r.month,
          r.region,
          String(r.n),
          r.score_mean.toFixed(6),
          r.score_std.toFixed(6),
          r.score_iqr.toFixed(6),
        ],
      }))}
    />
  );

  const tableBreadth = (
    <PanelTable
      title={`${t("atlas.diag.table")} — ${t("atlas.diag.breadth.title")}`}
      headers={["month", "region", "n"]}
      rows={aionis.scoreDiagnostics.map((r) => ({
        key: `${r.month}-${r.region}`,
        cells: [r.month, r.region, String(r.n)],
      }))}
    />
  );

  const tableInertia = (
    <PanelTable
      title={`${t("atlas.diag.table")} — ${t("atlas.diag.ac.title")}`}
      headers={["month", "region", "rank_autocorr"]}
      rows={aionis.scoreDiagnostics.map((r) => ({
        key: `${r.month}-${r.region}`,
        cells: [
          r.month,
          r.region,
          r.rank_autocorr === null ? null : r.rank_autocorr.toFixed(6),
        ],
      }))}
    />
  );

  return (
    <Card>
      <CardHeader>
        <CardTitle as="h2">{t("atlas.diag.title")}</CardTitle>
        <CardDescription>{t("atlas.diag.desc")}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-8">
        {/* Panel A — monthly score dispersion (std bars + IQR line, US / CN). */}
        <DiagramFigure
          title={t("atlas.diag.disp.title")}
          desc={t("atlas.diag.disp.desc")}
          caption={countsLine}
          table={tableDisp}
        >
          <div className="grid gap-6 md:grid-cols-2">
            {series.map((p) => (
              <DispersionPanel key={`disp-${p.label}`} p={p} />
            ))}
          </div>
          <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-muted-foreground">
            <span className="inline-flex items-center gap-1.5">
              <svg width={18} height={10} aria-hidden="true">
                <rect x={0} y={1} width={18} height={8} fill={diagram.primary} fillOpacity={0.5} />
              </svg>
              score_std
            </span>
            <span className="inline-flex items-center gap-1.5">
              <svg width={18} height={10} aria-hidden="true">
                <line x1={0} y1={5} x2={18} y2={5} stroke={diagram.ink} strokeWidth={1.1} />
              </svg>
              score_iqr
            </span>
          </div>
        </DiagramFigure>

        {/* Panel B — universe breadth (n per month, US / CN). */}
        <DiagramFigure
          title={t("atlas.diag.breadth.title")}
          desc={t("atlas.diag.breadth.desc")}
          table={tableBreadth}
        >
          <div className="grid gap-6 md:grid-cols-2">
            {series.map((p) => (
              <BreadthPanel key={`breadth-${p.label}`} p={p} />
            ))}
          </div>
        </DiagramFigure>

        {/* Panel C — score inertia (rank autocorrelation lines, 0 / 0.5 refs). */}
        <DiagramFigure
          title={t("atlas.diag.ac.title")}
          desc={t("atlas.diag.ac.desc")}
          table={tableInertia}
        >
          <InertiaPanel series={series} months={months} />
        </DiagramFigure>
      </CardContent>
    </Card>
  );
}
