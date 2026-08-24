"use client";

import { useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { useI18n } from "@/i18n/provider";
import { aionis } from "@/data/aionis";
import Link from "next/link";
import { ClockIcon, ShieldCheckIcon } from "lucide-react";
import { LoadMoreFooter, usePaged } from "@/components/stream/stream-kit";
import { STOCK_PAGE_TICKERS } from "@/components/institutions/manager-book";

type PressureEntry = {
  ticker: string;
  latest_mentions: number;
  velocity: number;
  crowding_z: number;
  bull_bear_lean: number;
  grade: string;
  n_days: number;
};

/** Reddit 热议榜 — ApeWisdom's own trending-stocks board (first-party
 *  fields, verbatim). Independent of OUR Atom collector panel below: this
 *  is the xiaoyinsi-/reddit alignment cut (their board's disclosed source),
 *  a TODAY snapshot with honest pagination disclosure (the free API served
 *  page 1 only of a declared 3 pages on 2026-08-23). Tickers link to
 *  /stock pages only where a static page exists. */
function TrendingSection() {
  const { t } = useI18n();
  const f = aionis.redditTrending;
  const { visibleCount, loadMore } = usePaged(50);
  const rows = useMemo(
    () => (f.status === "ok" ? f.tickers : []),
    [f.status, f.tickers],
  );
  const visible = useMemo(() => rows.slice(0, visibleCount), [rows, visibleCount]);

  if (f.status !== "ok" || rows.length === 0) return null;

  return (
    <Card className="min-w-0 overflow-hidden py-0">
      <CardHeader className="border-b">
        <CardTitle className="flex flex-wrap items-baseline gap-x-2 text-base">
          {t("reddit.trending.title")}
          <span className="font-mono text-xs font-normal text-muted-foreground tabular-nums">
            {f.n_rows}/{f.count_declared} · {f.as_of?.split("T")[0] ?? "—"}
          </span>
        </CardTitle>
        <CardDescription>{t("reddit.trending.note")}</CardDescription>
      </CardHeader>
      <CardContent className="p-0">
        <div className="divide-y">
          {visible.map((row) => {
            const delta =
              row.mentions_24h_ago === null
                ? null
                : row.mentions - row.mentions_24h_ago;
            return (
              <div key={`${row.rank}-${row.ticker}`} className="flex items-center gap-3 px-4 py-2 text-sm">
                <span className="w-7 shrink-0 text-right font-mono text-xs text-muted-foreground tabular-nums">
                  {row.rank}
                </span>
                {STOCK_PAGE_TICKERS.has(row.ticker) ? (
                  <Link
                    href={`/stock/${row.ticker}`}
                    className="shrink-0 font-mono text-xs font-semibold text-primary hover:underline"
                  >
                    {row.ticker}
                  </Link>
                ) : (
                  <span className="shrink-0 font-mono text-xs font-semibold">
                    {row.ticker}
                  </span>
                )}
                <span className="min-w-0 flex-1 truncate text-xs text-muted-foreground" title={row.name}>
                  {row.name || "—"}
                </span>
                <Badge variant="secondary" className="shrink-0 font-mono text-[11px] tabular-nums">
                  {t("reddit.trending.mentions")} {row.mentions}
                </Badge>
                {delta === null ? (
                  <span className="w-12 shrink-0 text-right font-mono text-[11px] text-muted-foreground">
                    —
                  </span>
                ) : (
                  <span
                    className={cn(
                      "w-12 shrink-0 text-right font-mono text-[11px] font-semibold tabular-nums",
                      delta > 0
                        ? "text-emerald-600 dark:text-emerald-400"
                        : delta < 0
                          ? "text-rose-600 dark:text-rose-400"
                          : "text-muted-foreground",
                    )}
                  >
                    {delta > 0 ? "+" : ""}
                    {delta}
                  </span>
                )}
              </div>
            );
          })}
        </div>
        <LoadMoreFooter
          shown={visible.length}
          total={rows.length}
          onLoadMore={loadMore}
          pageSize={50}
        />
        {!f.pagination_ok && (
          <p className="border-t px-4 py-2 text-[11px] text-muted-foreground">
            {t("reddit.trending.pagination_note")
              .replace("{rows}", String(f.n_rows))
              .replace("{declared}", String(f.count_declared))}
          </p>
        )}
      </CardContent>
    </Card>
  );
}

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
    <div className="flex flex-col gap-4">
      <p className="text-xs font-medium text-primary">{t("reddit.role")}</p>
      <header>
        <h1 className="text-2xl font-semibold tracking-[-0.032em]">{t("reddit.title")}</h1>
        <p className="mt-2 text-[13px] text-mute">{t("reddit.window")}</p>
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

      {/* ApeWisdom trending board — first-party TODAY snapshot, independent
          of the collector status below (renders whether or not the Atom
          collector is live). */}
      <TrendingSection />

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
                      ? "badge-up"
                      : pick.sentiment < -0.2
                      ? "badge-down"
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
                      <Link href={`/stock/${pick.ticker}`} className="truncate font-mono text-primary hover:underline">{pick.ticker}</Link>
                      <Badge
                        variant="secondary"
                        className="ml-auto shrink-0 tabular-nums"
                      >
                        {pick.mentions}
                      </Badge>
                      <Badge
                        variant="outline"
                        className={cn(
                          "shrink-0 px-1.5 py-0 text-xs",
                          sentimentColor
                        )}
                      >
                        {sentimentLabel} {pick.sentiment.toFixed(2)}
                      </Badge>
                      {pick.bull_ratio !== null && (
                        <span
                          className="ml-2 text-xs text-muted-foreground"
                          title={t("reddit.termBullRatioHint")}
                        >
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
          {/* Retail pressure (GME-style velocity × crowding-z × sentiment) */}
          {r.pressure && r.pressure.status !== "awaiting" ? (
            <Card className={cn("overflow-hidden py-0", r.pressure.status === "accumulating" && "border-dashed")}>
              <CardHeader className="border-b">
                <CardTitle className="text-base">{t("reddit.pressure.title")}</CardTitle>
                <CardDescription>{t("reddit.pressure.hint")}</CardDescription>
              </CardHeader>
              <CardContent className="p-0">
                {r.pressure.status === "ok" &&
                Object.keys(r.pressure.by_ticker as Record<string, unknown>).length > 0 ? (
                  <div className="divide-y">
                    {Object.entries(r.pressure.by_ticker as Record<string, PressureEntry>).map(([tk, pr]) => {
                      const tone =
                        pr.grade === "surge"
                          ? "border-rose-500/40 bg-rose-500/10 text-rose-600 dark:text-rose-400"
                          : pr.grade === "elevated"
                          ? "border-amber-500/40 bg-amber-500/10 text-amber-600 dark:text-amber-400"
                          : "border-muted-foreground/30 bg-muted/40 text-muted-foreground";
                      return (
                        <div key={tk} className="flex items-center gap-3 px-4 py-2.5 text-sm">
                          <span className="font-mono">{tk}</span>
                          <span className="ml-auto text-xs tabular-nums text-muted-foreground">
                            {t("reddit.pressure.velocity")} {pr.velocity.toFixed(2)}
                          </span>
                          <span className="text-xs tabular-nums text-muted-foreground">
                            {t("reddit.pressure.crowding")} {pr.crowding_z.toFixed(2)}
                          </span>
                          <Badge variant="outline" className={cn("shrink-0 px-1.5 py-0 text-xs", tone)}>
                            {t("reddit.pressure.grade")}: {pr.grade}
                          </Badge>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div className="p-4 text-xs text-muted-foreground">{t("reddit.pressure.accumulating")}</div>
                )}
              </CardContent>
            </Card>
          ) : null}
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
            <p className="text-xs text-muted-foreground">
              0 snapshots · {t("reddit.window")}
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
