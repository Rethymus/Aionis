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

// Category code → i18n key (t() takes a strict DictKey — no template literals).
const CATEGORY_LABEL: Record<string, string> = {
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
      <div className="space-y-6 p-4 md:p-6">
        <header className="space-y-1">
          <h1 className="text-2xl font-bold tracking-tight">
            {t("events.title")}
          </h1>
          <p className="text-sm text-muted-foreground">{t("events.window")}</p>
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
