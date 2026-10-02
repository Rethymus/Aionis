"use client";

import dynamic from "next/dynamic";
import { Card, CardContent } from "@/components/ui/card";
import { DiagramFigure } from "@/components/diagram/primitives";
import { aionis } from "@/data/aionis";
import { useI18n } from "@/i18n/provider";
import { fmtEmpty } from "@/lib/format";
import { FrostedScrollArea } from "@/components/ui/frosted-scroll-area";
import { REGIONS, fmtTpl, prepRegion } from "./atlas-divergence-prep";

// Surgical split (round 118): the SVG panels hydrate from a separate async
// chunk (ssr:false) — the round-117 ablation pinned this section at
// ~830-1,770ms of atlas TBT. The tables, headings and methodology below are
// the section's text content and stay SSR (content-first). The skeletons
// carry the figure heights so CLS holds at 0 (market round-114 precedent).
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
const DivergenceBlockAFigure = dynamic(
  () => import("./atlas-divergence-charts").then(m => m.DivergenceBlockAFigure),
  { ssr: false, loading: figureSkeleton(580) },
);
const DivergenceBlockBFigure = dynamic(
  () => import("./atlas-divergence-charts").then(m => m.DivergenceBlockBFigure),
  { ssr: false, loading: figureSkeleton(520) },
);

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

  const tablesAInner = (
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

  const tablesA = (
    <FrostedScrollArea maxHeight={360} label={t("atlas.div.table")}>
      {tablesAInner}
    </FrostedScrollArea>
  );
  const tablesBInner = (
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

  const tablesB = (
    <FrostedScrollArea maxHeight={360} label={t("atlas.div.table")}>
      {tablesBInner}
    </FrostedScrollArea>
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
            <DivergenceBlockAFigure panels={panels} />
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
            <DivergenceBlockBFigure panels={panels} />
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
