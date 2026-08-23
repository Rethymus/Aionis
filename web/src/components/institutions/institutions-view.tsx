"use client";

import Link from "next/link";
import { useState } from "react";
import { ArrowRightIcon, SearchIcon } from "lucide-react";
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
import { form13f } from "@/data/aionis/form13f";
import { aionis } from "@/data/aionis";
import {
  CATEGORY_LABEL,
  CATEGORY_ORDER,
  categoryLabelKey,
  fmtUsd,
  STOCK_PAGE_TICKERS,
  type Category,
} from "@/components/institutions/manager-book";

// /institutions = the CATEGORY DIRECTORY over the star-manager 13F registry:
// KPI row + filter chips (all + the 7 editorial categories) + one summary
// card per manager (name / zh label / category / latest quarter / positions /
// top holding / reported value), linking to the /manager/[cik] static detail
// page where the full top-10 book + quarter-over-quarter changes live.
// Everything is client-filtered — no extra data fetch, no server round-trip.

type CategoryFilter = "all" | Category;

/** ARK 家族 — 8-ETF daily holdings from ARK's own official CSVs (the
 *  institutions-cluster dimension xiaoyinsi carries; here it is a separate
 *  card block because ARK funds publish daily books, not 13F quarters).
 *  Top-5 by weight per fund with weight bars + the family-overlap table
 *  (tickers held by 2+ funds). Tickers link to /stock pages ONLY when a
 *  static page exists (same guard as the 13F book). */
