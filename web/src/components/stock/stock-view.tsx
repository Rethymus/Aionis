"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
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
import { aionis } from "@/data/aionis";
import { stockUniverse, type StockRow } from "@/data/aionis/stock-universe";
import { ProvenanceBadge } from "@/components/provenance-badge";
import { useLivePrices } from "@/lib/live-prices";
import { fmtShares, fmtUsd } from "@/lib/format";
import {
  ArrowUpIcon,
  ArrowDownIcon,
  MinusIcon,
  AlertTriangleIcon,
  SearchIcon,
  UsersIcon,
} from "lucide-react";

/** Honest-null disclaimer — mirrors picks-view's banner semantics. */
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
      </div>
    </div>
  );
}

function ScoreSparkline({ data }: { data: number[] }) {
  if (data.length < 2) return null;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const w = 100;
  const h = 24;
  const pts = data
    .map((v, i) => `${(i / (data.length - 1)) * w},${h - ((v - min) / range) * h}`)
    .join(" ");
  return (
    <svg
      viewBox={`0 0 ${w} ${h}`}
      className="h-12 w-full text-muted-foreground/60"
      preserveAspectRatio="none"
      aria-hidden
    >
      <polyline
        points={pts}
        fill="none"
        stroke="currentColor"
        strokeWidth={2}
        vectorEffect="non-scaling-stroke"
      />
    </svg>
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
        up ? "text-up" : "text-down",
      )}
      title={up ? `↑ ${change}` : `↓ ${Math.abs(change)}`}
    >
      {up ? <ArrowUpIcon className="size-3" /> : <ArrowDownIcon className="size-3" />}
      {Math.abs(change)}
    </span>
  );
}

function Stat({ label, children, hint }: { label: string; children: React.ReactNode; hint?: string }) {
  return (
    <div className="space-y-0.5" title={hint}>
      <p className="text-xs text-muted-foreground">{label}</p>
      <div className="text-lg font-bold tabular-nums">{children}</div>
    </div>
  );
}

/** 机构持有者（策展 13F 管理人反查，xiaoyinsi /stock 同位模块——其同位页当前
 *  空壳"共 0 家"，Aionis 用一手 13F 填上）。窗口 = 各管理人最新季前十大持仓；
 *  pct 口径按本页所列持有人的市值合计（脚注披露），与其"占前十"同型。 */
