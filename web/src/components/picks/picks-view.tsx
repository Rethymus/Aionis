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
import {
  ArrowUpIcon,
  ArrowDownIcon,
  MinusIcon,
  AlertTriangleIcon,
} from "lucide-react";

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
        <p className="font-mono text-[10px] text-amber-700/80 dark:text-amber-300/70">
          {aionis.picksMeta.disclaimer}
        </p>
      </div>
    </div>
  );
}

/** prob_up chip: color encodes distance from base_rate (no overclaiming). */
function ProbUpChip({ probUp, baseRate }: { probUp: number; baseRate: number }) {
  const delta = probUp - baseRate;
  // Tight band around base_rate (±0.03) = "no edge" (gray). Beyond = tinted.
  const tone =
    delta > 0.03
      ? "text-emerald-700 dark:text-emerald-300"
      : delta < -0.03
        ? "text-rose-700 dark:text-rose-300"
        : "text-muted-foreground";
  return (
    <span
      className={cn(
        "inline-flex w-14 shrink-0 justify-end font-mono text-xs tabular-nums",
        tone,
      )}
      title={`P(up) = ${(probUp * 100).toFixed(1)}% · base_rate ${(baseRate * 100).toFixed(1)}%`}
    >
      {(probUp * 100).toFixed(0)}%
    </span>
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
          ? "text-emerald-600 dark:text-emerald-400"
          : "text-rose-600 dark:text-rose-400",
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
};

/** One pick row: rank | name (main) + ticker (small) + sector badge | prob_up | score | change */
function PickRow({ p, baseRate, showChange }: PickRowProps) {
  const { t } = useI18n();
  const positive = p.score >= 0;
  const displayName = p.name && p.name.length > 0 ? p.name : p.ticker;
  const regionLabel = t(p.region === "us" ? "picks.region.us" : "picks.region.cn");
  return (
    <div className="flex items-center gap-3 px-4 py-2.5">
      <span className="w-6 shrink-0 text-sm font-semibold tabular-nums text-muted-foreground">
        {p.rank}
      </span>
      <div className="flex min-w-0 flex-1 flex-col">
        <span
          className="truncate text-sm font-medium"
          title={`${p.ticker} · ${p.sector || t("picks.no_sector")}`}
        >
          {displayName}
        </span>
        <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground">
          <span className="font-mono">{p.ticker}</span>
          <Badge variant="outline" className="px-1 py-0 text-[9px] font-normal">
            {regionLabel}
          </Badge>
          {p.sector ? (
            <span className="truncate">{p.sector}</span>
          ) : (
            <span className="italic opacity-60">{t("picks.no_sector")}</span>
          )}
        </div>
      </div>
      <ProbUpChip probUp={p.prob_up} baseRate={baseRate} />
      <span
        className={cn(
          "w-12 shrink-0 text-right font-mono text-sm tabular-nums",
          positive
            ? "text-emerald-600 dark:text-emerald-400"
            : "text-rose-600 dark:text-rose-400",
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
};

function RegionGroup({ title, picks, baseRate, latestDate, showChange }: RegionGroupProps) {
  if (picks.length === 0) return null;
  return (
    <Card className="overflow-hidden py-0">
      <CardHeader className="border-b">
        <CardTitle className="text-base">{title}</CardTitle>
        <CardDescription className="flex items-center gap-2 font-mono text-[10px]">
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
            />
          ))}
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

  return (
    <div className="space-y-6 p-4 md:p-6">
      <header className="space-y-2">
        <h1 className="text-2xl font-bold tracking-tight">{t("module.picks.title")}</h1>
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
      />
      <RegionGroup
        title={`Top 10 · A股 long · ${cnPicks.length}/10`}
        picks={cnPicks}
        baseRate={cnBase}
        latestDate={cnLatest}
        showChange
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
              />
            ))}
            {cnShorts.map((p) => (
              <PickRow
                key={`s-${p.region}-${p.ticker}`}
                p={{ ...p, rank_change: null }}
                baseRate={cnBase}
                showChange={false}
              />
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
