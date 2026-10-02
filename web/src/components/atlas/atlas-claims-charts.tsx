"use client";

// Claims chart figures (round 119 surgical split, divergence round-118
// recipe): the two SVG bodies hydrate from an async chunk (dynamic ssr:false)
// while their DiagramFigure wrappers — captions, table fallbacks, headers —
// stay SSR in atlas-claims.tsx (content-first). Both blocks below are SLICED
// VERBATIM from the pre-split file (byte-stability discipline); only the
// enclosing function shells are new.

import { divergingColor, divergingIndex, divergingScale, diagram } from "@/components/diagram/tokens";
import { niceTicks, scaleLinear } from "@/components/diagram/primitives";
import { aionis } from "@/data/aionis";
import { useI18n } from "@/i18n/provider";
import { isNum, fmt, tf } from "./atlas-claims-prep";

// --- pivot geometry + helpers (verbatim constants from the pre-split file) ---
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

// --- forest geometry (verbatim constants) ---
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

/** Block A figure body: the IC pivot heatmap grid (sliced verbatim). */
export function ClaimsPivotChart() {
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
  return (
    <>
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
    </>
  );
}

/** Block B figure body: the forest plot + legends + context line (verbatim). */
export function ClaimsForestChart() {
  const { t } = useI18n();
  const m = aionis.metrics;
  const x = scaleLinear(F_DOMAIN, [F_ML, F_W - F_MR]);
  const hasPoint = isNum(m.combined_ic);
  const hasCi = isNum(m.ci_lo) && isNum(m.ci_hi);
  const hasSesoi = isNum(m.sesoi);
  const sesoiLabel = tf(t("atlas.forest.sesoi"), { v: fmt(m.sesoi, 2) });
  // TASK-DISP-G1 — display-derived t for the literature-context line (the
  // wrapper's verdict/caption math stays SSR in the parent).
  const se = hasCi ? (m.ci_hi - m.ci_lo) / (2 * 1.96) : null;
  const derivedT =
    se !== null && se > 0 && hasPoint ? m.combined_ic / se : null;
  const contextLine =
    derivedT !== null
      ? tf(t("atlas.forest.context"), { t: fmt(derivedT, 2) })
      : null;
  return (
    <>
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
    </>
  );
}
