"use client";

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
import { fmtDateShort, fmtUsd } from "@/lib/format";
import { FilterPills, LoadMoreFooter, usePaged } from "@/components/stream/stream-kit";
import { AvatarInitials } from "@/components/stream/avatar-initials";
import { useI18n } from "@/i18n/provider";
import { aionis } from "@/data/aionis";
import { stockUniverse } from "@/data/aionis/stock-universe";
import Link from "next/link";
import {
  Bar,
  BarChart,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

const PAGE_SIZE = 50;

type SideFilter = "all" | "buy" | "sell";

// Link tickers to /stock pages only where a static page exists (same guard
// as executives-view / congress-view).
const STOCK_PAGE_TICKERS_SET: ReadonlySet<string> = new Set(
  stockUniverse.stocks.map((s) => s.ticker),
);

export function InsidersView() {
  const { t } = useI18n();
  const f = aionis.form4;
  const yearlyHeading = "年度内部人买卖 / Yearly insider buys vs sells";
  const [side, setSide] = useState<SideFilter>("all");
  const { visibleCount, reset, loadMore } = usePaged(PAGE_SIZE);

  const recent = f.status === "ok" ? f.recent : [];
  const filtered = useMemo(
    () => (side === "all" ? recent : recent.filter((r) => r.action === side)),
    [recent, side],
  );
  const visible = filtered.slice(0, visibleCount);

  const applySide = (k: SideFilter) => {
    setSide(k);
    reset();
  };

  if (f.status === "awaiting_fetch") {
    return (
      <div className="flex flex-col gap-4">
        <header>
          <h1 className="text-2xl font-semibold tracking-[-0.032em]">{t("insiders.title")}</h1>
          <p className="mt-2 text-[13px] text-mute">{t("insiders.window")}</p>
        </header>
        <Card className="border-amber-500/30 bg-amber-500/5">
          <CardContent className="space-y-1 p-4">
            <p className="text-sm font-medium text-amber-700 dark:text-amber-400">
              {t("insiders.awaiting")}
            </p>
            <p className="text-xs text-muted-foreground">{f.methodology}</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <header>
        <h1 className="text-2xl font-semibold tracking-[-0.032em]">{t("insiders.title")}</h1>
        <p className="mt-2 text-[13px] text-mute">
          {t("insiders.window")}
          {f.status === "ok" ? ` · ${(f.buys + f.sells).toLocaleString("en-US")} · ${f.window}` : ""}
        </p>
      </header>

      <div className="flex items-center justify-between gap-3 rounded-xl border border-line bg-card px-5 py-4">
        <span className="text-[12px] text-mute">{t("insiders.buys")}</span>
        <span className="font-mono text-[17px] leading-none font-bold text-up tabular-nums">{f.buys}</span>
        <span className="h-4 w-px bg-line" aria-hidden="true" />
        <span className="text-[12px] text-mute">{t("insiders.sells")}</span>
        <span className="font-mono text-[17px] leading-none font-bold text-down tabular-nums">{f.sells}</span>
        <span className="h-4 w-px bg-line" aria-hidden="true" />
        <span className="text-[12px] text-mute">{t("insiders.n_insiders")}</span>
        <span className="font-mono text-[17px] leading-none font-bold tabular-nums">{f.n_filers}</span>
      </div>

      <Card className="overflow-hidden py-0">
        <CardHeader className="border-b">
          <CardTitle className="text-base">{t("insiders.recent")}</CardTitle>
          <CardDescription>{t("insiders.window")}</CardDescription>
          <div className="pt-1">
            <FilterPills<SideFilter>
              label={t("insiders.filter.label")}
              value={side}
              onChange={applySide}
              options={[
                { key: "all", label: t("insiders.filter.all"), count: recent.length },
                { key: "buy", label: t("insiders.buy"), count: recent.filter((r) => r.action === "buy").length },
                { key: "sell", label: t("insiders.sell"), count: recent.filter((r) => r.action === "sell").length },
              ]}
            />
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <div>
            {visible.map((r, i) => {
              const prev = i > 0 ? visible[i - 1] : null;
              const newDay = !prev || prev.date !== r.date;
              const buy = r.action === "buy";
              // Aligned-site insider row: initials circle + name over a mono
              // meta line (ticker · $value · shares · date), direction pill in
              // brand-soft / red-tint. The whole row links the EDGAR filing.
              const value =
                r.shares != null && r.price != null ? r.shares * r.price : null;
              const initials = r.filer
                .split(/\s+/)
                .map((w) => w[0])
                .filter(Boolean)
                .slice(0, 2)
                .join("")
                .toUpperCase();
              const rowHref = r.doc_url ?? "#";
              return (
                <div key={i}>
                {newDay ? (
                  <div className="border-t border-line2 bg-soft px-5 py-1.5 text-[11px] font-semibold text-mute first:border-t-0">
                    {fmtDateShort(r.date)}
                  </div>
                ) : null}
                <a
                  href={rowHref}
                  target="_blank"
                  rel="noopener noreferrer"
                  className={`transition-colors hover:bg-soft ${
                    i > 0 ? "border-t border-line2" : ""
                  }`}
                >
                  {/* Desktop variant (their 7-col grid, single line). */}
                  <div className="hidden items-center gap-[14px] px-5 py-3 text-[13px] whitespace-nowrap sm:grid sm:grid-cols-[2fr_84px_110px_110px_80px]">
                    <span className="flex min-w-0 items-center gap-[11px]">
                      <span className="flex h-8 w-8 flex-none items-center justify-center rounded-full border border-line bg-soft text-[10px] font-semibold text-sub">
                        {initials}
                      </span>
                      <span className="truncate font-semibold">{r.filer}</span>
                    </span>
                    <span
                      className={cn(
                        "justify-self-start rounded-full px-[10px] py-[3px] text-[12px] font-semibold",
                        buy ? "bg-brand-tint text-brand" : "bg-red-tint text-red",
                      )}
                    >
                      {t(buy ? "insiders.buy" : "insiders.sell")}
                    </span>
                    <span className="text-right font-mono font-semibold tabular-nums">
                      {value !== null ? fmtUsd(value) : "—"}
                    </span>
                    <span className="text-right font-mono text-sub tabular-nums">
                      {r.shares != null ? r.shares.toLocaleString() : "—"}
                    </span>
                    <span className="text-right font-mono text-xs text-mute tabular-nums">
                      {fmtDateShort(r.date)}
                    </span>
                  </div>
                  {/* Mobile variant (their stacked two-line row). */}
                  <div className="flex flex-col gap-2 px-4 py-3 sm:hidden">
                  <div className="flex items-center gap-2.5">
                    <span className="flex h-8 w-8 flex-none items-center justify-center rounded-full border border-line bg-soft text-[10px] font-semibold text-sub">
                      {initials}
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-[13px] font-semibold">
                        {r.filer}
                      </span>
                      <span className="block truncate text-[11px] text-mute">
                        {STOCK_PAGE_TICKERS_SET.has(r.ticker) ? (
                          <Link
                            href={`/stock/${r.ticker}`}
                            onClick={(e) => e.stopPropagation()}
                            className="hover:text-brand"
                          >
                            {r.ticker}
                          </Link>
                        ) : (
                          r.ticker
                        )}
                      </span>
                    </span>
                    <span
                      className={cn(
                        "flex-none rounded-full px-[10px] py-[3px] text-[12px] font-semibold",
                        buy ? "bg-brand-tint text-brand" : "bg-red-tint text-red",
                      )}
                    >
                      {t(buy ? "insiders.buy" : "insiders.sell")}
                    </span>
                  </div>
                    <span className="flex flex-wrap items-center gap-x-1.5 pl-10 font-mono text-[12px] text-mute tabular-nums">
                      <b className="font-semibold text-ink">{r.ticker}</b>·
                      <b className="font-semibold text-ink">
                        {value !== null ? fmtUsd(value) : "—"}
                      </b>
                      ·{r.shares != null ? r.shares.toLocaleString() : "—"} ·{" "}
                      {fmtDateShort(r.date)}
                    </span>
                  </div>
                </a>
                </div>
              );
            })}
          </div>
          <LoadMoreFooter
            shown={visible.length}
            total={filtered.length}
            onLoadMore={loadMore}
            pageSize={PAGE_SIZE}
          />
        </CardContent>
      </Card>
      <Card className="overflow-hidden py-0">
        <CardHeader className="border-b">
          <CardTitle className="text-base">{t("insiders.top")}</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="divide-y">
            {f.top_insiders.map((ins, i) => (
              <div key={ins.filer + i} className="flex items-center gap-3 px-4 py-2.5 text-sm">
                <span className="w-6 shrink-0 text-muted-foreground tabular-nums">{i + 1}</span>
                <AvatarInitials name={ins.filer} />
                <span className="truncate">{ins.filer}</span>
                <Badge variant="secondary" className="ml-auto shrink-0 tabular-nums">
                  {ins.count}
                </Badge>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {f.yearly && f.yearly.length > 0 && (
        <Card>
          <CardHeader className="border-b">
            <CardTitle className="text-base" title={t("insiders.termInsiderHint")}>
              {yearlyHeading}
            </CardTitle>
          </CardHeader>
          <CardContent className="p-2">
            <div className="h-[180px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={f.yearly} margin={{ top: 12, right: 20, bottom: 24, left: 12 }}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                  <XAxis
                    dataKey="year"
                    tickFormatter={(v) => String(v)}
                    className="text-xs"
                  />
                  <YAxis className="text-xs" />
                  <Tooltip
                    formatter={(v) => [Number(v).toLocaleString(), ""]}
                    labelFormatter={(l) => `Year: ${l}`}
                    contentStyle={{ fontSize: "12px" }}
                  />
                  <Legend />
                  <Bar dataKey="buys" stackId="a" fill="var(--up)" name={t("insiders.termBuys")} />
                  <Bar dataKey="sells" stackId="a" fill="var(--down)" name={t("insiders.termSells")} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      )}


      <p className="text-xs text-muted-foreground">{t("insiders.explain")}</p>
    </div>
  );
}
