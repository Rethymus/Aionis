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

// Same guard as executives-view / manager-book.STOCK_PAGE_TICKERS: the terminal
// is a STATIC export and /stock/[ticker] pages exist only for the frozen OOS
// universe. An 8-K issuer outside it (BRK-B, delisted/renamed symbols, ...)
// keeps its company name as plain text — never a 404 deep link.
const STOCK_PAGE_TICKERS: ReadonlySet<string> = new Set(
  stockUniverse.stocks.map((s) => s.ticker),
);

// Category code → i18n key (t() takes a strict DictKey — no template literals).
// Exported: the overview home's 重大事件 card reuses the same mapping (single
// source — a category rendered on two pages must never carry two labels).
export const CATEGORY_LABEL: Record<string, string> = {
  merger_completion: "events.cat.merger_completion",
  delisting: "events.cat.delisting",
  control_change: "events.cat.control_change",
  non_reliance: "events.cat.non_reliance",
  agreement_termination: "events.cat.agreement_termination",
  officer_changes: "events.cat.officer_changes",
  exit_costs: "events.cat.exit_costs",
  financial_obligation: "events.cat.financial_obligation",
  major_agreement: "events.cat.major_agreement",
  security_terms: "events.cat.security_terms",
  charter_amendment: "events.cat.charter_amendment",
  vote_results: "events.cat.vote_results",
  results: "events.cat.results",
  reg_fd: "events.cat.reg_fd",
  other_events: "events.cat.other_events",
  exhibits: "events.cat.exhibits",
  other: "events.cat.other",
  unclassified: "events.cat.unclassified",
};

/** 全市场申报流 v2 — the unified cross-form feed queried DIRECTLY from SEC
 *  EDGAR (8-K / 10-K / 10-Q / S-1 family / 4 / D, /A amendments included;
 *  SC 13D / SC 13G via the daily index lanes). by_form pills are derived
 *  from the payload, so the v2 form family expands automatically. */
