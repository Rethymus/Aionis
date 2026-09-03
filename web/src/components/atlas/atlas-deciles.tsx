"use client";

// /atlas section 5 (P1-6 R1-full, adjudicated GO 2026-09-02) — decile
// monotonicity of the frozen OOS score surface (display lane, zero fetches):
// for each frozen (month, region) cross-section the exporter ranks scores
// into ten equal-count deciles and reports each decile's mean realized
// forward return over the next h=21 sessions — the SAME frozen
// close-to-close convention as the training label y_fwd_ret
// (aionis.icDeciles → ic_deciles.json). Panel A: grouped decile-mean bars
// for the latest realized month, ONE sub-panel per region (us | cn), side by
// side like the diagnostics panels. Panel B: the D10 − D1 spread series for
// both regions on ONE shared month axis. All values verbatim from the
// committed panel; deterministic layout computed at SSG build time; full
// data tables under every figure (headers always render — the house
// honesty pattern).
//
// Red lines honored: NO red/green or up/down direction encoding (a decile
// return is a measurement, not advice) — region accents are the approved
// ink-blue / warm-orange pair; the zero line is a solid ink reference among
// dashed gridlines; no Date.now / Math.random.

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  DiagramFigure,
  niceTicks,
  scaleLinear,
} from "@/components/diagram/primitives";
import { diagram, divergingScale } from "@/components/diagram/tokens";
import { aionis, type IcDecilesRow } from "@/data/aionis";
import { useI18n } from "@/i18n/provider";
import { FrostedScrollArea } from "@/components/ui/frosted-scroll-area";

// Region order follows the divergence precedent (us first); labels are
// literal locale-neutral tokens.
const REGIONS = ["us", "cn"] as const;
type Region = (typeof REGIONS)[number];

// CN category accent: the COOL end of the approved colorblind-safe diverging
// scale — giving the documented blue/orange category pair (NOT a direction
// semantic; the warm tail is reserved for out-of-band flags in the
// divergence block, and a rust tone could be misread as a down-direction).
// US keeps the primary ink; the pair stays distinguishable in both themes.
const ACCENT: Record<Region, string> = {
  us: diagram.primary,
  cn: divergingScale[0],
};

// Per-panel SVG geometry (viewBox units; ~2.5:1 aspect keeps rendered height
// in the spec's 180–220px band at two-column widths — siblings' constants).
const VB_W = 520;
const VB_H = 210;
const M_L = 32;
const M_R = 6;
const PLOT_TOP = 8;
const PLOT_BOTTOM = VB_H - 24;
const PLOT_W = VB_W - M_L - M_R;
// Shared wide axis for the spread series (both regions, one month grid) —
// diagnostics' inertia-panel precedent.
const VB_WIDE = 1000;
const PLOT_WIDE = VB_WIDE - M_L - M_R;

// Deterministic ascending month order (byte compare — ISO-like keys sort
// chronologically; no locale-dependent collation).
const byMonthAsc = (a: IcDecilesRow, b: IcDecilesRow) =>
  a.month < b.month ? -1 : a.month > b.month ? 1 : 0;

// Full data-table fallback (headers always render — PanelTable precedent).
function DecileTable({
  title,
  rows,
  monthHeader,
}: {
  title: string;
  rows: IcDecilesRow[];
  monthHeader: string;
}) {
  return (
    <FrostedScrollArea maxHeight={320} label={title}>
      <div className="space-y-4">
        <p className="text-xs font-semibold">{title}</p>
        <table className="mt-1 w-full text-left text-[12px]">
        <thead>
          <tr className="text-muted-foreground">
            <th className="border-b border-border px-3 py-1.5 font-medium">
              {monthHeader}
            </th>
            {Array.from({ length: 10 }, (_, d) => (
              <th
                key={d}
                className="border-b border-border px-2 py-1.5 text-right font-medium"
              >
                D{d + 1}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={`${r.region}-${r.month}`} className="border-t border-border">
              <td className="px-3 py-1 font-mono text-[11px]">
                {r.region} · {r.month}
                {r.realized ? "" : " (—)"}
              </td>
              {Array.from({ length: 10 }, (_, d) => (
                <td
                  key={d}
                  className="px-2 py-1 text-right font-mono text-[11px] tabular-nums text-muted-foreground"
                >
                  {r.realized ? (r.decile_mean_fwd_ret[d]?.toFixed(4) ?? "—") : "—"}
                </td>
              ))}
            </tr>
          ))}
          </tbody>
        </table>
      </div>
    </FrostedScrollArea>
  );
}

