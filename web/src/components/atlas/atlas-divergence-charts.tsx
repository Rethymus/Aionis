"use client";

// Divergence chart figures (round 118 surgical split): the SVG panels moved
// out of atlas-divergence.tsx into this dynamically-imported module so their
// hydration leaves the page's critical path (the round-117 ablation measured
// the divergence section at ~830-1,770ms of atlas TBT; the TABLE fallbacks —
// the section's text content — stay SSR in the parent, honoring the
// content-first constraint). Charts are pure visuals: the data lives in the
// committed tables/panels, so ssr:false costs no content.

import { niceTicks, scaleLinear } from "@/components/diagram/primitives";
import { diagram, divergingScale } from "@/components/diagram/tokens";
import { useI18n } from "@/i18n/provider";
import { fmtEmpty } from "@/lib/format";
import type { RegionPrep } from "./atlas-divergence-prep";
import { fmtTpl } from "./atlas-divergence-prep";

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

// Shared deterministic frame: horizontal gridlines + y labels + baseline +
// sparse x labels (every 6th month) — copied VERBATIM from the pre-split
// atlas-divergence.tsx (chart byte-stability discipline).
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

/** Block A figure body: US/CN probability-band panels + legend. */
export function DivergenceBlockAFigure({ panels }: { panels: RegionPrep[] }) {
  const { t } = useI18n();
  return (
    <>
      <div className="grid gap-6 md:grid-cols-2">
        {panels.map((p) => (
          <BandPanel key={`band-${p.label}`} p={p} />
        ))}
      </div>
      <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-muted-foreground">
        <span className="inline-flex items-center gap-1.5">
          <svg width={18} height={10} aria-hidden="true">
            <rect x={0} y={1} width={18} height={8} fill={diagram.primary} fillOpacity={0.22} />
          </svg>
          {t("atlas.div.band")}
        </span>
        <span className="inline-flex items-center gap-1.5">
          <svg width={10} height={10} aria-hidden="true">
            <circle cx={5} cy={5} r={3.2} fill={diagram.primary} stroke={diagram.card} strokeWidth={0.8} />
          </svg>
          {t("atlas.div.realized")}
        </span>
        <span className="inline-flex items-center gap-1.5">
          <svg width={10} height={10} aria-hidden="true">
            <circle cx={5} cy={5} r={3.2} fill={diagram.card} stroke={OUT_DOT} strokeWidth={1.6} />
          </svg>
          out-of-band
        </span>
      </div>
    </>
  );
}

/** Block B figure body: US/CN monthly ECE bars + pooled reference. */
export function DivergenceBlockBFigure({ panels }: { panels: RegionPrep[] }) {
  return (
    <div className="grid gap-6 md:grid-cols-2">
      {panels.map((p) => (
        <EcePanel key={`ece-${p.label}`} p={p} />
      ))}
    </div>
  );
}
