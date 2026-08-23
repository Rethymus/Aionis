"use client";

import { useMemo } from "react";
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
import { LoadMoreFooter, usePaged } from "@/components/stream/stream-kit";
import { useI18n } from "@/i18n/provider";
import { aionis } from "@/data/aionis";

const PAGE_SIZE = 50;

/** GDELT headline stream — metadata + outbound links only. Every title links
 *  out to the publisher's original article (copyright stays there); nothing
 *  is summarized or rewritten. Machine order (GDELT sort=datedesc), not an
 *  editorial ranking; the fixed quoted-phrase query is displayed verbatim. */
export function NewsView() {
  const { t } = useI18n();
  const f = aionis.newsFeed;
  const { visibleCount, loadMore } = usePaged(PAGE_SIZE);

  const rows = useMemo(
    () => (f.status === "ok" ? f.items : []),
    [f.status, f.items],
  );
  const visible = useMemo(
    () => rows.slice(0, visibleCount),
    [rows, visibleCount],
  );

  if (f.status !== "ok" || rows.length === 0) {
    return (
      <div className="space-y-6">
        <header className="space-y-1">
          <h1 className="text-2xl font-bold tracking-tight">
            {t("news.title")}
          </h1>
          <p className="text-sm text-muted-foreground">{t("news.window")}</p>
        </header>
        <Card className="border-amber-500/30 bg-amber-500/5">
          <CardContent className="space-y-1 p-4">
            <p className="text-sm font-medium text-amber-700 dark:text-amber-400">
              {t("news.awaiting")}
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
            <CardDescription>{t("news.kpi_total")}</CardDescription>
            <CardTitle className="text-2xl tabular-nums">
              {f.total.toLocaleString("en-US")}
            </CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>{t("news.kpi_sources")}</CardDescription>
            <CardTitle className="text-2xl tabular-nums">
              {f.n_sources.toLocaleString("en-US")}
            </CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>{t("news.kpi_days")}</CardDescription>
            <CardTitle className="text-2xl tabular-nums">
              {f.by_day.length}
            </CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>{t("news.kpi_window")}</CardDescription>
            <CardTitle className="text-sm font-medium tabular-nums">
              {f.window.start} → {f.window.end}
            </CardTitle>
          </CardHeader>
        </Card>
      </div>

      <Card className="min-w-0 overflow-hidden py-0">
        <CardHeader className="border-b">
          <CardTitle className="flex flex-wrap items-baseline gap-x-2 text-base">
            {t("news.stream_title")}
            <span className="font-mono text-xs font-normal text-muted-foreground tabular-nums">
              {rows.length.toLocaleString("en-US")} · {f.window.start} → {f.window.end}
            </span>
          </CardTitle>
          <CardDescription>{t("news.stream_note")}</CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t("news.headline")}</TableHead>
                <TableHead className="text-right">{t("news.seen")}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {visible.map((r) => (
                <TableRow key={r.url}>
                  <TableCell className="max-w-[560px]">
                    <a
                      href={r.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-baseline gap-1 font-medium text-primary hover:underline"
                    >
                      <span className="truncate" title={r.title}>
                        {r.title || r.url}
                      </span>
                      <ExternalLinkIcon className="size-3 shrink-0" />
                    </a>
                    <span className="mt-0.5 flex flex-wrap items-center gap-1.5">
                      <Badge variant="secondary" className="font-mono text-[11px]">
                        {r.domain || "—"}
                      </Badge>
                      {(r.language || r.sourcecountry) && (
                        <span className="font-mono text-[11px] text-muted-foreground">
                          {[r.language, r.sourcecountry].filter(Boolean).join(" · ")}
                        </span>
                      )}
                    </span>
                  </TableCell>
                  <TableCell
                    className="whitespace-nowrap text-right font-mono text-xs text-muted-foreground tabular-nums"
                    title={r.seendate}
                  >
                    {fmtDateShort(r.seendate)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          <LoadMoreFooter
            shown={visible.length}
            total={rows.length}
            onLoadMore={loadMore}
            pageSize={PAGE_SIZE}
          />
          {f.total > rows.length && (
            <p className="border-t px-4 py-2 text-[11px] text-muted-foreground">
              {t("news.limit_note")
                .replace("{total}", f.total.toLocaleString("en-US"))
                .replace("{visible}", rows.length.toLocaleString("en-US"))}
            </p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle>{t("news.methodology")}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-1">
          <p className="font-mono text-xs text-muted-foreground">{f.query}</p>
          <p className="text-xs leading-relaxed text-muted-foreground">
            {f.methodology}
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
