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
import { fmtDateShort } from "@/lib/format";
import { FilterPills, LoadMoreFooter, usePaged } from "@/components/stream/stream-kit";
import { useI18n } from "@/i18n/provider";
import { aionis } from "@/data/aionis";
import Link from "next/link";
import { ExternalLinkIcon } from "lucide-react";
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
      <div className="space-y-6 p-4 md:p-6">
        <header className="space-y-1">
          <h1 className="text-2xl font-bold tracking-tight">{t("insiders.title")}</h1>
          <p className="text-sm text-muted-foreground">{t("insiders.window")}</p>
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
    <div className="space-y-6 p-4 md:p-6">
      <p className="text-xs font-medium text-primary">{t("insiders.role")}</p>
      <header className="space-y-1">
        <h1 className="text-2xl font-bold tracking-tight">{t("insiders.title")}</h1>
        <p className="text-sm text-muted-foreground">{t("insiders.window")}</p>
        {f.status === "ok" ? (
          <p className="font-mono text-xs tabular-nums text-muted-foreground/80">
            {(f.buys + f.sells).toLocaleString("en-US")} · {f.window}
          </p>
        ) : null}
      </header>

      <div className="grid grid-cols-3 gap-3">
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">{t("insiders.buys")}</p>
            <p className="mt-1 text-2xl font-bold tabular-nums text-up">
              {f.buys}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">{t("insiders.sells")}</p>
            <p className="mt-1 text-2xl font-bold tabular-nums text-down">
              {f.sells}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">{t("insiders.n_insiders")}</p>
            <p className="mt-1 text-2xl font-bold tabular-nums">{f.n_filers}</p>
          </CardContent>
        </Card>
      </div>

      <Card className="overflow-hidden py-0">
        <CardHeader className="border-b">
          <CardTitle className="text-base">{t("insiders.top")}</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="divide-y">
            {f.top_insiders.map((ins, i) => (
              <div key={ins.filer + i} className="flex items-center gap-3 px-4 py-2.5 text-sm">
                <span className="w-6 shrink-0 text-muted-foreground tabular-nums">{i + 1}</span>
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
          <div className="divide-y">
            {visible.map((r, i) => {
              const buy = r.action === "buy";
              return (
                <div key={i} className="flex items-center gap-3 px-4 py-2.5 text-sm">
                  <span
                    className="w-14 shrink-0 font-mono text-xs text-muted-foreground"
                    title={r.date}
                  >
                    {fmtDateShort(r.date)}
                  </span>
                  <Badge
                    variant="outline"
                    className={cn(
                      "shrink-0 px-1.5 py-0 text-xs",
                      buy ? "badge-up" : "badge-down",
                    )}
                  >
                    {t(buy ? "insiders.buy" : "insiders.sell")}
                  </Badge>
                  <span className="w-32 shrink-0 truncate text-muted-foreground">{r.filer}</span>
                  <Link href={`/stock/${r.ticker}`} className="truncate font-medium text-primary hover:underline">{r.ticker}</Link>
                  {r.doc_url ? (
                    <a
                      href={r.doc_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      title="EDGAR"
                      aria-label={`EDGAR filing for ${r.ticker}`}
                      className="shrink-0 text-primary hover:underline"
                    >
                      <ExternalLinkIcon className="size-3" />
                    </a>
                  ) : (
                    <span className="shrink-0 text-muted-foreground">—</span>
                  )}
                  {r.shares != null ? (
                    <span className="ml-auto shrink-0 font-mono text-xs tabular-nums text-muted-foreground">
                      {r.shares.toLocaleString()} @ ${r.price ?? "—"}
                    </span>
                  ) : null}
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

      <p className="text-xs text-muted-foreground">{t("insiders.explain")}</p>
    </div>
  );
}