export default function AtlasDeciles() {
  const { t } = useI18n();
  const rows: IcDecilesRow[] = aionis.icDeciles ?? [];

  const byRegion: Record<Region, IcDecilesRow[]> = { us: [], cn: [] };
  for (const r of rows) {
    if (r.region === "us" || r.region === "cn") byRegion[r.region].push(r);
  }
  for (const k of REGIONS) byRegion[k].sort(byMonthAsc);

  // Latest realized month per region (the frozen surface's honest extent —
  // months past the panel edge carry realized:false and stay out of Panel A).
  const latest: Partial<Record<Region, IcDecilesRow>> = {};
  for (const reg of REGIONS) {
    const realized = byRegion[reg].filter((r) => r.realized);
    if (realized.length) latest[reg] = realized[realized.length - 1];
  }

  // Panel A: symmetric y domain across BOTH regions' latest months so the
  // side-by-side bars share one comparable scale (diagnostics precedent).
  const aVals = REGIONS.flatMap((reg) =>
    (latest[reg]?.decile_mean_fwd_ret ?? []).filter(
      (v): v is number => v != null,
    ),
  );
  const aAbsMax = Math.max(0.01, ...aVals.map((v) => Math.abs(v)));
  const aTicks = niceTicks(-aAbsMax, aAbsMax);
  const ay = scaleLinear([-aAbsMax, aAbsMax], [PLOT_BOTTOM, PLOT_TOP]);

  // Panel B: D10 − D1 spread series per region on ONE shared month grid —
  // y domain always spans 0 (the null verdict's reference).
  const spreadBy: Partial<Record<Region, { month: string; v: number }[]>> = {};
  for (const reg of REGIONS) {
    spreadBy[reg] = byRegion[reg]
      .filter((r) => r.realized && r.d10_minus_d1 != null)
      .map((r) => ({ month: r.month, v: r.d10_minus_d1 as number }));
  }
  const months = Array.from(
    new Set(REGIONS.flatMap((reg) => (spreadBy[reg] ?? []).map((p) => p.month))),
  ).sort();
  const allSpreads = REGIONS.flatMap((reg) => (spreadBy[reg] ?? []).map((p) => p.v));
  const bTicks = allSpreads.length
    ? niceTicks(Math.min(0, ...allSpreads), Math.max(0, ...allSpreads))
    : [];
  const bLo = bTicks.length ? bTicks[0] : -0.05;
  const bHi = bTicks.length ? bTicks[bTicks.length - 1] : 0.05;
  const by = scaleLinear([bLo, bHi], [PLOT_BOTTOM, PLOT_TOP]);
  const bStep = months.length > 0 ? PLOT_WIDE / months.length : PLOT_WIDE;
  const bx = (m: string) => M_L + (months.indexOf(m) + 0.5) * bStep;

  const realizedCount = rows.filter((r) => r.realized).length;
  const coverageLine = (t("atlas.deciles.coverage") as string)
    .replace("{realized}", String(realizedCount))
    .replace("{total}", String(rows.length));

  const tableBlock = (
    <DecileTable
      title={t("atlas.deciles.tableTitle")}
      rows={REGIONS.flatMap((reg) => byRegion[reg].slice(-24))}
      monthHeader={t("atlas.deciles.tableMonth")}
    />
  );

  return (
    <Card>
      <CardHeader>
        <CardTitle as="h2">{t("atlas.deciles.title")}</CardTitle>
        <CardDescription>{t("atlas.deciles.desc")}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-8">
        <p className="text-xs text-muted-foreground">
          {t("atlas.deciles.alignment")}
        </p>

        {/* Panel A — grouped decile bars, latest realized month, US | CN. */}
        <DiagramFigure
          title={t("atlas.deciles.panelA")}
          desc={t("atlas.deciles.panelADesc")}
          caption={coverageLine}
          table={tableBlock}
        >
          <div className="grid gap-6 md:grid-cols-2">
            {REGIONS.map((reg) => {
              const r = latest[reg];
              const n = r?.n ?? 0;
              return (
                <div key={`dec-${reg}`}>
                  <p className="text-[13px] font-semibold">
                    {reg.toUpperCase()}
                  </p>
                  <p className="font-mono text-[11px] text-muted-foreground">
                    {r
                      ? `${r.month} · n=${n}`
                      : t("atlas.deciles.noRealized")}
                  </p>
                  <svg
                    viewBox={`0 0 ${VB_W} ${VB_H}`}
                    className="mt-1 h-auto w-full"
                    role="img"
                    aria-label={`${reg} decile means`}
                  >
                    {aTicks.map((v) => (
                      <g key={`ay-${v}`}>
                        <line
                          x1={M_L}
                          x2={VB_W - M_R}
                          y1={ay(v)}
                          y2={ay(v)}
                          stroke={diagram.border}
                          strokeDasharray={v === 0 ? undefined : "2 4"}
                        />
                        <text
                          x={M_L - 4}
                          y={ay(v) + 3}
                          textAnchor="end"
                          fontSize={9}
                          fill={diagram.muted}
                          className="font-mono"
                        >
                          {(v * 100).toFixed(1)}%
                        </text>
                      </g>
                    ))}
                    {r?.decile_mean_fwd_ret.map((v, i) => {
                      if (v == null) return null;
                      const band = PLOT_W / 10;
                      const bw = band * 0.6;
                      const y0 = Math.min(ay(0), ay(v));
                      const h = Math.max(Math.abs(ay(v) - ay(0)), 1);
                      return (
                        <rect
                          key={`bar-${i}`}
                          x={M_L + (i + 0.5) * band - bw / 2}
                          y={y0}
                          width={bw}
                          height={h}
                          fill={ACCENT[reg]}
                          fillOpacity={0.85}
                        />
                      );
                    })}
                    {Array.from({ length: 10 }, (_, i) => (
                      <text
                        key={`ax-${i}`}
                        x={M_L + (i + 0.5) * (PLOT_W / 10)}
                        y={VB_H - 8}
                        textAnchor="middle"
                        fontSize={9}
                        fill={diagram.muted}
                        className="font-mono"
                      >
                        D{i + 1}
                      </text>
                    ))}
                  </svg>
                </div>
              );
            })}
          </div>
          <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-muted-foreground">
            {REGIONS.map((reg) => (
              <span key={`lg-${reg}`} className="inline-flex items-center gap-1.5">
                <svg width={18} height={10} aria-hidden="true">
                  <rect
                    x={0}
                    y={1}
                    width={18}
                    height={8}
                    fill={ACCENT[reg]}
                    fillOpacity={0.85}
                  />
                </svg>
                {reg.toUpperCase()}
              </span>
            ))}
          </div>
        </DiagramFigure>

        {/* Panel B — D10 − D1 spread, both regions on one shared month axis. */}
        <DiagramFigure
          title={t("atlas.deciles.spread.title")}
          desc={t("atlas.deciles.spread.desc")}
        >
          {months.length >= 2 ? (
            <svg
              viewBox={`0 0 ${VB_WIDE} ${VB_H}`}
              className="h-auto w-full"
              role="img"
              aria-label={t("atlas.deciles.spread.title")}
            >
              {bTicks.map((v) => (
                <g key={`by-${v}`}>
                  <line
                    x1={M_L}
                    x2={VB_WIDE - M_R}
                    y1={by(v)}
                    y2={by(v)}
                    stroke={diagram.border}
                    strokeDasharray={v === 0 ? undefined : "2 4"}
                  />
                  <text
                    x={M_L - 4}
                    y={by(v) + 3}
                    textAnchor="end"
                    fontSize={9}
                    fill={diagram.muted}
                    className="font-mono"
                  >
                    {(v * 100).toFixed(1)}%
                  </text>
                </g>
              ))}
              {REGIONS.map((reg) => {
                const pts = (spreadBy[reg] ?? []).map(
                  (p) => `${bx(p.month)},${by(p.v)}`,
                );
                if (pts.length < 2) return null;
                return (
                  <polyline
                    key={`sp-${reg}`}
                    points={pts.join(" ")}
                    fill="none"
                    stroke={ACCENT[reg]}
                    strokeWidth={1.6}
                    strokeLinejoin="round"
                  />
                );
              })}
              {months.map(
                (mo, i) =>
                  i % 6 === 0 ? (
                    <text
                      key={`bm-${mo}`}
                      x={M_L + (i + 0.5) * bStep}
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
            </svg>
          ) : (
            <p className="p-4 text-xs text-muted-foreground">
              {t("atlas.deciles.spread.empty")}
            </p>
          )}
        </DiagramFigure>
      </CardContent>
    </Card>
  );
}
