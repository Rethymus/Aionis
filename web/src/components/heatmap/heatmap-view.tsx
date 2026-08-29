"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { useI18n } from "@/i18n/provider";
import { stockUniverse, type StockRow } from "@/data/aionis/stock-universe";
import { ProvenanceBadge } from "@/components/provenance-badge";

// Squarified treemap (Bruls/Dik/Huizing) over the frozen OOS universe —
// xiaoyinsi-style bird's-eye: cell AREA = |model score|, cell TINT = direction
// (var(--up)/var(--down) so the color-convention toggle recolors the map).
// Hand-rolled layout (no new deps): deterministic SSR-friendly divs with
// percentage geometry. Click-through to /stock/[ticker]; the aggregated
// "other" bucket is honest about what it hides and is not clickable.

const TOP_N = 150;

type Cell = { key: string; value: number };
type Rect = { x: number; y: number; w: number; h: number };
type Laid = Rect & Cell;

function worstRatio(rect: Rect, rowValues: number[]): number {
  // Worst aspect ratio the candidate row would produce laid along the short side.
  const short = Math.min(rect.w, rect.h);
  if (short <= 0 || rowValues.length === 0) return Infinity;
  const thickness = rowValues.reduce((a, b) => a + b, 0) / short;
  if (thickness <= 0) return Infinity;
  let worst = 0;
  for (const v of rowValues) {
    const side = v / thickness;
    const r = Math.max(thickness / side, side / thickness);
    if (r > worst) worst = r;
  }
  return worst;
}

function squarify(items: Cell[], rect: Rect): Laid[] {
  const out: Laid[] = [];
  const rectArea = rect.w * rect.h;
  const total = items.reduce((s, i) => s + i.value, 0);
  if (total <= 0 || rectArea <= 0) return out;
  const scale = rectArea / total;
  let r: Rect = { ...rect };
  // Largest first (squarify precondition).
  let remaining = [...items].sort((a, b) => b.value - a.value);
  while (remaining.length > 0 && r.w > 0 && r.h > 0) {
    // Greedily grow the row while the worst aspect ratio improves.
    const row: Cell[] = [];
    let bestWorst = Infinity;
    let bestCount = 0;
    for (let i = 0; i < remaining.length; i++) {
      row.push(remaining[i]);
      const worst = worstRatio(r, row.map((c) => c.value * scale));
      if (worst <= bestWorst) {
        bestWorst = worst;
        bestCount = row.length;
      } else {
        break;
      }
    }
    const rowItems = remaining.slice(0, bestCount);
    remaining = remaining.slice(bestCount);
    const rowArea = rowItems.reduce((s, c) => s + c.value * scale, 0);
    const short = Math.min(r.w, r.h);
    const thickness = rowArea / short;
    if (r.w >= r.h) {
      // Vertical strip at the left edge.
      let y = r.y;
      for (const c of rowItems) {
        const h = (c.value * scale) / thickness;
        out.push({ ...c, x: r.x, y, w: thickness, h });
        y += h;
      }
      r = { x: r.x + thickness, y: r.y, w: r.w - thickness, h: r.h };
    } else {
      // Horizontal strip at the top edge.
      let x = r.x;
      for (const c of rowItems) {
        const w = (c.value * scale) / thickness;
        out.push({ ...c, x, y: r.y, w, h: thickness });
        x += w;
      }
      r = { x: r.x, y: r.y + thickness, w: r.w, h: r.h - thickness };
    }
  }
  return out;
}

type PreparedCell = {
  stock: StockRow | null; // null = aggregated "other" bucket
  value: number; // |score| (sum for the bucket)
  count: number;
  meanScore: number | null;
};

function prepareRegion(region: "us" | "cn"): PreparedCell[] {
  const rows = stockUniverse.stocks.filter((s) => s.region === region);
  const byAbs = [...rows].sort((a, b) => Math.abs(b.score) - Math.abs(a.score));
  const top = byAbs.slice(0, TOP_N);
  const rest = byAbs.slice(TOP_N);
  const cells: PreparedCell[] = top.map((s) => ({
    stock: s,
    value: Math.abs(s.score),
    count: 1,
    meanScore: s.score,
  }));
  if (rest.length > 0) {
    const sumScore = rest.reduce((a, s) => a + s.score, 0);
    cells.push({
      stock: null,
      value: rest.reduce((a, s) => a + Math.abs(s.score), 0),
      count: rest.length,
      meanScore: sumScore / rest.length,
    });
  }
  return cells;
}

