"use client";

// /atlas section 5 (P1-6 R1-full, adjudicated GO 2026-09-02) — decile
// monotonicity of the frozen OOS score surface (display lane, zero fetches):
// for each frozen (month, region) cross-section the panel ranks scores into
// ten equal-count deciles and reports each decile's mean realized forward
// return over the next h=21 sessions — the SAME frozen close-to-close
// convention as the training label y_fwd_ret, so the readout is arithmetically
// comparable to the headline IC. Panel A: per-decile mean forward return as a
// grouped bar pair (CN | US) for the LATEST realized month per region;
// Panel B: the D10−D1 spread time series per region (nulls honestly break the
// line at the panel edge / missing CN panel). All values verbatim from
// aionis.icDeciles (web/src/data/aionis/ic_deciles.json).
//
// Red lines honored: NO direction coloring on the bars (a decile return is a
// measurement, not advice) — bars use the region accents (ink-blue / warm
// orange); the zero line is a dashed ink reference. No Date.now /
// Math.random; deterministic layout from the committed panel (SSG build
// time); full <table> fallback per figure.

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { DiagramFigure } from "@/components/diagram/primitives";
import { diagram } from "@/components/diagram/tokens";
import { aionis, type IcDecilesRow } from "@/data/aionis";
import { useI18n } from "@/i18n/provider";

const REGIONS = ["cn", "us"] as const;
const ACCENT_WARM = "#b45309"; // approved warm accent (diagram.diverging tail family)

type Row = IcDecilesRow;

const byMonthAsc = (a: Row, b: Row) => (a.month < b.month ? -1 : a.month > b.month ? 1 : 0);

function latestRealized(rows: Row[]): Row | undefined {
  const realized = rows.filter((r) => r.realized);
  return realized.length ? realized[realized.length - 1] : undefined;
}