function StreamSection() {
  const { t } = useI18n();
  const f = aionis.filingStream;
  const [form, setForm] = useState<string>("all");
  const { visibleCount, reset, loadMore } = usePaged(50);

  const rows = useMemo(
    () => (f.status === "ok" ? f.filings : []),
    [f.status, f.filings],
  );
  const filtered = useMemo(
    () => (form === "all" ? rows : rows.filter((r) => r.form === form)),
    [rows, form],
  );
  if (f.status !== "ok" || rows.length === 0) return null;
  const visible = filtered.slice(0, visibleCount);
  const apply = (k: string) => {
    setForm(k);
    reset();
  };

  return (
    <Card className="min-w-0 overflow-hidden py-0">
      <CardHeader className="border-b">
        <CardTitle className="flex flex-wrap items-baseline gap-x-2 text-base">
          {t("events.stream_all.title")}
          <span className="font-mono text-xs font-normal text-muted-foreground tabular-nums">
            {f.n_visible.toLocaleString("en-US")} · {f.window.start} → {f.window.end}
          </span>
        </CardTitle>
        <CardDescription>{t("events.stream_all.note")}</CardDescription>
        <div className="pt-1">
          <FilterPills<string>
            label={t("events.stream_all.form")}
            value={form}
            onChange={apply}
            options={[
              { key: "all", label: t("events.stream_all.all"), count: rows.length },
              ...Object.entries(f.by_form).map(([k, n]) => ({
                key: k,
                label: k,
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
              <TableHead>{t("events.stream_all.form")}</TableHead>
              <TableHead>{t("events.stream_all.who")}</TableHead>
              <TableHead className="text-right">{t("events.stream_all.filed")}</TableHead>
              <TableHead className="text-right">EDGAR</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {visible.map((r) => (
              <TableRow key={r.doc_url}>
                <TableCell>
                  <Badge variant="secondary" className="font-mono text-[11px]">
                    {r.form}
                  </Badge>
                </TableCell>
                <TableCell className="max-w-[340px]">
                  <span className="block truncate font-medium" title={r.who}>
                    {r.who}
                  </span>
                  {r.ticker ? (
                    <span className="font-mono text-[11px] text-muted-foreground">
                      {r.ticker}
                    </span>
                  ) : null}
                </TableCell>
                <TableCell className="whitespace-nowrap text-right font-mono text-xs text-muted-foreground tabular-nums">
                  {fmtDateShort(r.filed_date)}
                </TableCell>
                <TableCell className="text-right">
                  <a
                    href={r.doc_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-primary hover:underline"
                  >
                    EDGAR
                    <ExternalLinkIcon className="size-3" />
                  </a>
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
      </CardContent>
    </Card>
  );
}

export function EventsView() {
  const { t } = useI18n();
  const f = aionis.form8k;
  const PAGE_SIZE = 50;
  const [cat, setCat] = useState<string>("all");
  const { visibleCount, reset, loadMore } = usePaged(PAGE_SIZE);

  const events = f.status === "ok" ? f.events : [];
  const filtered = useMemo(
    () => (cat === "all" ? events : events.filter((e) => e.category === cat)),
    [events, cat],
  );
  const visible = filtered.slice(0, visibleCount);

  const applyCat = (k: string) => {
    setCat(k);
    reset();
  };

  if (f.status !== "ok" || f.events.length === 0) {
    return (
      <div className="flex flex-col gap-4">
        <header>
          <h1 className="text-2xl font-semibold tracking-[-0.032em]">
            {t("events.title")}
          </h1>
          <p className="mt-2 text-[13px] text-mute">{t("events.window")}</p>
        </header>
        <Card className="border-amber-500/30 bg-amber-500/5">
          <CardContent className="space-y-1 p-4">
            <p className="text-sm font-medium text-amber-700 dark:text-amber-400">
              {t("events.awaiting")}
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
            <CardDescription>{t("events.total")}</CardDescription>
            <CardTitle className="text-2xl tabular-nums">{f.total}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>{t("events.issuers")}</CardDescription>
            <CardTitle className="text-2xl tabular-nums">{f.issuers}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>{t("events.unclassified")}</CardDescription>
            <CardTitle className="text-2xl tabular-nums">{f.unclassified}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>{t("events.window_label")}</CardDescription>
            <CardTitle className="text-sm font-medium tabular-nums">
              {f.window.start} → {f.window.end}
            </CardTitle>
          </CardHeader>
        </Card>
      </div>

      {/* 全市场申报流 — the unified cross-form feed above the 8-K stream:
          all forms first, then the 8-K deep cut below. */}
      <StreamSection />

      <div className="flex flex-wrap gap-2">
        {Object.entries(f.by_category).map(([cat, n]) => (
          <Badge key={cat} variant="secondary" className="gap-1">
            {t((CATEGORY_LABEL[cat] ?? "events.cat.other") as DictKey)}
            <span className="tabular-nums text-muted-foreground">{n}</span>
          </Badge>
        ))}
      </div>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle>{t("events.stream_title")}</CardTitle>
          <CardDescription>{t("events.stream_note")}</CardDescription>
          <div className="pt-1">
            <FilterPills<string>
              label={t("events.filter.label")}
              value={cat}
              onChange={applyCat}
              options={[
                { key: "all", label: t("events.filter.all"), count: events.length },
                ...Object.entries(f.by_category)
                  .sort((a, b) => b[1] - a[1])
                  .map(([c, n]) => ({
                    key: c,
                    label: t((CATEGORY_LABEL[c] ?? "events.cat.other") as DictKey),
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
                <TableHead>{t("events.date")}</TableHead>
                <TableHead>{t("events.company")}</TableHead>
                <TableHead>{t("events.category")}</TableHead>
                <TableHead className="hidden md:table-cell">
                  {t("events.items")}
                </TableHead>
                <TableHead className="text-right">{t("events.source")}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {visible.map((e) => (
                <TableRow key={e.doc_url || `${e.ticker}-${e.filing_date}-${e.form}`}>
                  <TableCell
                    className="whitespace-nowrap tabular-nums text-muted-foreground"
                    title={e.filing_date}
                  >
                    {fmtDateShort(e.filing_date)}
                  </TableCell>
                  <TableCell>
                    {STOCK_PAGE_TICKERS.has(e.ticker) ? (
                      <Link
                        href={`/stock/${e.ticker}`}
                        className="font-medium text-primary hover:underline"
                      >
                        {e.company}
                      </Link>
                    ) : (
                      <span className="font-medium">{e.company}</span>
                    )}
                    <span className="ml-2 text-xs text-muted-foreground">
                      {e.ticker}
                    </span>
                  </TableCell>
                  <TableCell>
                    <Badge variant="secondary">
                      {t((CATEGORY_LABEL[e.category] ?? "events.cat.other") as DictKey)}
                    </Badge>
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
          <CardTitle>{t("events.methodology")}</CardTitle>
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