function RegionMap({ region, heightClass }: { region: "us" | "cn"; heightClass: string }) {
  const { t } = useI18n();
  const cells = useMemo(() => prepareRegion(region), [region]);
  const laid = useMemo(
    () => squarify(cells.map((c, i) => ({ key: String(i), value: c.value })), { x: 0, y: 0, w: 100, h: 100 }),
    [cells],
  );
  const maxAbs = useMemo(() => Math.max(...cells.map((c) => c.value), 0.001), [cells]);

  if (cells.length === 0) {
    return (
      <Card className="py-0">
        <CardContent className="p-4 text-sm italic text-muted-foreground">
          {t("heatmap.empty")}
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="py-0">
      <CardHeader className="border-b">
        <CardTitle className="flex items-center gap-2 text-base">
          {t(region === "us" ? "heatmap.tab.us" : "heatmap.tab.cn")}
          <span className="text-sm font-normal text-muted-foreground">
            {cells.reduce((a, c) => a + c.count, 0).toLocaleString()}
          </span>
          <ProvenanceBadge ts={stockUniverse.as_of[region]} frozen className="ml-auto" />
        </CardTitle>
        <CardDescription className="font-mono text-xs">{t("heatmap.colormap.note")}</CardDescription>
      </CardHeader>
      <CardContent className="p-2">
        <div className={cn("relative w-full overflow-hidden rounded-md border", heightClass)}>
          {laid.map((l) => {
            // Map geometry back to data by the ORIGINAL index carried in
            // l.key — NOT by array position: squarify sorts internally
            // (descending), and the aggregated "other" bucket (usually the
            // largest value) sits at the END of `cells`, so position-mapping
            // shifted every label/color/link one cell off wherever the bucket
            // outranked its input position (the giant "COIN/sh.688041" cell
            // was actually the bucket's rectangle — owner-reported 2026-08-29).
            const prep = cells[Number(l.key)];
            if (!prep) return null;
            const stock = prep.stock;
            const positive = (stock?.score ?? prep.meanScore ?? 0) >= 0;
            // Intensity: 0.12 → 0.5 alpha by normalized |score| within region.
            const intensity = 0.12 + 0.38 * Math.min(1, prep.value / maxAbs);
            const varName = stock ? (positive ? "--up" : "--down") : null;
            const bg = varName
              ? `color-mix(in oklab, var(${varName}) ${Math.round(intensity * 100)}%, transparent)`
              : "color-mix(in oklab, var(--muted-foreground) 10%, transparent)";
            const title = stock
              ? `${stock.name || stock.ticker} · ${stock.ticker} | ${t("heatmap.tip.score")} ${stock.score.toFixed(2)} | ${t("heatmap.tip.rank")} ${stock.rank}/${stock.n_region} | ${t("heatmap.tip.prob")} ${(stock.prob_up * 100).toFixed(1)}%`
              : t("heatmap.other.legend")
                  .replace("{n}", String(prep.count))
                  .replace("{shown}", String(TOP_N))
                  .replace("{score}", (prep.meanScore ?? 0).toFixed(2));
            // Label tiers by cell size (percent of the map box). Owner-reported
            // 2026-08-29: the single threshold (w>7 && h>9) hid tickers on
            // ~half the cells — the median top-150 cell in the two-up grid is
            // ≈40px and just missed it, so the map read as hover-only. Now:
            // big cells carry label + score, medium cells carry a smaller
            // label; only genuinely tiny slivers go bare (the hover title
            // still carries the full name everywhere).
            const big = l.w > 7 && l.h > 9;
            const medium = !big && l.w > 3.4 && l.h > 4.2;
            const showScore = big;
            // CN tickers ("sh.688041") are opaque 9-char codes that clip to
            // garbage in small cells — the short CJK name is the recognizable
            // identifier, so CN rows label by name (hover title keeps the
            // code). US rows keep the ticker (it IS the short id).
            const cellLabel = stock
              ? stock.region === "cn" && stock.name
                ? stock.name
                : stock.ticker
              : t("heatmap.other.bucket").replace("{n}", String(prep.count));
            const body = (
              <>
                {big || medium ? (
                  <span
                    className={cn(
                      "max-w-full truncate font-mono font-semibold leading-none",
                      big ? "text-[11px]" : "text-[10px]",
                      stock ? "text-foreground" : "text-muted-foreground",
                    )}
                  >
                    {cellLabel}
                  </span>
                ) : null}
                {showScore ? (
                  <span className="font-mono text-[11px] leading-none text-muted-foreground">
                    {stock ? stock.score.toFixed(2) : `μ ${(prep.meanScore ?? 0).toFixed(2)}`}
                  </span>
                ) : null}
              </>
            );
            return stock ? (
              <Link
                key={l.key}
                href={`/stock/${stock.ticker}`}
                title={title}
                className="absolute flex flex-col items-center justify-center gap-0.5 overflow-hidden border border-background/60 p-0.5 transition-opacity hover:opacity-80"
                style={{
                  left: `${l.x}%`,
                  top: `${l.y}%`,
                  width: `${l.w}%`,
                  height: `${l.h}%`,
                  backgroundColor: bg,
                }}
              >
                {body}
              </Link>
            ) : (
              <div
                key={l.key}
                title={title}
                className="absolute flex flex-col items-center justify-center gap-0.5 overflow-hidden border border-background/60 p-0.5"
                style={{
                  left: `${l.x}%`,
                  top: `${l.y}%`,
                  width: `${l.w}%`,
                  height: `${l.h}%`,
                  backgroundColor: bg,
                }}
              >
                {body}
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}

export function HeatmapView() {
  const { t } = useI18n();
  const [tab, setTab] = useState<"all" | "us" | "cn">("all");
  const tabs = [
    { key: "all" as const, label: t("heatmap.tab.all") },
    { key: "us" as const, label: t("heatmap.tab.us") },
    { key: "cn" as const, label: t("heatmap.tab.cn") },
  ];

  return (
    <div className="flex flex-col gap-4">
      <p className="text-xs font-medium text-primary">{t("heatmap.role")}</p>
      <header>
        <h1 className="text-2xl font-semibold tracking-[-0.032em]">{t("heatmap.title")}</h1>
        <p className="max-w-2xl text-sm text-muted-foreground">{t("heatmap.intro")}</p>
      </header>

      <div className="flex flex-wrap items-center gap-2">
        {tabs.map((x) => (
          <button
            key={x.key}
            type="button"
            onClick={() => setTab(x.key)}
            aria-pressed={tab === x.key}
            className={cn(
              "rounded-full border px-3 py-1 text-xs font-medium transition-colors",
              tab === x.key
                ? "border-primary bg-primary text-primary-foreground"
                : "border-border text-muted-foreground hover:bg-muted",
            )}
          >
            {x.label}
          </button>
        ))}
        <div className="ml-auto flex items-center gap-2 text-xs text-muted-foreground">
          <span className="inline-flex items-center gap-1">
            <span className="inline-block size-2.5 rounded-sm" style={{ background: "var(--up)" }} />
            {t("heatmap.legend.up")}
          </span>
          <span className="inline-flex items-center gap-1">
            <span className="inline-block size-2.5 rounded-sm" style={{ background: "var(--down)" }} />
            {t("heatmap.legend.down")}
          </span>
        </div>
      </div>

      <div className={cn("grid gap-4", tab === "all" && "md:grid-cols-2")}>
        {tab !== "cn" ? <RegionMap region="us" heightClass={tab === "all" ? "h-[420px]" : "h-[560px]"} /> : null}
        {tab !== "us" ? <RegionMap region="cn" heightClass={tab === "all" ? "h-[420px]" : "h-[560px]"} /> : null}
      </div>

      <Card className="border-muted">
        <CardHeader>
          <CardTitle className="text-sm">{t("heatmap.methodology.title")}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-1">
          <p className="text-xs leading-relaxed text-muted-foreground">{t("heatmap.disclaimer")}</p>
          <p className="font-mono text-xs leading-relaxed text-muted-foreground">
            {stockUniverse.methodology}
          </p>
          <Badge variant="outline" className="text-xs font-normal text-muted-foreground">
            squarified treemap · Bruls/Dik/Huizing
          </Badge>
        </CardContent>
      </Card>
    </div>
  );
}