function ArkSection() {
  const { t } = useI18n();
  const ark = aionis.ark;
  if (ark.status !== "ok" || ark.funds.length === 0) return null;

  const maxTop = Math.max(
    ...ark.funds.flatMap((f) => f.top.map((p) => p.weight_pct)),
    0.01,
  );

  const tickerCell = (ticker: string) =>
    STOCK_PAGE_TICKERS.has(ticker) ? (
      <Link
        href={`/stock/${ticker}`}
        className="font-mono text-xs font-semibold text-primary hover:underline"
      >
        {ticker}
      </Link>
    ) : (
      <span className="font-mono text-xs font-semibold">{ticker}</span>
    );

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <h2 className="text-lg font-semibold tracking-tight">
          {t("institutions.ark.title")}
        </h2>
        <span className="font-mono text-xs text-muted-foreground tabular-nums">
          {ark.as_of} · {ark.n_funds}/{ark.n_funds_expected} ·{" "}
          {ark.funds.reduce((a, f) => a + f.n_positions, 0)}{" "}
          {t("institutions.ark.positions")}
        </span>
      </div>
      <p className="text-xs text-muted-foreground">{t("institutions.ark.note")}</p>

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {ark.funds.map((f) => (
          <Card key={f.ticker} className="py-0">
            <CardHeader className="border-b">
              <div className="flex items-baseline justify-between gap-2">
                <CardTitle className="font-mono text-sm">{f.ticker}</CardTitle>
                <span className="font-mono text-[11px] text-muted-foreground tabular-nums">
                  {f.n_positions} · {f.as_of.slice(5)}
                </span>
              </div>
              <CardDescription className="truncate" title={f.fund}>
                {f.fund || "—"}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-1.5 p-3">
              {f.top.slice(0, 5).map((p) => (
                <div key={p.ticker} className="flex items-center gap-2">
                  <span className="w-14 shrink-0">{tickerCell(p.ticker)}</span>
                  <span className="h-1.5 flex-1 overflow-hidden rounded-full bg-muted">
                    <span
                      className="block h-full rounded-full bg-primary/50"
                      style={{ width: `${Math.max(2, Math.round((p.weight_pct / maxTop) * 100))}%` }}
                    />
                  </span>
                  <span className="w-10 shrink-0 text-right font-mono text-[11px] tabular-nums">
                    {p.weight_pct.toFixed(2)}%
                  </span>
                </div>
              ))}
            </CardContent>
          </Card>
        ))}
      </div>

      <Card className="min-w-0 py-0">
        <CardHeader className="border-b">
          <CardTitle className="text-base">{t("institutions.ark.overlap_title")}</CardTitle>
          <CardDescription>{t("institutions.ark.overlap_note")}</CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          <div className="divide-y">
            {ark.family_overlap.slice(0, 10).map((o) => (
              <div key={o.ticker} className="flex items-center gap-3 px-4 py-2">
                <span className="w-14 shrink-0">{tickerCell(o.ticker)}</span>
                <span className="min-w-0 flex-1 truncate text-xs text-muted-foreground" title={o.company}>
                  {o.company || "—"}
                </span>
                <span className="flex shrink-0 gap-1">
                  {o.funds.map((fd) => (
                    <span
                      key={fd}
                      className="rounded-[4px] bg-muted px-1.5 py-px font-mono text-[10px] font-medium text-muted-foreground"
                    >
                      {fd}
                    </span>
                  ))}
                </span>
                <span className="w-14 shrink-0 text-right font-mono text-[11px] tabular-nums">
                  {o.max_weight_pct.toFixed(2)}%
                </span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

export function InstitutionsView() {
  const { t } = useI18n();
  const f = form13f;
  const [filter, setFilter] = useState<CategoryFilter>("all");
  const [query, setQuery] = useState("");

  if (f.status !== "ok" || f.managers.length === 0) {
    return (
      <div className="space-y-6 p-4 md:p-6">
        <header className="space-y-1">
          <h1 className="text-2xl font-bold tracking-tight">
            {t("institutions.title")}
          </h1>
          <p className="text-sm text-muted-foreground">{t("institutions.window")}</p>
        </header>
        <Card className="border-amber-500/30 bg-amber-500/5">
          <CardContent className="space-y-1 p-4">
            <p className="text-sm font-medium text-amber-700 dark:text-amber-400">
              {t("institutions.awaiting")}
            </p>
            <p className="text-xs text-muted-foreground">{f.methodology}</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const combinedValue = f.managers.reduce((acc, m) => acc + m.total_value, 0);
  // Honest per-category counts drive both the chip labels and the filter —
  // categories with zero managers simply render no chip.
  const counts = new Map<string, number>();
  for (const m of f.managers) {
    counts.set(m.category, (counts.get(m.category) ?? 0) + 1);
  }
  const visible =
    filter === "all"
      ? f.managers
      : f.managers.filter((m) => m.category === filter);
  // Substring search over name / zh label / CIK (client-side, zero fetch).
  const needle = query.trim().toLowerCase();
  const searched = needle
    ? visible.filter(
        (m) =>
          m.name.toLowerCase().includes(needle) ||
          (m.zh_name ? m.zh_name.toLowerCase().includes(needle) : false) ||
          m.cik.includes(needle),
      )
    : visible;

  const chipBase =
    "rounded-full border px-3 py-1 text-xs font-medium transition-colors";

  return (
    <div className="space-y-6 p-4 md:p-6">
      <p className="text-xs font-medium text-primary">{t("institutions.role")}</p>
      <header className="space-y-1">
        <h1 className="text-2xl font-bold tracking-tight">{t("institutions.title")}</h1>
        <p className="text-sm text-muted-foreground">{t("institutions.window")}</p>
      </header>

      <div className="grid grid-cols-3 gap-3">
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">{t("institutions.kpi_managers")}</p>
            <p className="mt-1 text-2xl font-bold tabular-nums">{f.managers.length}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">{t("institutions.kpi_quarter")}</p>
            <p className="mt-1 text-2xl font-bold tabular-nums">{f.as_of}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">{t("institutions.kpi_value")}</p>
            <p className="mt-1 text-2xl font-bold tabular-nums">{fmtUsd(combinedValue)}</p>
          </CardContent>
        </Card>
      </div>

      {/* Category filter chips: 全部 + the 7 editorial categories, with the
          honest per-category manager count. Client-side filter only. */}
      <div className="flex flex-wrap items-center gap-1.5">
        <button
          type="button"
          onClick={() => setFilter("all")}
          aria-pressed={filter === "all"}
          className={cn(
            chipBase,
            filter === "all"
              ? "border-primary bg-primary text-primary-foreground"
              : "bg-background text-muted-foreground hover:text-foreground",
          )}
        >
          {t("institutions.cat_all")} ({f.managers.length})
        </button>
        {CATEGORY_ORDER.filter((c) => counts.get(c)).map((c) => (
          <button
            key={c}
            type="button"
            onClick={() => setFilter(c)}
            aria-pressed={filter === c}
            className={cn(
              chipBase,
              filter === c
                ? "border-primary bg-primary text-primary-foreground"
                : "bg-background text-muted-foreground hover:text-foreground",
            )}
          >
            {t(CATEGORY_LABEL[c])} ({counts.get(c)})
          </button>
        ))}
      </div>
      <p className="text-xs text-muted-foreground">{t("institutions.cat_note")}</p>

      {/* Manager search: name / 中文别名 / CIK substring, client-side. */}
      <div className="relative max-w-sm">
        <SearchIcon className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={t("institutions.search.placeholder")}
          aria-label={t("institutions.search.label")}
          className="h-9 w-full rounded-md border bg-transparent pl-9 pr-3 text-sm outline-none placeholder:text-muted-foreground focus-visible:ring-2 focus-visible:ring-ring"
        />
      </div>

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {searched.map((m) => (
          <Link key={m.cik} href={`/manager/${m.cik}`} className="group block">
            <Card className="h-full py-0 transition-colors group-hover:border-primary/40">
              <CardHeader className="border-b">
                <div className="flex flex-wrap items-center gap-2">
                  <CardTitle className="text-sm">{m.name}</CardTitle>
                  {m.zh_name ? (
                    <span className="text-xs text-muted-foreground">{m.zh_name}</span>
                  ) : null}
                </div>
                <CardDescription className="flex flex-wrap items-center gap-1.5">
                  <Badge variant="secondary" className="text-[11px]">
                    {t(categoryLabelKey(m.category))}
                  </Badge>
                  <Badge variant="outline" className="tabular-nums text-[11px]">
                    {m.quarter}
                  </Badge>
                  <span className="text-[11px]">
                    {t("institutions.filed")} {m.filed}
                  </span>
                </CardDescription>
              </CardHeader>
              <CardContent className="grid grid-cols-2 gap-x-3 gap-y-2 p-4 text-xs">
                <div>
                  <p className="text-muted-foreground">{t("institutions.n_positions")}</p>
                  <p className="mt-0.5 font-medium tabular-nums">{m.n_positions}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">{t("institutions.total_value")}</p>
                  <p className="mt-0.5 font-medium tabular-nums">
                    {fmtUsd(m.total_value)}
                  </p>
                </div>
                <div className="col-span-2">
                  <p className="text-muted-foreground">{t("institutions.top_holding")}</p>
                  <p className="mt-0.5 truncate font-medium">
                    {m.positions[0] ? m.positions[0].issuer : "—"}
                    {m.positions[0] ? (
                      <span className="ml-1 font-normal text-muted-foreground tabular-nums">
                        {m.positions[0].pct.toFixed(1)}%
                      </span>
                    ) : null}
                  </p>
                </div>
                <p className="col-span-2 mt-1 inline-flex items-center gap-1 text-primary">
                  {t("institutions.view_detail")}
                  <ArrowRightIcon className="size-3 transition-transform group-hover:translate-x-0.5" />
                </p>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
      {searched.length === 0 ? (
        <p className="text-sm italic text-muted-foreground">
          {t("institutions.search.empty")}
        </p>
      ) : null}

      {/* ARK 家族 (daily official CSVs) — the institutions cluster's
          non-13F member: daily books instead of quarterly filings. */}
      <ArkSection />

      <p className="text-xs text-muted-foreground">{t("institutions.explain")}</p>
    </div>
  );
}
