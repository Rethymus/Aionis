"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { ExternalLinkIcon } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { fmtDateShort } from "@/lib/format";
import { FilterPills, LoadMoreFooter, usePaged } from "@/components/stream/stream-kit";
import { useI18n } from "@/i18n/provider";
import { aionis } from "@/data/aionis";
import { stockUniverse } from "@/data/aionis/stock-universe";

// The terminal is a STATIC export: /stock/[ticker] pages exist only for the
// frozen OOS universe (generateStaticParams). A periodic-report filer is often
// OUTSIDE that universe — link only when a page exists; otherwise keep the
// ticker as a plain-text label, same guard as ipo-view / institutions-view.
const STOCK_PAGE_TICKERS: ReadonlySet<string> = new Set(
  stockUniverse.stocks.map((s) => s.ticker),
);

export type FinDeadlineVariant = "annual" | "quarterly";
type StatusFilter = "all" | "new" | "amendment";

// Per-variant payload slice + form family (the immutable form type IS the
// new-vs-amendment discriminator — no guessed status field, the def14a
// precedent). All lookups keyed off `variant` so the shared view never
// branches on anything else.
const VARIANT: Record<
  FinDeadlineVariant,
  { base: string; amendment: string }
> = {
  annual: { base: "10-K", amendment: "10-K/A" },
  quarterly: { base: "10-Q", amendment: "10-Q/A" },
};

/** 财报截止流 · /annual + /quarterly — the 10-K / 10-Q deep cuts over the
 *  unified filing-stream v2 panel. The panel's 800-newest visible cap
 *  squeezes periodic reports out entirely in filing season (zero visible
 *  10-K/10-Q rows while the window counts 76 / 2,115), so each family rides
 *  its OWN newest-first slice (cap 400) from the same direct-EFTS parquet.
 *  KPIs show the FULL-window totals (*_total), never the payload cap; the
 *  new-vs-amendment filter derives from the immutable form type; ticker
 *  links are guarded against the static-export universe. */
export function FinDeadlineView({ variant }: { variant: FinDeadlineVariant }) {
  const { t } = useI18n();
  const f = aionis.filingStream;
  const forms = VARIANT[variant];
  const [filter, setFilter] = useState<StatusFilter>("all");
  const { visibleCount, reset, loadMore } = usePaged(50);

  // Hooks stay unconditional (the early return below must not skip them).
  const rows = useMemo(
    () =>
      f.status === "ok"
        ? variant === "annual"
          ? f.annual_filings
          : f.quarterly_filings
        : [],
    [f.status, f.annual_filings, f.quarterly_filings, variant],
  );
  const total = variant === "annual" ? f.annual_total : f.quarterly_total;
  const counts = useMemo(() => {
    const c = { new: 0, amendment: 0 };
    for (const r of rows) {
      if (r.form === forms.base) c.new += 1;
      else if (r.form === forms.amendment) c.amendment += 1;
    }
    return c;
  }, [rows, forms]);
  const filtered = useMemo(
    () =>
      filter === "all"
        ? rows
        : rows.filter((r) => r.form === (filter === "new" ? forms.base : forms.amendment)),
    [rows, filter, forms],
  );

  if (f.status !== "ok") {
    return (
      <Card className="border-amber-500/30 bg-amber-500/5">
        <CardContent className="space-y-1 p-4">
          <p className="text-sm font-medium text-amber-700 dark:text-amber-400">
            {t("filings.common.awaiting")}
          </p>
          <p className="text-xs text-muted-foreground">{f.methodology}</p>
        </CardContent>
      </Card>
    );
  }
  if (rows.length === 0) return null;
  const visible = filtered.slice(0, visibleCount);
  const apply = (k: StatusFilter) => {
    setFilter(k);
    reset();
  };

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>{t("filings.common.total")}</CardDescription>
            <CardTitle className="text-2xl tabular-nums">
              {total.toLocaleString("en-US")}
            </CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>{t("filings.common.visible")}</CardDescription>
            <CardTitle className="text-2xl tabular-nums">
              {rows.length.toLocaleString("en-US")}
            </CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>{t("filings.common.amendments")}</CardDescription>
            <CardTitle className="text-2xl tabular-nums">
              {counts.amendment.toLocaleString("en-US")}
            </CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>{t("filings.common.window_label")}</CardDescription>
            <CardTitle className="text-sm font-medium tabular-nums">
              {f.window.start} → {f.window.end}
            </CardTitle>
          </CardHeader>
        </Card>
      </div>

      <Card className="min-w-0 overflow-hidden py-0">
        <CardHeader className="border-b">
          <CardTitle className="flex flex-wrap items-baseline gap-x-2 text-base">
            {t(variant === "annual" ? "filings.annual.title" : "filings.quarterly.title")}
            <span className="font-mono text-xs font-normal text-muted-foreground tabular-nums">
              {total.toLocaleString("en-US")} · {f.window.start} → {f.window.end}
            </span>
          </CardTitle>
          <CardDescription>
            {t(variant === "annual" ? "filings.annual.note" : "filings.quarterly.note")}
          </CardDescription>
          <div className="pt-1">
            <FilterPills<StatusFilter>
              label={t("filings.common.filter")}
              value={filter}
              onChange={apply}
              options={[
                { key: "all", label: t("filings.common.all"), count: rows.length },
                { key: "new", label: t("filings.common.status_new"), count: counts.new },
                {
                  key: "amendment",
                  label: t("filings.common.status_amendment"),
                  count: counts.amendment,
                },
              ]}
            />
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t("filings.common.who")}</TableHead>
                <TableHead>{t("filings.common.form")}</TableHead>
                <TableHead className="text-right">{t("filings.common.filed")}</TableHead>
                <TableHead className="text-right">EDGAR</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {visible.map((r) => (
                <TableRow key={r.doc_url}>
                  <TableCell className="max-w-[340px]">
                    <span className="block truncate font-medium" title={r.who}>
                      {r.who}
                    </span>
                    {r.ticker && STOCK_PAGE_TICKERS.has(r.ticker) ? (
                      <Link
                        href={`/stock/${r.ticker}`}
                        className="font-mono text-[11px] text-primary hover:underline"
                      >
                        {r.ticker}
                      </Link>
                    ) : r.ticker ? (
                      <span className="font-mono text-[11px] text-muted-foreground">
                        {r.ticker}
                      </span>
                    ) : null}
                  </TableCell>
                  <TableCell>
                    <Badge variant="secondary" className="font-mono text-[11px]">
                      {r.form}
                    </Badge>
                  </TableCell>
                  <TableCell className="whitespace-nowrap text-right font-mono text-xs text-muted-foreground tabular-nums">
                    {fmtDateShort(r.filed_date)}
                  </TableCell>
                  <TableCell className="text-right">
                    {r.doc_url ? (
                      <a
                        href={r.doc_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-primary hover:underline"
                      >
                        EDGAR
                        <ExternalLinkIcon className="size-3" />
                      </a>
                    ) : (
                      <span className="text-muted-foreground">—</span>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          <LoadMoreFooter
            shown={visible.length}
            total={filtered.length}
            onLoadMore={loadMore}
            pageSize={50}
          />
          <p className="border-t px-4 py-2 text-[11px] leading-relaxed text-muted-foreground">
            {t("filings.common.limit_note")
              .replace("{total}", total.toLocaleString("en-US"))
              .replace("{visible}", rows.length.toLocaleString("en-US"))}
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle>{t("filings.common.methodology")}</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-xs leading-relaxed text-muted-foreground">
            {f.methodology}
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
