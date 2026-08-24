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

/** 主题 ETF — 10 thematic funds' daily holdings from the ISSUERS' own
 *  official CSVs (iShares/BlackRock + Global X; the theme dimensions the
 *  ARK panel does not carry: semiconductor / clean energy / broad+active AI
 *  / cloud / blockchain / lithium-battery / robotics / cybersecurity).
 *  Same shape as ArkSection: top-5 by official weight with weight bars +
 *  the cross-fund resonance table (tickers held by 2+ theme ETFs ACROSS
 *  issuers — e.g. NVDA across 5 funds). Issuer badge discloses whose
 *  official file each book comes from. */
function ThemeEtfsSection() {
  const { t } = useI18n();
  const etfs = aionis.themeEtfs;
  if (etfs.status !== "ok" || etfs.funds.length === 0) return null;

  const maxTop = Math.max(
    ...etfs.funds.flatMap((f) => f.top.map((p) => p.weight_pct)),
    0.01,
  );
  const nIssuers = new Set(etfs.funds.map((f) => f.issuer)).size;

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
          {t("institutions.etf.title")}
        </h2>
        <span className="font-mono text-xs text-muted-foreground tabular-nums">
          {etfs.as_of} · {etfs.n_funds}/{etfs.n_funds_expected} ·{" "}
          {etfs.funds.reduce((a, f) => a + f.n_positions, 0)}{" "}
          {t("institutions.etf.positions")} · {nIssuers}{" "}
          {t("institutions.etf.issuers")}
        </span>
      </div>
      <p className="text-xs text-muted-foreground">{t("institutions.etf.note")}</p>

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {etfs.funds.map((f) => (
          <Card key={f.ticker} className="py-0">
            <CardHeader className="border-b">
              <div className="flex items-baseline justify-between gap-2">
                <CardTitle className="font-mono text-sm">{f.ticker}</CardTitle>
                <span className="font-mono text-[11px] text-muted-foreground tabular-nums">
                  {f.n_positions} · {f.as_of.slice(5)}
                </span>
              </div>
              <CardDescription className="space-y-0.5">
                <span
                  className="block truncate text-[11px] text-muted-foreground"
                  title={f.issuer}
                >
                  {f.issuer}
                </span>
                <span className="block truncate" title={f.fund}>
                  {f.fund || "—"}
                </span>
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
          <CardTitle className="text-base">{t("institutions.etf.resonance_title")}</CardTitle>
          <CardDescription>{t("institutions.etf.resonance_note")}</CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          <div className="divide-y">
            {etfs.cross_fund_overlap.slice(0, 10).map((o) => (
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
      <div className="flex flex-col gap-4">
        <header>
          <h1 className="text-2xl font-semibold tracking-[-0.032em]">
            {t("institutions.title")}
          </h1>
          <p className="mt-2 text-[13px] text-mute">{t("institutions.window")}</p>
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
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-[-0.032em]">{t("institutions.title")}</h1>
        <p className="mt-2 text-[13px] text-mute">
          {t("institutions.kpi_managers")} {f.managers.length} ·{" "}
          {t("institutions.total_value")} {fmtUsd(combinedValue)} · {f.as_of} ·{" "}
          {t("institutions.window")}
        </p>
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
              ? "border-brand bg-brand-tint font-mono font-semibold text-brand"
              : "border-line bg-card font-mono font-semibold text-sub hover:border-faint hover:text-ink",
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
                ? "border-brand bg-brand-tint font-mono font-semibold text-brand"
                : "border-line bg-card font-mono font-semibold text-sub hover:border-faint hover:text-ink",
            )}
          >
            {t(CATEGORY_LABEL[c])} ({counts.get(c)})
          </button>
        ))}
      </div>

      {/* Manager search: name / 中文别名 / CIK substring, client-side. */}
      <div className="relative max-w-sm">
        <SearchIcon className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-faint" />
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={t("institutions.search.placeholder")}
          aria-label={t("institutions.search.label")}
          className="h-9 w-full rounded-md border border-line bg-card pl-9 pr-3 text-[13px] outline-none placeholder:text-faint focus-visible:ring-2 focus-visible:ring-ring"
        />
      </div>

      {/* Ranked manager list (aligned-site anatomy): rank in brand mono,
          truncate name + mono value on line 1; 5px share bar + meta on
          line 2. Bar width = share of the largest visible book. */}
      <div className="overflow-x-auto rounded-xl border border-line bg-card">
        {searched.map((m, i) => (
          <Link
            key={m.cik}
            href={`/manager/${m.cik}`}
            className={`flex flex-col gap-1.5 px-4 py-3 transition-colors hover:bg-soft ${
              i > 0 ? "border-t border-line2" : ""
            }`}
          >
            <div className="flex items-baseline gap-2 text-[13px]">
              <span className="w-6 flex-none text-right font-mono font-bold text-brand">{i + 1}</span>
              <span className="min-w-0 flex-1 truncate font-semibold" title={m.name}>
                {m.name}
                {m.zh_name ? (
                  <span className="ml-1.5 font-normal text-mute">{m.zh_name}</span>
                ) : null}
              </span>
              <span className="flex-none font-mono font-semibold tabular-nums">
                {fmtUsd(m.total_value)}
              </span>
            </div>
            <div className="flex items-center gap-2.5 pl-8">
              <div className="h-[5px] flex-1 overflow-hidden rounded bg-line2">
                <div
                  className="h-full rounded bg-green-fill"
                  style={{
                    width: `${Math.max(
                      1.5,
                      (m.total_value / Math.max(...searched.map((x) => x.total_value), 1)) * 100,
                    )}%`,
                  }}
                />
              </div>
              <span className="flex-none font-mono text-[11px] text-mute tabular-nums">
                {t("institutions.n_positions")} {m.n_positions} · {m.quarter} ·{" "}
                {m.positions[0] ? `${m.positions[0].issuer} ${m.positions[0].pct.toFixed(1)}%` : "—"}
              </span>
            </div>
          </Link>
        ))}
      </div>
      {searched.length === 0 ? (
        <p className="text-[13px] italic text-mute">
          {t("institutions.search.empty")}
        </p>
      ) : null}

      {/* ARK 家族 (daily official CSVs) — the institutions cluster's
          non-13F member: daily books instead of quarterly filings. */}
      <ArkSection />

      {/* 主题 ETF (issuer-official CSVs) — the other theme-ETF dimension:
          non-ARK thematic families, daily books from their own issuers. */}
      <ThemeEtfsSection />

      <p className="text-xs text-muted-foreground">{t("institutions.explain")}</p>
    </div>
  );
}
