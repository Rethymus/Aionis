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
import { Badge } from "@/components/ui/badge";
import { fmtDateShort } from "@/lib/format";
import { FilterPills, LoadMoreFooter, usePaged } from "@/components/stream/stream-kit";
import { useI18n } from "@/i18n/provider";
import { aionis } from "@/data/aionis";
import { stockUniverse } from "@/data/aionis/stock-universe";

// The terminal is a STATIC export: /stock/[ticker] pages exist only for the
// frozen OOS universe (generateStaticParams). A DEF 14A filer is a public
// company and usually carries a symbol, but most are still OUTSIDE the OOS
// universe — link only when a page exists, else plain-text ticker (same
// guard as ipo-view).
const STOCK_PAGE_TICKERS: ReadonlySet<string> = new Set(
  stockUniverse.stocks.map((s) => s.ticker),
);

type Def14aFilter = "all" | "new" | "amendment";

/** 代理委托书 · DEF 14A — the governance companion stream under /executives:
 *  definitive proxy statements (the statutory home of directors /
 *  executives / compensation / ownership) from the same EDGAR form-level
 *  machinery as /ipo's streams. Filing-stream v1: person names, pay, and
 *  holdings live inside the proxy HTML and are NOT parsed (disclosed);
 *  DEF 14A/A rows map to amendment (none today — amendments are DEFA14A,
 *  out of scope). Newest-first + status filter + client-side paging. */
function Def14aSection() {
  const { t } = useI18n();
  const f = aionis.def14a;
  const [filter, setFilter] = useState<Def14aFilter>("all");
  const { visibleCount, reset, loadMore } = usePaged(50);

  // Hooks stay unconditional (the early return below must not skip them).
  const counts = useMemo(() => {
    const c: Record<string, number> = { new: 0, amendment: 0 };
    for (const r of f.filings) {
      if (r.status in c) c[r.status] += 1;
    }
    return c;
  }, [f.filings]);
  const filtered = useMemo(
    () => (filter === "all" ? f.filings : f.filings.filter((r) => r.status === filter)),
    [f.filings, filter],
  );

  if (f.status !== "ok" || f.filings.length === 0) return null;
  const visible = filtered.slice(0, visibleCount);
  const apply = (k: Def14aFilter) => {
    setFilter(k);
    reset();
  };

  return (
    <Card className="min-w-0 overflow-hidden py-0">
      <CardHeader className="border-b">
        <CardTitle className="flex flex-wrap items-baseline gap-x-2 text-base">
          {t("executives.def14a.title")}
          <span className="font-mono text-xs font-normal text-muted-foreground tabular-nums">
            {f.total.toLocaleString("en-US")} · {f.issuers.toLocaleString("en-US")} ·{" "}
            {f.window.start} → {f.window.end}
          </span>
        </CardTitle>
        <CardDescription>{t("executives.def14a.note")}</CardDescription>
        <div className="pt-1">
          <FilterPills<Def14aFilter>
            label={t("executives.def14a.filter")}
            value={filter}
            onChange={apply}
            options={[
              { key: "all", label: t("executives.def14a.all"), count: f.filings.length },
              { key: "new", label: t("executives.def14a.status_new"), count: counts.new },
              { key: "amendment", label: t("executives.def14a.status_amendment"), count: counts.amendment },
            ]}
          />
        </div>
      </CardHeader>
      <CardContent className="p-0">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>{t("executives.def14a.company")}</TableHead>
              <TableHead>{t("executives.def14a.form")}</TableHead>
              <TableHead className="text-right">{t("executives.def14a.filed")}</TableHead>
              <TableHead className="text-right">EDGAR</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {visible.map((r) => (
              <TableRow key={r.doc_url || `${r.company}-${r.filed_date}-${r.form}`}>
                <TableCell className="max-w-[320px]">
                  <span className="block truncate font-medium" title={r.company}>
                    {r.company || "—"}
                  </span>
                  {r.ticker && STOCK_PAGE_TICKERS.has(r.ticker) ? (
                    <Link
                      href={`/stock/${r.ticker}`}
                      className="font-mono text-[11px] text-primary hover:underline"
                    >
                      {r.ticker}
                    </Link>
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
          {t("executives.def14a.limit_note")
            .replace("{total}", f.total.toLocaleString("en-US"))
            .replace("{visible}", f.filings.length.toLocaleString("en-US"))}
        </p>
      </CardContent>
    </Card>
  );
}

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

      {/* DEF 14A 代理委托书流 — the governance companion under the same
          route: proxy statements stream below the 8-K officer-change feed. */}
      <Def14aSection />

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
