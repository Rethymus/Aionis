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
import type { DictKey } from "@/i18n/dict";
import { aionis } from "@/data/aionis";
import { stockUniverse } from "@/data/aionis/stock-universe";

// The terminal is a STATIC export: /stock/[ticker] pages exist only for the
// frozen OOS universe (generateStaticParams). An IPO filer's ticker (parsed
// from the EDGAR display name) is almost always OUTSIDE that universe — a
// pre-IPO company by definition has no frozen OOS history. Link only when a
// page exists; otherwise keep the ticker as a plain-text label (identity
// info), same guard as institutions-view.
const STOCK_PAGE_TICKERS: ReadonlySet<string> = new Set(
  stockUniverse.stocks.map((s) => s.ticker),
);

// Status → i18n key (t() takes a strict DictKey — no template literals).
const STATUS_LABEL: Record<string, "ipo.status_filed" | "ipo.status_priced"> = {
  filed: "ipo.status_filed",
  priced: "ipo.status_priced",
};

const PAGE_SIZE = 50;

type StatusFilter = "all" | "filed" | "priced";

export function IpoView() {
  const { t } = useI18n();
  const f = aionis.ipo;
  const [status, setStatus] = useState<StatusFilter>("all");
  const { visibleCount, reset, loadMore } = usePaged(PAGE_SIZE);

  const filings = f.status === "ok" ? f.filings : [];
  const filtered = useMemo(
    () => (status === "all" ? filings : filings.filter((r) => r.status === status)),
    [filings, status],
  );
  const visible = filtered.slice(0, visibleCount);

  const applyStatus = (k: StatusFilter) => {
    setStatus(k);
    reset();
  };

  if (f.status !== "ok" || f.filings.length === 0) {
    return (
      <div className="space-y-6 p-4 md:p-6">
        <header className="space-y-1">
          <h1 className="text-2xl font-bold tracking-tight">
            {t("ipo.title")}
          </h1>
          <p className="text-sm text-muted-foreground">{t("ipo.window")}</p>
        </header>
        <Card className="border-amber-500/30 bg-amber-500/5">
          <CardContent className="space-y-1 p-4">
            <p className="text-sm font-medium text-amber-700 dark:text-amber-400">
              {t("ipo.awaiting")}
            </p>
            <p className="text-xs text-muted-foreground">{f.methodology}</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>{t("ipo.total")}</CardDescription>
            <CardTitle className="text-2xl tabular-nums">{f.total}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>{t("ipo.status_priced")}</CardDescription>
            <CardTitle className="text-2xl tabular-nums">
              {f.by_status.priced ?? 0}
            </CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>{t("ipo.status_filed")}</CardDescription>
            <CardTitle className="text-2xl tabular-nums">
              {f.by_status.filed ?? 0}
            </CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>{t("ipo.issuers")}</CardDescription>
            <CardTitle className="text-2xl tabular-nums">{f.issuers}</CardTitle>
          </CardHeader>
        </Card>
      </div>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle>{t("ipo.stream_title")}</CardTitle>
          <CardDescription>{t("ipo.stream_note")}</CardDescription>
          <div className="pt-1">
            <FilterPills<StatusFilter>
              label={t("ipo.filter.label")}
              value={status}
              onChange={applyStatus}
              options={[
                { key: "all", label: t("ipo.filter.all"), count: filings.length },
                { key: "filed", label: t("ipo.status_filed"), count: filings.filter((r) => r.status === "filed").length },
                { key: "priced", label: t("ipo.status_priced"), count: filings.filter((r) => r.status === "priced").length },
              ]}
            />
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t("ipo.date")}</TableHead>
                <TableHead>{t("ipo.company")}</TableHead>
                <TableHead>{t("ipo.status")}</TableHead>
                <TableHead className="hidden md:table-cell">
                  {t("ipo.form")}
                </TableHead>
                <TableHead className="text-right">{t("ipo.source")}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {visible.map((r) => (
                <TableRow key={r.doc_url || `${r.company}-${r.filed_date}-${r.form}`}>
                  <TableCell
                    className="whitespace-nowrap tabular-nums text-muted-foreground"
                    title={r.filed_date}
                  >
                    {fmtDateShort(r.filed_date)}
                  </TableCell>
                  <TableCell>
                    <span className="font-medium">{r.company}</span>
                    {r.ticker ? (
                      STOCK_PAGE_TICKERS.has(r.ticker) ? (
                        <Link
                          href={`/stock/${r.ticker}`}
                          className="ml-2 font-mono text-xs text-primary hover:underline"
                        >
                          {r.ticker}
                        </Link>
                      ) : (
                        // Resolved identity but no static stock page (a
                        // pre-IPO filer has no frozen OOS history) — plain
                        // text, never a 404 link.
                        <span className="ml-2 font-mono text-xs text-muted-foreground">
                          {r.ticker}
                        </span>
                      )
                    ) : null}
                  </TableCell>
                  <TableCell>
                    {/* Neutral secondary badge: filed vs priced is a stage
                        marker, not a good/bad signal. */}
                    <Badge variant="secondary">
                      {t((STATUS_LABEL[r.status] ?? "ipo.status_filed") as DictKey)}
                    </Badge>
                  </TableCell>
                  <TableCell className="hidden font-mono text-xs text-muted-foreground md:table-cell">
                    {r.form}
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
            pageSize={PAGE_SIZE}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle>{t("ipo.methodology")}</CardTitle>
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
