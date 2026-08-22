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

// /executives v1 — filing-stream level (same honesty boundary as /congress):
// which company filed an 8-K Item 5.02 (officer/director change) WHEN, with
// the full item list and the EDGAR primary-doc link. Person-level detail
// (names, roles, appointed-vs-departed) is deferred, never guessed — the
// methodology card carries the disclosure.
const PAGE_SIZE = 50;

export function ExecutivesView() {
  const { t } = useI18n();
  const f = aionis.executives;
  const [company, setCompany] = useState<string>("all");
  const { visibleCount, reset, loadMore } = usePaged(PAGE_SIZE);

  const events = f.status === "ok" ? f.events : [];
  const filtered = useMemo(
    () => (company === "all" ? events : events.filter((e) => e.company === company)),
    [events, company],
  );
  const visible = filtered.slice(0, visibleCount);

  const applyCompany = (k: string) => {
    setCompany(k);
    reset();
  };

  if (f.status !== "ok" || f.events.length === 0) {
    return (
      <div className="space-y-6">
        <header className="space-y-1">
          <h1 className="text-2xl font-bold tracking-tight">
            {t("executives.title")}
          </h1>
          <p className="text-sm text-muted-foreground">{t("executives.window")}</p>
        </header>
        <Card className="border-amber-500/30 bg-amber-500/5">
          <CardContent className="space-y-1 p-4">
            <p className="text-sm font-medium text-amber-700 dark:text-amber-400">
              {t("executives.awaiting")}
            </p>
            <p className="text-xs text-muted-foreground">{f.methodology}</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <p className="text-xs font-medium text-primary">{t("executives.role")}</p>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>{t("executives.total")}</CardDescription>
            <CardTitle className="text-2xl tabular-nums">{f.total}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>{t("executives.issuers")}</CardDescription>
            <CardTitle className="text-2xl tabular-nums">{f.issuers}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>{t("executives.window_label")}</CardDescription>
            <CardTitle className="text-sm font-medium tabular-nums">
              {f.window.start} → {f.window.end}
            </CardTitle>
          </CardHeader>
        </Card>
      </div>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle>{t("executives.stream_title")}</CardTitle>
          <CardDescription>{t("executives.stream_note")}</CardDescription>
          <div className="pt-1">
            <FilterPills<string>
              label={t("executives.filter.label")}
              value={company}
              onChange={applyCompany}
              options={[
                { key: "all", label: t("executives.filter.all"), count: events.length },
                ...Object.entries(f.by_company).map(([name, n]) => ({
                  key: name,
                  label: name,
                  count: n,
                })),
              ]}
            />
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t("executives.date")}</TableHead>
                <TableHead>{t("executives.company")}</TableHead>
                <TableHead className="hidden md:table-cell">
                  {t("executives.items")}
                </TableHead>
                <TableHead className="text-right">{t("executives.source")}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {visible.map((e) => (
                <TableRow
                  key={e.doc_url || `${e.ticker}-${e.filing_date}-${e.items.join("-")}`}
                >
                  <TableCell
                    className="whitespace-nowrap tabular-nums text-muted-foreground"
                    title={e.filing_date}
                  >
                    {fmtDateShort(e.filing_date)}
                  </TableCell>
                  <TableCell>
                    <Link
                      href={`/stock/${e.ticker}`}
                      className="font-medium text-primary hover:underline"
                    >
                      {e.company}
                    </Link>
                    <span className="ml-2 text-xs text-muted-foreground">
                      {e.ticker}
                    </span>
                  </TableCell>
                  <TableCell className="hidden font-mono text-xs text-muted-foreground md:table-cell">
                    {e.items.join(", ")}
                  </TableCell>
                  <TableCell className="text-right">
                    {e.doc_url ? (
                      <a
                        href={e.doc_url}
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
          <CardTitle>{t("executives.methodology")}</CardTitle>
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