function InstitutionalHolders({ ticker }: { ticker: string }) {
  const { t } = useI18n();
  const f = aionis.form13f;
  const holders = useMemo(() => {
    if (f.status !== "ok") return [];
    const rows: { cik: string; name: string; value: number; shares: number; quarter: string }[] = [];
    for (const m of f.managers) {
      for (const h of m.top10) {
        if (h.ticker === ticker) {
          rows.push({
            cik: m.cik,
            name: m.zh_name || m.name,
            value: h.value,
            shares: h.shares,
            quarter: m.quarter,
          });
        }
      }
    }
    rows.sort((a, b) => b.value - a.value);
    return rows.slice(0, 10);
  }, [f, ticker]);

  const total = holders.reduce((s, h) => s + h.value, 0);

  return (
    <Card className="py-0 md:col-span-2">
      <CardHeader className="border-b">
        <CardTitle className="flex flex-wrap items-center gap-2 text-base">
          {t("stock.holders")}
          <span className="font-mono text-xs font-normal text-muted-foreground">
            {holders.length > 0 ? `${holders.length} · ${holders[0].quarter}` : ""}
          </span>
        </CardTitle>
        <CardDescription>
          {t("stock.holders.note")}
          {holders.length > 0 ? (
            <span className="ml-1 font-mono text-[11px] text-muted-foreground/70">
              {t("stock.holders.footnote")}
            </span>
          ) : null}
        </CardDescription>
      </CardHeader>
      <CardContent className="p-0">
        {holders.length === 0 ? (
          <p className="p-4 text-sm italic text-muted-foreground">
            {t("stock.holders.empty")}
          </p>
        ) : (
          <div className="divide-y">
            {holders.map((h, i) => (
              <div key={h.cik} className="flex items-center gap-3 px-4 py-2.5 text-sm">
                <span className="w-6 shrink-0 tabular-nums text-muted-foreground">{i + 1}</span>
                <Link
                  href={`/manager/${h.cik}`}
                  className="truncate font-medium text-primary hover:underline"
                >
                  {h.name}
                </Link>
                <span className="ml-auto shrink-0 font-mono text-xs tabular-nums text-muted-foreground">
                  {fmtUsd(h.value)}
                </span>
                <span className="w-20 shrink-0 text-right font-mono text-xs tabular-nums text-muted-foreground">
                  {fmtShares(h.shares)}
                </span>
                <span className="w-16 shrink-0 text-right font-mono text-xs font-semibold tabular-nums">
                  {total > 0 ? `${((h.value / total) * 100).toFixed(1)}%` : "—"}
                </span>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

/** Ticker switcher: client-side search over the whole frozen universe. */
function TickerSwitcher({ current }: { current: string }) {
  const { t } = useI18n();
  const [q, setQ] = useState("");
  const matches = useMemo(() => {
    const needle = q.trim().toLowerCase();
    if (!needle) return [];
    return stockUniverse.stocks
      .filter(
        (s) =>
          s.ticker.toLowerCase().includes(needle) ||
          (s.name && s.name.toLowerCase().includes(needle)),
      )
      .slice(0, 8);
  }, [q]);

  return (
    <Card className="py-0">
      <CardHeader className="border-b">
        <CardTitle className="flex items-center gap-2 text-base">
          <SearchIcon className="size-4 text-muted-foreground" />
          {t("stock.search.label")}
        </CardTitle>
        <CardDescription className="font-mono text-xs">
          {stockUniverse.n_stocks} · {t("stock.search.hint")}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-2 p-4">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder={t("stock.search.placeholder")}
          aria-label={t("stock.search.label")}
          className="h-9 w-full rounded-md border bg-transparent px-3 text-sm outline-none placeholder:text-muted-foreground focus-visible:ring-2 focus-visible:ring-ring"
        />
        {q.trim() !== "" && matches.length === 0 && (
          <p className="text-xs italic text-muted-foreground">{t("stock.search.none")}</p>
        )}
        <div className="flex flex-wrap gap-1.5">
          {matches.map((s) => (
            <Badge
              key={s.ticker}
              variant={s.ticker === current ? "default" : "outline"}
              className="max-w-full truncate font-normal"
            >
              {s.ticker === current ? (
                <span className="truncate">{s.ticker}</span>
              ) : (
                <Link href={`/stock/${s.ticker}`} className="truncate hover:underline">
                  {s.ticker}
                  {s.name ? ` · ${s.name}` : ""}
                </Link>
              )}
            </Badge>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

export function StockView({ ticker }: { ticker: string }) {
  const { t } = useI18n();
  const stock = useMemo<StockRow | undefined>(
    () => stockUniverse.stocks.find((s) => s.ticker === ticker),
    [ticker],
  );
  const { prices, updatedAt } = useLivePrices(
    stock ? [{ ticker: stock.ticker, region: stock.region }] : [],
  );
  // 1s tick so the relative "updated Xs ago" indicator stays live.
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1_000);
    return () => clearInterval(id);
  }, []);
  const agoSec = updatedAt ? Math.max(0, Math.round((now - updatedAt) / 1000)) : null;

  if (!stock) {
    return (
      <div className="space-y-6 p-4 md:p-6">
        <header className="space-y-1">
          <h1 className="font-mono text-2xl font-bold tracking-tight">{ticker}</h1>
        </header>
        <Card className="border-amber-500/30 bg-amber-500/5">
          <CardContent className="space-y-3 p-4 text-sm text-muted-foreground">
            <p>{t("stock.notfound.body")}</p>
            <Link href="/picks" className="text-primary hover:underline">
              {t("stock.notfound.back")}
            </Link>
          </CardContent>
        </Card>
        <TickerSwitcher current={ticker} />
      </div>
    );
  }

  const displayName = stock.name && stock.name.length > 0 ? stock.name : stock.ticker;
  const regionLabel = t(stock.region === "us" ? "picks.region.us" : "picks.region.cn");
  const regionMeta = aionis.picksMeta.regions[stock.region]?.meta;
  const baseRate = regionMeta?.base_rate ?? 0.5;
  const live = prices[stock.ticker];
  const hist = stock.scores.filter((v): v is number => v !== null);
  const histMean = hist.length ? hist.reduce((a, b) => a + b, 0) / hist.length : null;
  const histStd = hist.length > 1
    ? Math.sqrt(hist.reduce((a, b) => a + (b - (histMean ?? 0)) ** 2, 0) / (hist.length - 1))
    : null;
  const percentile = Math.round((1 - (stock.rank - 1) / stock.n_region) * 100);
  // Sector standing within the region's sector table (frozen panel).
  const sectorRows = aionis.sectorBreakdown.all_sectors ?? aionis.sectorBreakdown.sectors ?? [];
  const sectorRow = sectorRows.find(
    (r) => r.sector === stock.sector && r.regions.includes(stock.region),
  );
  const regionSectorRows = sectorRows.filter((r) => r.regions.includes(stock.region));
  const sectorRank = sectorRow
    ? regionSectorRows.findIndex((r) => r.sector === stock.sector) + 1
    : null;

  return (
    <div className="space-y-6 p-4 md:p-6">
      <p className="text-xs font-medium text-primary">{t("stock.role")}</p>
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 space-y-1.5">
          <h1 className="flex flex-wrap items-baseline gap-2 text-2xl font-bold tracking-tight">
            <span className="truncate">{displayName}</span>
            <span className="font-mono text-base text-muted-foreground">{stock.ticker}</span>
            <Badge variant="outline" className="px-1.5 py-0 font-normal">
              {regionLabel}
            </Badge>
          </h1>
          <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            {stock.sector ? <span>{stock.sector}</span> : null}
            {live?.price !== undefined && live?.price !== null ? (
              <span className="font-mono tabular-nums" title={t("stock.live.note")}>
                {agoSec !== null ? (
                  <span
                    className="mr-1 text-muted-foreground/70"
                    title={live.as_of ?? undefined}
                  >
                    {t("stock.live.updated.prefix")}
                    {agoSec}
                    {t("stock.live.updated.suffix")}
                  </span>
                ) : null}
                {live.price.toFixed(2)}
                {live.change_pct !== null && live.change_pct !== undefined ? (
                  <span
                    className={cn(
                      "ml-1",
                      live.change_pct >= 0
                        ? "text-up"
                        : "text-down",
                    )}
                  >
                    {live.change_pct >= 0 ? "+" : ""}
                    {live.change_pct.toFixed(2)}%
                  </span>
                ) : null}
              </span>
            ) : null}
          </div>
        </div>
        <ProvenanceBadge ts={stockUniverse.as_of[stock.region]} frozen />
      </header>

      <NullDisclaimer />

      <div className="grid gap-4 md:grid-cols-2">
        <Card className="py-0">
          <CardHeader className="border-b">
            <CardTitle className="text-base">{t("stock.readout")}</CardTitle>
            <CardDescription>{t("stock.readout.note")}</CardDescription>
          </CardHeader>
          <CardContent className="grid grid-cols-2 gap-4 p-4">
            <Stat label={t("stock.score")} hint={t("stock.score.hint")}>
              <span className={stock.score >= 0 ? "text-up" : "text-down"}>
                {stock.score > 0 ? "+" : ""}
                {stock.score.toFixed(2)}
              </span>
            </Stat>
            <Stat label={t("stock.rank")}>
              {stock.rank}
              <span className="text-sm font-normal text-muted-foreground">
                {" / "}
                {stock.n_region}
              </span>
            </Stat>
            <Stat label={t("stock.percentile")} hint={t("stock.percentile.hint")}>
              {percentile}%
            </Stat>
            <Stat label={t("stock.rank_change")}>
              <Change change={stock.rank_change} />
            </Stat>
            <div className="col-span-2 space-y-1">
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span>{t("stock.prob")}</span>
                <span className="font-mono tabular-nums">
                  {(stock.prob_up * 100).toFixed(1)}% · {t("stock.baserate")}{" "}
                  {(baseRate * 100).toFixed(1)}%
                </span>
              </div>
              <div className="h-2 w-full overflow-hidden rounded-full bg-muted/50">
                <div
                  className={cn(
                    "h-full rounded-full",
                    stock.prob_up > 0.5
                      ? "bg-up"
                      : "bg-down",
                  )}
                  style={{ width: `${Math.round(stock.prob_up * 100)}%` }}
                />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="py-0">
          <CardHeader className="border-b">
            <CardTitle className="text-base">{t("stock.history")}</CardTitle>
            <CardDescription className="font-mono text-xs">
              {stockUniverse.months[0]} → {stockUniverse.months[stockUniverse.months.length - 1]}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 p-4">
            <ScoreSparkline data={hist} />
            <div className="grid grid-cols-3 gap-2 text-xs">
              <div>
                <p className="text-muted-foreground">{t("stock.mean")}</p>
                <p className="font-mono tabular-nums">
                  {histMean !== null ? histMean.toFixed(2) : "—"}
                </p>
              </div>
              <div>
                <p className="text-muted-foreground">{t("stock.std")}</p>
                <p className="font-mono tabular-nums">
                  {histStd !== null ? histStd.toFixed(2) : "—"}
                </p>
              </div>
              <div>
                <p className="text-muted-foreground">{t("stock.months.n")}</p>
                <p className="font-mono tabular-nums">{hist.length}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="py-0">
          <CardHeader className="border-b">
            <CardTitle className="text-base">{t("stock.sector.context")}</CardTitle>
            <CardDescription>{t("stock.sector.note")}</CardDescription>
          </CardHeader>
          <CardContent className="p-4">
            {sectorRow ? (
              <div className="grid grid-cols-2 gap-3">
                <Stat label={t("stock.sector.mean_score")}>
                  {sectorRow.mean_score > 0 ? "+" : ""}
                  {sectorRow.mean_score.toFixed(2)}
                </Stat>
                <Stat label={t("stock.sector.mean_prob")}>
                  {(sectorRow.mean_prob_up * 100).toFixed(1)}%
                </Stat>
                <Stat label={t("stock.sector.rank")}>
                  {sectorRank !== null ? `${sectorRank} / ${regionSectorRows.length}` : "—"}
                </Stat>
                <Stat label={t("stock.sector.n")}>{sectorRow.n_stocks}</Stat>
              </div>
            ) : (
              <p className="text-sm italic text-muted-foreground">{t("stock.sector.none")}</p>
            )}
          </CardContent>
        </Card>

        <Card className="py-0">
          <CardHeader className="border-b">
            <CardTitle className="flex items-center gap-2 text-base">
              <UsersIcon className="size-4 text-muted-foreground" />
              {t("stock.corroboration")}
            </CardTitle>
            <CardDescription>{t("stock.corroboration.note")}</CardDescription>
          </CardHeader>
          <CardContent className="p-4">
            <div className="grid grid-cols-3 gap-3">
              <Stat label={t("stock.sm")} hint={stock.smart_money_latest ?? undefined}>
                {stock.smart_money_n ?? "—"}
              </Stat>
              <Stat label={t("stock.f4")} hint={stock.form4_latest ?? undefined}>
                {stock.form4_n ?? "—"}
              </Stat>
              <Stat label={t("stock.reddit")}>{stock.reddit_mentions ?? "—"}</Stat>
            </div>
            <Link
              href="/confirmation"
              className="mt-3 inline-block text-xs text-primary hover:underline"
            >
              {t("stock.corroboration.link")}
            </Link>
          </CardContent>
        </Card>

        <InstitutionalHolders ticker={stock.ticker} />
      </div>

      <TickerSwitcher current={stock.ticker} />

      <Card className="border-muted">
        <CardHeader>
          <CardTitle className="text-sm">{t("stock.methodology")}</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="font-mono text-xs leading-relaxed text-muted-foreground">
            {stockUniverse.methodology}
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
