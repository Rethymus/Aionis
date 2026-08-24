"use client";

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
import { aionis, type Pick } from "@/data/aionis";
import { ProvenanceBadge } from "@/components/provenance-badge";
import { useLivePrices, type PriceMap } from "@/lib/live-prices";
import Link from "next/link";
import {
  ArrowUpIcon,
  ArrowDownIcon,
  MinusIcon,
  AlertTriangleIcon,
} from "lucide-react";
import { useMemo } from "react";

/** Honest-null disclaimer banner — shown above every prob_up readout. */
function NullDisclaimer() {
  const { t } = useI18n();
  return (
    <div
      role="note"
      className="flex gap-2 rounded-md border border-amber-300/60 bg-amber-50/80 p-3 text-xs text-amber-900 dark:border-amber-700/50 dark:bg-amber-950/40 dark:text-amber-200"
    >
      <AlertTriangleIcon className="mt-0.5 size-3.5 shrink-0" />
      <div className="space-y-1">
        <p className="font-medium">{t("picks.disclaimer.title")}</p>
        <p className="leading-relaxed text-amber-800/90 dark:text-amber-200/80">
          {t("picks.disclaimer.body")}
        </p>
        <p className="font-mono text-xs text-amber-700/80 dark:text-amber-300/70">
          {aionis.picksMeta.disclaimer}
        </p>
      </div>
    </div>
  );
}

/** prob_up horizontal bar: visual encoding of calibrated P(up) with directional color. */
function ProbUpBar({ probUp, baseRate }: { probUp: number; baseRate: number }) {
  const widthPct = Math.round(probUp * 100);
  // Green when prob_up > 0.5 (bullish edge), rose when < 0.5 (bearish)
  const barColor =
    probUp > 0.5
      ? "bg-up"
      : "bg-down";

  return (
    <div className="flex w-20 shrink-0 flex-col gap-0.5">
      <div className="flex items-center gap-1.5">
        <div className="h-2 w-full overflow-hidden rounded-full bg-muted/50">
          <div
            className={cn("h-full rounded-full transition-all", barColor)}
            style={{ width: `${widthPct}%` }}
            title={`P(up) = ${(probUp * 100).toFixed(1)}% · base_rate ${(baseRate * 100).toFixed(1)}%`}
          />
        </div>
        <span className="text-xs font-mono tabular-nums text-muted-foreground">
          {widthPct}%
        </span>
      </div>
    </div>
  );
}

function Change({ change }: { change: number | null }) {
  if (change === null || change === 0) {
    return <MinusIcon className="size-3.5 text-muted-foreground" />;
  }
  const up = change > 0;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-0.5 text-xs font-medium tabular-nums",
        up
          ? "text-up"
          : "text-down",
      )}
    >
      {up ? <ArrowUpIcon className="size-3.5" /> : <ArrowDownIcon className="size-3.5" />}
      {Math.abs(change)}
    </span>
  );
}

type PickRowProps = {
  p: Pick;
  baseRate: number;
  showChange: boolean;
  livePrice?: { price: number | null; change_pct: number | null };
};

