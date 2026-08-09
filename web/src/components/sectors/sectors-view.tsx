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
import { aionis, type SectorRow } from "@/data/aionis";
import { AlertTriangleIcon, ArrowUpIcon, ArrowDownIcon } from "lucide-react";

function NullDisclaimer() {
  const { t } = useI18n();
  return (
    <div
      role="note"
      className="flex gap-2 rounded-md border border-amber-300/60 bg-amber-50/80 p-3 text-xs text-amber-900 dark:border-amber-700/50 dark:bg-amber-950/40 dark:text-amber-200"
    >
      <AlertTriangleIcon className="mt-0.5 size-3.5 shrink-0" />
      <div className="space-y-1">
        <p className="font-medium">{t("sectors.disclaimer.title")}</p>
        <p className="leading-relaxed text-amber-800/90 dark:text-amber-200/80">
          {t("sectors.disclaimer.body")}
        </p>
      </div>
    </div>
  );
}

/** Horizontal bar showing relative favor — width ∝ standardized mean_score. */
function FavorBar({ score, minScore, maxScore }: { score: number; minScore: number; maxScore: number }) {
  const span = Math.max(1e-9, maxScore - minScore);
  const pct = ((score - minScore) / span) * 100;
  const positive = score >= 0;
  return (
    <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
      <div
        className={cn(
          "h-full rounded-full",
          positive ? "bg-emerald-500/70 dark:bg-emerald-400/70" : "bg-rose-500/70 dark:bg-rose-400/70",
        )}
        style={{ width: `${Math.max(4, Math.min(100, pct))}%` }}
      />
    </div>
  );
}

type SectorCardProps = {
  row: SectorRow;
  minScore: number;
  maxScore: number;
  baseRate: number;
  rank: number;
};

function SectorCard({ row, minScore, maxScore, baseRate, rank }: SectorCardProps) {
  const probPct = (row.mean_prob_up * 100).toFixed(1);
  const delta = row.mean_prob_up - baseRate;
  const probTone =
    delta > 0.03
      ? "text-emerald-700 dark:text-emerald-300"
      : delta < -0.03
        ? "text-rose-700 dark:text-rose-300"
        : "text-muted-foreground";
  return (
    <div className="flex items-center gap-3 px-4 py-2.5">
      <span className="w-6 shrink-0 text-sm font-semibold tabular-nums text-muted-foreground">
        {rank}
      </span>
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        <div className="flex items-center justify-between gap-2">
          <span className="truncate text-sm font-medium" title={row.sector}>
            {row.sector}
          </span>
          <span className={cn("font-mono text-xs tabular-nums", probTone)}>
            P(up) {probPct}%
          </span>
        </div>
        <FavorBar score={row.mean_score} minScore={minScore} maxScore={maxScore} />
        <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
          <span className="font-mono">{row.mean_score > 0 ? "+" : ""}{row.mean_score.toFixed(2)}</span>
          <span className="opacity-60">·</span>
          <span>{row.n_stocks} stocks</span>
          <span className="opacity-60">·</span>
          <span className="flex gap-0.5">
            {row.regions.map((r) => (
              <Badge key={r} variant="outline" className="px-1 py-0 text-[9px] font-normal uppercase">
                {r}
              </Badge>
            ))}
          </span>
        </div>
      </div>
    </div>
  );
}

export function SectorsView() {
  const { t } = useI18n();
  const sb = aionis.sectorBreakdown;
  if (sb.status !== "ok") {
    return (
      <div className="space-y-6 p-4 md:p-6">
        <h1 className="text-2xl font-bold tracking-tight">{t("module.sectors.title")}</h1>
        <Card>
          <CardContent className="p-6 text-sm text-muted-foreground">
            {sb.methodology ?? t("sectors.awaiting")}
          </CardContent>
        </Card>
      </div>
    );
  }
  const all = sb.all_sectors as SectorRow[];
  const scores = all.map((s) => s.mean_score);
  const minScore = Math.min(...scores, 0);
  const maxScore = Math.max(...scores, 0);
  const top = sb.top_favored as SectorRow[];
  const bot = sb.least_favored as SectorRow[];
  const latestDates = sb.latest_dates
    ? Object.values(sb.latest_dates as Record<string, string>).join(" · ")
    : "";

  return (
    <div className="space-y-6 p-4 md:p-6">
      <p className="text-xs font-medium text-primary">{t("sectors.role")}</p>
      <header className="space-y-2">
        <h1 className="text-2xl font-bold tracking-tight">{t("module.sectors.title")}</h1>
        <p className="max-w-2xl text-sm text-muted-foreground">{t("sectors.intro")}</p>
        <div className="flex flex-wrap gap-x-6 gap-y-1 pt-1 text-sm">
          <span className="text-muted-foreground">
            {t("sectors.n_sectors")}{" "}
            <span className="font-mono text-foreground">{sb.n_sectors}</span>
          </span>
          <span className="text-muted-foreground">
            {t("sectors.latest")}{" "}
            <span className="font-mono text-foreground">{latestDates}</span>
          </span>
        </div>
      </header>

      <NullDisclaimer />

      <Card className="overflow-hidden py-0">
        <CardHeader className="border-b">
          <CardTitle className="flex items-center gap-2 text-base">
            <ArrowUpIcon className="size-4 text-emerald-600 dark:text-emerald-400" />
            {t("sectors.top_favored")}
          </CardTitle>
          <CardDescription>{t("sectors.top_favored_desc")}</CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          <div className="divide-y">
            {top.map((s, i) => (
              <SectorCard
                key={s.sector}
                row={s}
                minScore={minScore}
                maxScore={maxScore}
                baseRate={0.5}
                rank={i + 1}
              />
            ))}
          </div>
        </CardContent>
      </Card>

      <Card className="overflow-hidden py-0">
        <CardHeader className="border-b">
          <CardTitle className="flex items-center gap-2 text-base">
            <ArrowDownIcon className="size-4 text-rose-600 dark:text-rose-400" />
            {t("sectors.least_favored")}
          </CardTitle>
          <CardDescription>{t("sectors.least_favored_desc")}</CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          <div className="divide-y">
            {bot.map((s, i) => (
              <SectorCard
                key={s.sector}
                row={s}
                minScore={minScore}
                maxScore={maxScore}
                baseRate={0.5}
                rank={i + 1}
              />
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-4 text-xs text-muted-foreground">
          <p className="font-medium text-foreground">{t("sectors.methodology_title")}</p>
          <p className="mt-1 leading-relaxed">{sb.methodology}</p>
        </CardContent>
      </Card>
    </div>
  );
}
