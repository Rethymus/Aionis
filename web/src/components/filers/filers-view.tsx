"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { ExternalLinkIcon, SearchIcon } from "lucide-react";
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
import { cn } from "@/lib/utils";
import { fmtDateShort } from "@/lib/format";
import { FilterPills, LoadMoreFooter, usePaged } from "@/components/stream/stream-kit";
import { useI18n } from "@/i18n/provider";
import { filers13f } from "@/data/aionis/filers13f";
import { form13f } from "@/data/aionis/form13f";

type SortKey = "latest" | "filings" | "name";

// /filers = the FULL 13F filer directory (every CIK that filed a 13F-HR(/A)
// over the trailing year — the ~9k-institution list dimension). The star-
// manager registry at /institutions stays editorial (40 managers); this page
// is the exhaustive machine directory: search + sort + honest counts, each
// row linking the filer's EDGAR 13F history. No holdings here — books stay
// in /institutions + /manager/[cik].
export function FilersView() {
  const { t } = useI18n();
  const f = filers13f;
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState<SortKey>("latest");
  const { visibleCount, reset, loadMore } = usePaged(50);

  const rows = f.status === "ok" ? f.filers : [];
  const searched = useMemo(() => {
    const needle = query.trim().toLowerCase();
    const base = needle
      ? rows.filter(
          (r) =>
            r.name.toLowerCase().includes(needle) || r.cik.includes(needle),
        )
      : rows;
    const sorted = [...base];
    if (sort === "latest") {
      sorted.sort((a, b) => (a.latest_filed < b.latest_filed ? 1 : a.latest_filed > b.latest_filed ? -1 : a.name.localeCompare(b.name)));
    } else if (sort === "filings") {
      sorted.sort((a, b) => b.n_filings + b.n_amendments - (a.n_filings + a.n_amendments) || a.name.localeCompare(b.name));
    } else {
      sorted.sort((a, b) => a.name.localeCompare(b.name));
    }
    return sorted;
  }, [rows, query, sort]);
  const visible = searched.slice(0, visibleCount);

  const applySort = (k: SortKey) => {
    setSort(k);
    reset();
  };

  if (f.status !== "ok" || rows.length === 0) {
    return (
      <Card className="border-amber-500/30 bg-amber-500/5">
        <CardContent className="space-y-1 p-4">
          <p className="text-sm font-medium text-amber-700 dark:text-amber-400">
            {t("filers.awaiting")}
          </p>
          <p className="text-xs text-muted-foreground">{f.methodology}</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-3">
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">{t("filers.kpi_filers")}</p>
            <p className="mt-1 text-2xl font-bold tabular-nums">
              {f.n_filers.toLocaleString("en-US")}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">{t("filers.kpi_filings")}</p>
            <p className="mt-1 text-2xl font-bold tabular-nums">
              {f.total_filings.toLocaleString("en-US")}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">{t("filers.kpi_window")}</p>
            <p className="mt-1 text-sm font-bold tabular-nums">
              {f.window.start} → {f.window.end}
            </p>
          </CardContent>
        </Card>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <div className="relative max-w-sm flex-1">
          <SearchIcon className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <input
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              reset();
            }}
            placeholder={t("filers.search.placeholder")}
            aria-label={t("filers.search.label")}
            className="h-9 w-full rounded-md border bg-transparent pl-9 pr-3 text-sm outline-none placeholder:text-muted-foreground focus-visible:ring-2 focus-visible:ring-ring"
          />
        </div>
        <FilterPills<SortKey>
          label={t("filers.sort.label")}
          value={sort}
          onChange={applySort}
          options={[
            { key: "latest", label: t("filers.sort.latest") },
            { key: "filings", label: t("filers.sort.filings") },
            { key: "name", label: t("filers.sort.name") },
          ]}
        />
      </div>

      <Card className="min-w-0 overflow-hidden py-0">
        <CardHeader className="border-b">
          <CardTitle className="text-base">{t("filers.title")}</CardTitle>
          <CardDescription>{t("filers.note")}</CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t("filers.filer")}</TableHead>
                <TableHead className="text-right">{t("filers.filings")}</TableHead>
                <TableHead className="hidden text-right md:table-cell">{t("filers.cik")}</TableHead>
                <TableHead className="text-right">{t("filers.latest")}</TableHead>
                <TableHead className="text-right">EDGAR</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {visible.map((r) => {
                // A star-manager CIK links its book page; everyone else links
                // the EDGAR 13F history (the source of truth either way).
                const isStar = form13f.managers.some((m) => m.cik === r.cik);
                const edgarUrl = `https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=${r.cik}&type=13F&dateb=&owner=include&count=40`;
                return (
                  <TableRow key={r.cik}>
                    <TableCell className="max-w-[360px]">
                      {isStar ? (
                        <Link
                          href={`/manager/${r.cik}`}
                          className="block truncate font-medium text-primary hover:underline"
                          title={r.name}
                        >
                          {r.name}
                        </Link>
                      ) : (
                        <span className="block truncate font-medium" title={r.name}>
                          {r.name}
                        </span>
                      )}
                      {r.n_amendments > 0 ? (
                        <span className="font-mono text-[11px] text-muted-foreground">
                          +{r.n_amendments}A
                        </span>
                      ) : null}
                    </TableCell>
                    <TableCell className="text-right font-mono text-xs tabular-nums">
                      {r.n_filings}
                    </TableCell>
                    <TableCell className="hidden text-right font-mono text-[11px] text-muted-foreground tabular-nums md:table-cell">
                      {r.cik}
                    </TableCell>
                    <TableCell className="whitespace-nowrap text-right font-mono text-xs text-muted-foreground tabular-nums">
                      {fmtDateShort(r.latest_filed)}
                    </TableCell>
                    <TableCell className="text-right">
                      <a
                        href={edgarUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-primary hover:underline"
                      >
                        13F
                        <ExternalLinkIcon className="size-3" />
                      </a>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
          <LoadMoreFooter
            shown={visible.length}
            total={searched.length}
            onLoadMore={loadMore}
            pageSize={50}
          />
          <p className={cn("border-t px-4 py-2 text-[11px] text-muted-foreground")}>
            {t("filers.footnote")}
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle>{t("filers.methodology")}</CardTitle>
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