export default function AtlasDeciles() {
  const { t } = useI18n();
  const rows: Row[] = aionis.icDeciles ?? [];
  const realizedCount = rows.filter((r) => r.realized).length;
  const byRegion: Record<string, Row[]> = { cn: [], us: [] };
  for (const r of rows) (byRegion[r.region] ??= []).push(r);
  for (const k of Object.keys(byRegion)) byRegion[k].sort(byMonthAsc);

  const latest: Partial<Record<string, Row>> = {};
  for (const reg of REGIONS) latest[reg] = latestRealized(byRegion[reg]);

  const spreadSeries = REGIONS.map((reg) => ({
    region: reg,
    points: byRegion[reg]
      .filter((r) => r.realized && r.d10_minus_d1 != null)
      .map((r) => ({ month: r.month, v: r.d10_minus_d1 as number })),
  })).filter((s) => s.points.length >= 2);

  const allSpreads = spreadSeries.flatMap((s) => s.points.map((p) => p.v));
  const sMin = allSpreads.length ? Math.min(...allSpreads) : -0.05;
  const sMax = allSpreads.length ? Math.max(...allSpreads) : 0.05;
  const pad = Math.max((sMax - sMin) * 0.1, 0.01);
  const lo = sMin - pad;
  const hi = sMax + pad;

  // Panel A geometry: grouped decile bars for the latest realized month.
  const VB_W = 520;
  const VB_H = 210;
  const M_L = 44;
  const M_R = 8;
  const plotW = VB_W - M_L - M_R;
  const bandW = plotW / 10;
  const aVals = REGIONS.flatMap((reg) =>
    latest[reg]?.decile_mean_fwd_ret ?? [],
  ).filter((v): v is number => v != null);
  const aAbsMax = Math.max(0.01, ...aVals.map((v) => Math.abs(v)));
  const yFor = (v: number) => {
    const h = VB_H - 46;
    const mid = 24 + h / 2;
    return mid - (v / aAbsMax) * (h / 2);
  };
  const zeroY = yFor(0);

  const fmtPct = (v: number | null | undefined) =>
    v == null ? "—" : `${(v * 100).toFixed(2)}%`;

  return (
    <Card>
      <CardHeader className="border-b">
        <CardTitle className="text-base">{t("deciles.title")}</CardTitle>
        <CardDescription>{t("deciles.subtitle")}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4 p-4">
        <p className="text-xs text-muted-foreground">
          {t("deciles.alignmentNote")}
        </p>

        <div className="grid gap-4 md:grid-cols-2">
          {REGIONS.map((reg) => {
            const r = latest[reg];
            return (
              <DiagramFigure
                key={reg}
                title={t("deciles.panelA")}
                desc={t("deciles.alignmentNote")}
                caption={(t("deciles.panelACaption") as string).replace(
                  "{month}",
                  r?.month ?? "—",
                )}
                table={
                  <table className="w-full text-xs">
                    <thead>
                      <tr>
                        <th className="text-left">D1…D10</th>
                        <th className="text-right">{t("deciles.meanFwd")}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(r?.decile_mean_fwd_ret ?? []).map((v, i) => (
                        <tr key={i}>
                          <td>D{i + 1}</td>
                          <td className="text-right tabular-nums">{fmtPct(v)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                }
              >
                <svg viewBox={`0 0 ${VB_W} ${VB_H}`} role="img" aria-label={t("deciles.panelA")}>
                  <line
                    x1={M_L} x2={VB_W - M_R} y1={zeroY} y2={zeroY}
                    stroke={diagram.border} strokeWidth={1} strokeDasharray="3 3"
                  />
                  {r?.decile_mean_fwd_ret.map((v, i) => {
                    if (v == null) return null;
                    const y0 = Math.min(zeroY, yFor(v));
                    const h = Math.max(Math.abs(yFor(v) - zeroY), 1);
                    return (
                      <rect
                        key={i}
                        x={M_L + i * bandW + bandW * 0.2}
                        y={y0}
                        width={bandW * 0.6}
                        height={h}
                        fill={reg === "us" ? diagram.ink : ACCENT_WARM}
                        opacity={0.85}
                      />
                    );
                  })}
                  {Array.from({ length: 10 }, (_, i) => (
                    <text
                      key={i}
                      x={M_L + i * bandW + bandW / 2}
                      y={VB_H - 8}
                      textAnchor="middle"
                      fontSize={9}
                      fill={diagram.muted}
                    >
                      D{i + 1}
                    </text>
                  ))}
                  <text x={4} y={yFor(aAbsMax) + 4} fontSize={9} fill={diagram.muted}>
                    {fmtPct(aAbsMax)}
                  </text>
                  <text x={4} y={zeroY - 3} fontSize={9} fill={diagram.muted}>0</text>
                </svg>
              </DiagramFigure>
            );
          })}
        </div>

        <DiagramFigure
          title={t("deciles.panelB")}
          desc={t("deciles.subtitle")}
          caption={t("deciles.meanFwd")}
          table={
            <table className="w-full text-xs">
              <thead>
                <tr>
                  <th className="text-left">region</th>
                  <th className="text-left">month</th>
                  <th className="text-right">D10 − D1</th>
                </tr>
              </thead>
              <tbody>
                {spreadSeries.flatMap((s) =>
                  s.points.map((p) => (
                    <tr key={`${s.region}-${p.month}`}>
                      <td>{s.region}</td>
                      <td>{p.month}</td>
                      <td className="text-right tabular-nums">{fmtPct(p.v)}</td>
                    </tr>
                  )),
                )}
              </tbody>
            </table>
          }
        >
          {spreadSeries.length === 0 ? (
            <div className="p-4 text-xs text-muted-foreground">{t("deciles.empty")}</div>
          ) : (
            (() => {
              const VBW = 1000;
              const H = 190;
              const ML = 48;
              const MR = 8;
              const plotW2 = VBW - ML - MR;
              const months = Array.from(
                new Set(spreadSeries.flatMap((s) => s.points.map((p) => p.month))),
              ).sort();
              const xFor = (m: string) => ML + (months.indexOf(m) / (months.length - 1 || 1)) * plotW2;
              const yS = (v: number) => 14 + (1 - (v - lo) / (hi - lo)) * (H - 40);
              return (
                <svg viewBox={`0 0 ${VBW} ${H}`} role="img" aria-label={t("deciles.panelB")}>
                  <line
                    x1={ML} x2={VBW - MR} y1={yS(0)} y2={yS(0)}
                    stroke={diagram.border} strokeDasharray="3 3" strokeWidth={1}
                  />
                  {spreadSeries.map((s) => {
                    const pts = s.points.map(
                      (p) => `${xFor(p.month)},${yS(p.v)}`,
                    );
                    return (
                      <polyline
                        key={s.region}
                        points={pts.join(" ")}
                        fill="none"
                        stroke={s.region === "us" ? diagram.ink : ACCENT_WARM}
                        strokeWidth={1.6}
                        strokeLinejoin="round"
                      />
                    );
                  })}
                  <text x={4} y={yS(hi) + 10} fontSize={9} fill={diagram.muted}>
                    {fmtPct(hi)}
                  </text>
                  <text x={4} y={yS(lo) + 4} fontSize={9} fill={diagram.muted}>
                    {fmtPct(lo)}
                  </text>
                  <text x={4} y={yS(0) - 3} fontSize={9} fill={diagram.muted}>0</text>
                </svg>
              );
            })()
          )}
        </DiagramFigure>

        <p className="text-xs text-muted-foreground">
          {fmtTplCount(t("deciles.coverage"), realizedCount, rows.length)}
        </p>
      </CardContent>
    </Card>
  );
}

function fmtTplCount(tpl: string, realized: number, total: number): string {
  return tpl.replace("{realized}", String(realized)).replace("{total}", String(total));
}