/** One pick row: rank | name + ticker + sector | live% | prob_up | score | change */
function PickRow({ p, baseRate, showChange, livePrice }: PickRowProps) {
  const { t } = useI18n();
  const positive = p.score >= 0;
  const displayName = p.name && p.name.length > 0 ? p.name : p.ticker;
  const regionLabel = t(p.region === "us" ? "picks.region.us" : "picks.region.cn");
  return (
    <div className="flex items-center gap-3 px-4 py-2.5">
      <span className="w-6 shrink-0 text-sm font-semibold tabular-nums text-muted-foreground">
        {p.rank}
      </span>
      <Link
        href={`/stock/${p.ticker}`}
        className="flex min-w-0 flex-1 flex-col rounded-sm hover:underline"
        title={`${p.ticker} · ${p.sector || t("picks.no_sector")}`}
      >
        <span className="truncate text-sm font-medium">{displayName}</span>
        <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <span className="font-mono">{p.ticker}</span>
          <Badge variant="outline" className="px-1 py-0 text-[11px] font-normal">
            {regionLabel}
          </Badge>
          {p.sector ? (
            <span className="truncate">{p.sector}</span>
          ) : (
            <span className="italic">{t("picks.no_sector")}</span>
          )}
        </span>
      </Link>
      <ProbUpBar probUp={p.prob_up} baseRate={baseRate} />
      {livePrice?.change_pct !== undefined && livePrice?.change_pct !== null ? (
        <span
          className={cn(
            "w-16 shrink-0 text-right font-mono text-xs tabular-nums",
            livePrice.change_pct >= 0
              ? "text-up"
              : "text-down",
          )}
          title={livePrice.price ? `¥${livePrice.price.toFixed(2)} / $${livePrice.price.toFixed(2)}` : undefined}
        >
          {livePrice.change_pct >= 0 ? "+" : ""}
          {livePrice.change_pct.toFixed(2)}%
        </span>
      ) : (
        <span className="w-16 shrink-0 text-right text-xs text-muted-foreground/30">—</span>
      )}
      <span
        className={cn(
          "w-12 shrink-0 text-right font-mono text-sm tabular-nums",
          positive
            ? "text-up"
            : "text-down",
        )}
      >
        {p.score > 0 ? "+" : ""}
        {p.score.toFixed(2)}
      </span>
      <span className="w-8 shrink-0 text-right">
        {showChange ? <Change change={p.rank_change} /> : null}
      </span>
    </div>
  );
}

type RegionGroupProps = {
  title: string;
  picks: Pick[];
  baseRate: number;
  latestDate: string;
  showChange: boolean;
  prices: PriceMap;
};

