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
import { ArrowUpIcon, ArrowDownIcon, MinusIcon } from "lucide-react";

function Change({ change }: { change: number | null }) {
  if (change === null || change === 0) {
    return <MinusIcon className="size-3.5 text-muted-foreground" />;
  }
  const up = change > 0;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-0.5 text-xs font-medium tabular-nums",
        up ? "text-emerald-600 dark:text-emerald-400" : "text-rose-600 dark:text-rose-400",
      )}
    >
      {up ? <ArrowUpIcon className="size-3.5" /> : <ArrowDownIcon className="size-3.5" />}
      {Math.abs(change)}
    </span>
  );
}

function PickRow({ p, showChange }: { p: Pick; showChange: boolean }) {
  const { t } = useI18n();
  const positive = p.score >= 0;
  return (
    <div className="flex items-center gap-3 px-4 py-2.5">
      <span className="w-6 shrink-0 text-sm font-semibold tabular-nums text-muted-foreground">
        {p.rank}
      </span>
      <span className="w-28 shrink-0 truncate font-medium">{p.ticker}</span>
      <Badge variant="outline" className="shrink-0 px-1.5 py-0 text-[10px] font-normal">
        {t(p.region === "us" ? "picks.region.us" : "picks.region.cn")}
      </Badge>
      <span
        className={cn(
          "ml-auto font-mono text-sm tabular-nums",
          positive ? "text-emerald-600 dark:text-emerald-400" : "text-rose-600 dark:text-rose-400",
        )}
      >
        {p.score > 0 ? "+" : ""}
        {p.score.toFixed(2)}
      </span>
      <span className="w-10 shrink-0 text-right">
        {showChange ? <Change change={p.rank_change} /> : null}
      </span>
    </div>
  );
}

export function PicksView() {
  const { t } = useI18n();
  return (
    <div className="space-y-6 p-4 md:p-6">
      <header className="space-y-2">
        <h1 className="text-2xl font-bold tracking-tight">{t("module.picks.title")}</h1>
        <p className="max-w-2xl text-sm text-muted-foreground">{t("picks.intro")}</p>
        <div className="flex flex-wrap gap-x-6 gap-y-1 pt-1 text-sm">
          <span className="text-muted-foreground">
            {t("module.picks.window")}: <span className="font-medium text-foreground">{aionis.metrics.latest_month}</span>
          </span>
          <span className="text-muted-foreground">
            {t("picks.region.us")} + {t("picks.region.cn")}:{" "}
            <span className="font-medium tabular-nums text-foreground">{aionis.metrics.n_picks_total}</span>
          </span>
        </div>
      </header>

      <Card className="overflow-hidden py-0">
        <CardHeader className="border-b">
          <CardTitle className="text-base">Top 20 · long</CardTitle>
          <CardDescription>{t("module.picks.window")}</CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          <div className="divide-y">
            {aionis.picks.map((p) => (
              <PickRow key={p.ticker} p={p} showChange />
            ))}
          </div>
        </CardContent>
      </Card>

      <Card className="overflow-hidden py-0">
        <CardHeader className="border-b">
          <CardTitle className="text-base">{t("picks.shorts.title")}</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="divide-y">
            {aionis.shorts.map((p) => (
              <PickRow key={p.ticker} p={{ ...p, rank_change: null }} showChange={false} />
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
