"use client";

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { useI18n } from "@/i18n/provider";
import { aionis } from "@/data/aionis";
import { ClockIcon, ShieldCheckIcon } from "lucide-react";

export function RedditView() {
  const { t } = useI18n();
  const r = aionis.reddit;
  const isLive = r.status === "live";

  // Compute total mentions for KPI
  const totalMentions = isLive
    ? r.picks.reduce((sum, pick) => sum + pick.mentions, 0)
    : 0;

  // Format latest snapshot date (date portion only)
  const latestDate = isLive && r.latest_snapshot_ts
    ? r.latest_snapshot_ts.split("T")[0]
    : "—";

  return (
    <div className="space-y-6 p-4 md:p-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-bold tracking-tight">{t("reddit.title")}</h1>
        <p className="text-sm text-muted-foreground">{t("reddit.window")}</p>
      </header>

      {/* Status badge */}
      <Card className={cn(
        "border-amber-500/30 bg-amber-500/5",
        isLive && "border-emerald-500/30 bg-emerald-500/5"
      )}>
        <CardContent className="space-y-2 p-4">
          <div className="flex items-center gap-2">
            <ClockIcon className={cn(
              "size-4 text-amber-600 dark:text-amber-400",
              isLive && "text-emerald-600 dark:text-emerald-400"
            )} />
            <Badge
              variant="outline"
              className={cn(
                "border-amber-500/40 bg-amber-500/10 text-amber-700 dark:text-amber-400",
                isLive && "border-emerald-500/40 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400"
              )}
            >
              {isLive
                ? `${t("reddit.status.live")} · ${r.transport}`
                : t("reddit.status.awaiting")
              }
            </Badge>
          </div>
          <p className="font-mono text-xs">{r.collector}</p>
          <p className="text-xs text-muted-foreground">{r.mode}</p>
        </CardContent>
      </Card>

      {isLive && (
        <>
          {/* KPI grid */}
          <div className="grid grid-cols-3 gap-3">
            <Card>
              <CardContent className="p-4">
                <p className="text-xs text-muted-foreground">{t("reddit.snapshots")}</p>
                <p className="mt-1 text-2xl font-bold tabular-nums">{r.n_snapshots}</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <p className="text-xs text-muted-foreground">{t("reddit.latest")}</p>
                <p className="mt-1 text-2xl font-bold tabular-nums">{latestDate}</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <p className="text-xs text-muted-foreground">{t("reddit.mentions")}</p>
                <p className="mt-1 text-2xl font-bold tabular-nums">{totalMentions}</p>
              </CardContent>
            </Card>
          </div>

          {/* Ranked picks list */}
          <Card className="overflow-hidden py-0">
            <CardHeader className="border-b">
              <CardTitle className="text-base">{t("reddit.title")}</CardTitle>
              <CardDescription>{t("reddit.window")}</CardDescription>
            </CardHeader>
            <CardContent className="p-0">
              <div className="divide-y">
                {r.picks.map((pick, i) => {
                  // Sentiment badge color
                  const sentimentColor =
                    pick.sentiment > 0.2
                      ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                      : pick.sentiment < -0.2
                      ? "border-rose-500/40 bg-rose-500/10 text-rose-600 dark:text-rose-400"
                      : "text-muted-foreground";

                  const sentimentLabel =
                    pick.sentiment > 0.2
                      ? t("reddit.bull")
                      : pick.sentiment < -0.2
                      ? t("reddit.bear")
                      : t("reddit.neutral");

                  return (
                    <div key={pick.ticker} className="flex items-center gap-3 px-4 py-2.5 text-sm">
                      <span className="w-6 shrink-0 text-muted-foreground tabular-nums">
                        {i + 1}
                      </span>
                      <span className="truncate font-mono">{pick.ticker}</span>
                      <Badge
                        variant="secondary"
                        className="ml-auto shrink-0 tabular-nums"
                      >
                        {pick.mentions}
                      </Badge>
                      <Badge
                        variant="outline"
                        className={cn(
                          "shrink-0 px-1.5 py-0 text-[10px]",
                          sentimentColor
                        )}
                      >
                        {sentimentLabel} {pick.sentiment.toFixed(2)}
                      </Badge>
                      {pick.bull_ratio !== null && (
                        <span className="ml-2 text-[10px] text-muted-foreground">
                          bull {pick.bull_ratio.toFixed(2)}
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>

          {/* Score unavailable disclosure */}
          {!r.score_available && (
            <Card className="border-amber-500/30 bg-amber-500/5">
              <CardContent className="p-4">
                <p className="text-xs text-muted-foreground">
                  {t("reddit.scoreUnavailable")}
                </p>
              </CardContent>
            </Card>
          )}
        </>
      )}

      <p className="text-sm text-muted-foreground">{t("reddit.explain")}</p>

      <div className="flex flex-wrap gap-2">
        {r.subreddits.map((s) => (
          <Badge key={s} variant="secondary" className="font-mono">
            r/{s}
          </Badge>
        ))}
      </div>

      <Card>
        <CardHeader className="border-b">
          <CardTitle className="flex items-center gap-2 text-base">
            <ShieldCheckIcon className="size-4" /> {t("reddit.howto")}
          </CardTitle>
        </CardHeader>
        <CardContent className="p-4">
          <p className="text-xs text-muted-foreground">{t("reddit.howto.body")}</p>
        </CardContent>
      </Card>

      {!isLive && (
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-center justify-center gap-1 py-12 text-center">
            <p className="text-sm font-medium text-muted-foreground">
              {t("reddit.status.awaiting")}
            </p>
            <p className="text-xs text-muted-foreground/70">
              0 snapshots · {t("reddit.window")}
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