function RegionGroup({ title, picks, baseRate, latestDate, showChange, prices }: RegionGroupProps) {
  if (picks.length === 0) return null;
  return (
    <Card className="overflow-hidden py-0">
      <CardHeader className="border-b">
        <CardTitle className="text-base">{title}</CardTitle>
        <CardDescription className="flex items-center gap-2 font-mono text-xs">
          <span>{latestDate}</span>
          <span className="opacity-60">·</span>
          <span>P(up) base {((baseRate ?? 0) * 100).toFixed(1)}%</span>
        </CardDescription>
      </CardHeader>
      <CardContent className="p-0">
        <div className="divide-y">
          {picks.map((p) => (
            <PickRow
              key={`${p.region}-${p.ticker}`}
              p={p}
              baseRate={baseRate}
              showChange={showChange}
              livePrice={prices[p.ticker]}
            />
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Portfolio concentration (display-only). Equal-weight sector aggregation of a
// region's longs + shorts: sector shares by name COUNT (frozen OOS picks carry
// no market-cap dimension), HHI = Σ share², and a display-heuristic level
// badge (<0.25 / 0.25–0.45 / >0.45). This is a readout lens, not a claim.
// ---------------------------------------------------------------------------

type SectorCount = { sector: string; n: number; share: number };

/** Aggregate rows by sector. Empty-sector rows collapse into "" (rendered as
 * "Uncategorized" downstream) and are counted honestly, never dropped. */
function aggregateSectors(rows: { sector: string | "" }[]): SectorCount[] {
  if (rows.length === 0) return [];
  const counts = new Map<string, number>();
  for (const r of rows) {
    counts.set(r.sector, (counts.get(r.sector) ?? 0) + 1);
  }
  const total = rows.length;
  return [...counts.entries()]
    .map(([sector, n]) => ({ sector, n, share: n / total }))
    .sort((a, b) => b.n - a.n || a.sector.localeCompare(b.sector));
}

const CONCENTRATION_LEVEL_KEY = {
  low: "picks.concentration.level.low",
  mid: "picks.concentration.level.mid",
  high: "picks.concentration.level.high",
} as const;

type ConcentrationLevel = keyof typeof CONCENTRATION_LEVEL_KEY;

/** Display heuristic only (see methodology footnote) — not a statistical claim. */
function concentrationLevel(hhi: number): ConcentrationLevel {
  if (hhi < 0.25) return "low";
  if (hhi <= 0.45) return "mid";
  return "high";
}

type RegionConcentrationProps = {
  regionLabel: string;
  longs: { sector: string | "" }[];
  shorts: { sector: string | "" }[];
  className?: string;
};

function RegionConcentration({ regionLabel, longs, shorts, className }: RegionConcentrationProps) {
  const { t } = useI18n();
  const agg = aggregateSectors([...longs, ...shorts]);
  if (agg.length === 0) return null;
  const total = longs.length + shorts.length;
  const hhi = agg.reduce((acc, s) => acc + s.share * s.share, 0);
  const level = concentrationLevel(hhi);
  const top = agg[0];
  const countsLine = `${t("picks.concentration.nStocks")} ${total} · ${t("picks.concentration.long")} ${longs.length} + ${t("picks.concentration.short")} ${shorts.length}`;
  return (
    <div className={cn("space-y-3 p-4", className)}>
      <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
        <span className="text-sm font-medium">{regionLabel}</span>
        <span className="font-mono text-xs tabular-nums text-muted-foreground">
          {countsLine}
        </span>
      </div>
      <div className="flex items-end justify-between gap-3">
        <div className="flex flex-col gap-0.5">
          <span className="text-2xl font-bold tabular-nums">{hhi.toFixed(3)}</span>
          <span className="text-xs text-muted-foreground">
            {t("picks.concentration.hhi")}
          </span>
        </div>
        <Badge
          variant="outline"
          className="px-1.5 py-0 text-xs font-normal text-muted-foreground"
          title={`${t("picks.concentration.hhi")} = ${hhi.toFixed(3)}`}
        >
          {t(CONCENTRATION_LEVEL_KEY[level])}
        </Badge>
      </div>
      <p className="text-xs text-muted-foreground">
        {t("picks.concentration.topSector")}:{" "}
        <span className="font-medium text-foreground">
          {top.sector || t("picks.concentration.uncategorized")}
        </span>{" "}
        · <span className="font-mono tabular-nums">{(top.share * 100).toFixed(1)}%</span>
      </p>
      <div className="space-y-1.5">
        {agg.map((row) => {
          const uncategorized = row.sector === "";
          const isTop = row.n === top.n;
          return (
            <div key={row.sector || "uncategorized"} className="space-y-0.5">
              <div className="flex items-baseline justify-between gap-2 text-xs">
                <span className={cn("min-w-0 truncate", uncategorized && "italic")}>
                  {row.sector || t("picks.concentration.uncategorized")}
                </span>
                <span className="shrink-0 font-mono tabular-nums text-muted-foreground">
                  {row.n} · {(row.share * 100).toFixed(1)}%
                </span>
              </div>
              {/* Bars scale to the region's top share (top = full width); the
                  printed share stays the honest absolute number. Muted/primary
                  only — deliberately NOT up/down directional colors. */}
              <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted/50">
                <div
                  className={cn(
                    "h-full rounded-full",
                    isTop ? "bg-primary" : "bg-muted-foreground/35",
                  )}
                  style={{ width: `${(row.share / top.share) * 100}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/** Portfolio concentration card: per-region sector concentration of the
 * frozen longs + shorts (one card, two region panels side by side ≥md). */
function ConcentrationCard({
  usLongs,
  usShorts,
  cnLongs,
  cnShorts,
}: {
  usLongs: { sector: string | "" }[];
  usShorts: { sector: string | "" }[];
  cnLongs: { sector: string | "" }[];
  cnShorts: { sector: string | "" }[];
}) {
  const { t } = useI18n();
  const usEmpty = usLongs.length + usShorts.length === 0;
  const cnEmpty = cnLongs.length + cnShorts.length === 0;
  if (usEmpty && cnEmpty) return null;
  return (
    <Card className="overflow-hidden py-0">
      <CardHeader className="border-b">
        <CardTitle className="text-base">{t("picks.concentration.title")}</CardTitle>
        <CardDescription className="flex flex-wrap items-center gap-2 text-xs">
          <span>{t("picks.concentration.intro")}</span>
          <ProvenanceBadge ts={aionis.picksMeta.latest_date} frozen />
        </CardDescription>
      </CardHeader>
      <CardContent className="p-0">
        <div className="grid md:grid-cols-2 md:divide-x">
          <RegionConcentration
            regionLabel={t("picks.region.us")}
            longs={usLongs}
            shorts={usShorts}
            className="border-b md:border-b-0"
          />
          <RegionConcentration
            regionLabel={t("picks.region.cn")}
            longs={cnLongs}
            shorts={cnShorts}
          />
        </div>
        <div className="border-t px-4 py-2.5 text-xs leading-relaxed text-muted-foreground">
          {t("picks.concentration.methodology")}
        </div>
      </CardContent>
    </Card>
  );
}

export function PicksView() {
  const { t } = useI18n();
  const meta = aionis.picksMeta;
  const usMeta = meta.regions.us?.meta;
  const cnMeta = meta.regions.cn?.meta;
  const usBase = usMeta?.base_rate ?? 0.5;
  const cnBase = cnMeta?.base_rate ?? 0.5;
  const usLatest = meta.regions.us?.latest_date ?? meta.latest_date;
  const cnLatest = meta.regions.cn?.latest_date ?? meta.latest_date;

  const usPicks = aionis.picks.filter((p) => p.region === "us");
  const cnPicks = aionis.picks.filter((p) => p.region === "cn");
  const usShorts = aionis.shorts.filter((p) => p.region === "us");
  const cnShorts = aionis.shorts.filter((p) => p.region === "cn");

  // Live price overlay (graceful degradation: empty prices when Worker is off).
  const allTickers = useMemo(
    () => [...aionis.picks, ...aionis.shorts].map((p) => ({ ticker: p.ticker, region: p.region })),
    [],
  );
  const { prices } = useLivePrices(allTickers);

  return (
    <div className="flex flex-col gap-4">
      <p className="text-xs font-medium text-primary">{t("picks.role")}</p>
      <header className="space-y-2">
        <h1 className="text-2xl font-semibold tracking-[-0.032em]">{t("module.picks.title")}</h1>
        <p className="max-w-2xl text-sm text-muted-foreground">{t("picks.intro")}</p>
        <div className="flex flex-wrap gap-x-6 gap-y-1 pt-1 text-sm">
          <span className="text-muted-foreground">
            {t("picks.method")}{" "}
            <span className="font-mono text-foreground">{meta.method}</span>
          </span>
          {usMeta ? (
            <span className="text-muted-foreground">
              US {usMeta.n_pairs.toLocaleString()}-pair ·
              <span className="font-mono text-foreground">
                {" "}
                [{usMeta.prob_min.toFixed(2)}, {usMeta.prob_max.toFixed(2)}]
              </span>
            </span>
          ) : null}
          {cnMeta ? (
            <span className="text-muted-foreground">
              CN {cnMeta.n_pairs.toLocaleString()}-pair ·
              <span className="font-mono text-foreground">
                {" "}
                [{cnMeta.prob_min.toFixed(2)}, {cnMeta.prob_max.toFixed(2)}]
              </span>
            </span>
          ) : null}
        </div>
      </header>

      <NullDisclaimer />

      <RegionGroup
        title={`Top 10 · US long · ${usPicks.length}/10`}
        picks={usPicks}
        baseRate={usBase}
        latestDate={usLatest}
        showChange
        prices={prices}
      />
      <RegionGroup
        title={`Top 10 · A股 long · ${cnPicks.length}/10`}
        picks={cnPicks}
        baseRate={cnBase}
        latestDate={cnLatest}
        showChange
        prices={prices}
      />

      <Card className="overflow-hidden py-0">
        <CardHeader className="border-b">
          <CardTitle className="text-base">{t("picks.shorts.title")}</CardTitle>
          <CardDescription>{t("picks.shorts.intro")}</CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          <div className="divide-y">
            {usShorts.map((p) => (
              <PickRow
                key={`s-${p.region}-${p.ticker}`}
                p={{ ...p, rank_change: null }}
                baseRate={usBase}
                showChange={false}
                livePrice={prices[p.ticker]}
              />
            ))}
            {cnShorts.map((p) => (
              <PickRow
                key={`s-${p.region}-${p.ticker}`}
                p={{ ...p, rank_change: null }}
                baseRate={cnBase}
                showChange={false}
                livePrice={prices[p.ticker]}
              />
            ))}
          </div>
        </CardContent>
      </Card>

      <ConcentrationCard
        usLongs={usPicks}
        usShorts={usShorts}
        cnLongs={cnPicks}
        cnShorts={cnShorts}
      />

      <TrackRecord />
    </div>
  );
}

/** Track record: past months' top picks vs their realized forward returns. */
function TrackRecord() {
  const { t } = useI18n();
  const bt = aionis.picksBacktest;
  if (!bt?.months?.length) return null;
  const s = bt.summary;
  const hitPct = (s.hit_rate * 100).toFixed(0);
  const excessPct = (s.avg_excess * 100).toFixed(2);
  const excessTone =
    s.avg_excess > 0.005
      ? "text-emerald-700 dark:text-emerald-300"
      : s.avg_excess < -0.005
        ? "text-rose-700 dark:text-rose-300"
        : "text-muted-foreground";
  return (
    <Card className="overflow-hidden py-0">
      <CardHeader className="border-b">
        <CardTitle className="text-base">{t("picks.track.title")}</CardTitle>
        <CardDescription className="flex flex-wrap gap-x-4 text-xs">
          <span>{t("picks.track.hit_rate")}: <span className="font-mono">{hitPct}%</span></span>
          <span>{t("picks.track.excess")}: <span className={cn("font-mono", excessTone)}>{excessPct}%</span></span>
          <span>{t("picks.track.n_picks")}: <span className="font-mono">{s.n_picks}</span></span>
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-0 p-0">
        {bt.months.map((m) => {
          const regionLabel = t(m.region === "us" ? "picks.region.us" : "picks.region.cn");
          const excess = m.excess;
          const excessColor =
            excess > 0.005
              ? "text-up"
              : excess < -0.005
                ? "text-down"
                : "text-muted-foreground";
          return (
            <div key={`${m.month}-${m.region}`} className="border-b px-4 py-2 last:border-b-0">
              <div className="mb-1 flex items-center justify-between text-xs">
                <span className="font-mono text-muted-foreground">
                  {m.month} · {regionLabel}
                </span>
                <span className={cn("font-mono", excessColor)}>
                  {t("picks.track.top")}: {(m.top_mean_return * 100).toFixed(2)}% · {t("picks.track.base")}: {(m.base_mean_return * 100).toFixed(2)}% · Δ:{(excess * 100).toFixed(2)}%
                </span>
              </div>
              <div className="flex flex-wrap gap-x-3 gap-y-0.5">
                {m.picks.map((p) => {
                  const retPct = (p.realized_return * 100).toFixed(2);
                  const tone = p.realized_return > 0
                    ? "text-up"
                    : "text-down";
                  return (
                    <span key={p.ticker} className={cn("font-mono text-xs", tone)} title={`${p.name} · score ${p.score}`}>
                      {p.name || p.ticker} {retPct}%
                    </span>
                  );
                })}
              </div>
            </div>
          );
        })}
        <div className="px-4 py-2 text-xs text-muted-foreground">
          {bt.methodology}
        </div>
      </CardContent>
    </Card>
  );
}
