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

type FormDFilter = "all" | "new" | "amendment";

/** 豁免发行 · Form D — the primary-market (一级市场) companion stream: exempt
 *  offering notices (Reg D family) from the same EDGAR form-level machinery
 *  as the S-1/424B4 stream above. Filing-stream v1: offering amounts live
 *  inside the filing XML and are NOT parsed (disclosed); filers are private
 *  companies, so no ticker links are attempted. Newest-first + form filter
 *  + client-side paging, the same stream kit as the IPO table. */
function FormDSection() {
  const { t } = useI18n();
  const f = aionis.formD;
  const [filter, setFilter] = useState<FormDFilter>("all");
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
  const apply = (k: FormDFilter) => {
    setFilter(k);
    reset();
  };

  return (
    <Card className="min-w-0 overflow-hidden py-0">
      <CardHeader className="border-b">
        <CardTitle className="flex flex-wrap items-baseline gap-x-2 text-base">
          {t("ipo.form_d.title")}
          <span className="font-mono text-xs font-normal text-muted-foreground tabular-nums">
            {f.total.toLocaleString("en-US")} · {f.issuers.toLocaleString("en-US")} ·{" "}
            {f.window.start} → {f.window.end}
          </span>
        </CardTitle>
        <CardDescription>{t("ipo.form_d.note")}</CardDescription>
        <div className="pt-1">
          <FilterPills<FormDFilter>
            label={t("ipo.form_d.filter")}
            value={filter}
            onChange={apply}
            options={[
              { key: "all", label: t("ipo.form_d.all"), count: f.filings.length },
              { key: "new", label: t("ipo.form_d.status_new"), count: counts.new },
              { key: "amendment", label: t("ipo.form_d.status_amendment"), count: counts.amendment },
            ]}
          />
        </div>
      </CardHeader>
      <CardContent className="p-0">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>{t("ipo.form_d.company")}</TableHead>
              <TableHead>{t("ipo.form_d.form")}</TableHead>
              <TableHead className="text-right">{t("ipo.form_d.filed")}</TableHead>
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
          {t("ipo.form_d.limit_note")
            .replace("{total}", f.total.toLocaleString("en-US"))
            .replace("{visible}", f.filings.length.toLocaleString("en-US"))}
        </p>
      </CardContent>
    </Card>
  );
}

// Status → i18n key (t() takes a strict DictKey — no template literals).
const STATUS_LABEL: Record<string, "ipo.status_filed" | "ipo.status_priced"> = {
  filed: "ipo.status_filed",
  priced: "ipo.status_priced",
};

const PAGE_SIZE = 50;

type StatusFilter = "all" | "filed" | "priced";

// Offer price renders at full cent precision ($11.00 / $7.50) — NOT fmtUsd,
// whose magnitude rounding would blur sub-$1000 share prices.
function fmtOfferPrice(p: number | null): string {
  if (p == null || Number.isNaN(p)) return "—";
  return `$${p.toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

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

  // Bounded offer-price walk disclosure (TASK-DISP-H3): counts come straight
  // from the export's honest accounting block.
  const priceMeta = f.offer_price_meta;
  const priceNote = t("ipo.price.note")
    .replace("{targeted}", String(priceMeta?.newest_targeted ?? 0))
    .replace("{priced}", String(priceMeta?.priced_filings ?? 0))
    .replace("{budget}", String(priceMeta?.requests?.task_budget ?? 170));

  // Sidebar "recently priced" list: newest 424B4 filings, defensively sorted
  // by filed_date desc (source order is already descending, but the slice
  // must not depend on that).
  const recentPriced = useMemo(
    () =>
      [...filings]
        .filter((r) => r.status === "priced")
        .sort((a, b) => (a.filed_date < b.filed_date ? 1 : -1))
        .slice(0, 5),
    [filings],
  );

  const applyStatus = (k: StatusFilter) => {
    setStatus(k);
    reset();
  };

  if (f.status !== "ok" || f.filings.length === 0) {
    return (
      <div className="flex flex-col gap-4">
        <header>
          <h1 className="text-2xl font-semibold tracking-[-0.032em]">
            {t("ipo.title")}
          </h1>
          <p className="mt-2 text-[13px] text-mute">{t("ipo.window")}</p>
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
      {/* No visible page title in the ok state (the card title below is the
          Form D section) — sr-only h1 keeps heading navigation usable. */}
      <h1 className="sr-only">{t("nav.ipo")}</h1>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
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
        <Card className="max-md:col-span-2 md:col-span-1">
          <CardHeader className="pb-2">
            <CardDescription>{t("ipo.price.kpi")}</CardDescription>
            <CardTitle className="text-2xl tabular-nums">
              {f.offer_price_parsed}
              <span className="text-sm font-normal text-muted-foreground">
                {" "}
                / {f.by_status.priced ?? 0}
              </span>
            </CardTitle>
            <p className="text-[11px] leading-snug text-muted-foreground">
              {t("ipo.price.kpi_sub").replace(
                "{cap}",
                String(priceMeta?.target_cap_docs ?? 80),
              )}
              {" · "}
              {priceMeta?.coverage_pct_of_priced ?? 0}%
            </p>
          </CardHeader>
        </Card>
      </div>

      <div className="grid items-start gap-6 lg:grid-cols-[1fr_320px]">
        <Card className="min-w-0">
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
            {/* Bounded-parse honesty line (TASK-DISP-H3): what is priced,
                what got a value, and the request budget that bounds it. */}
            <p className="pt-1 text-[11px] leading-relaxed text-muted-foreground">
              {priceNote}
            </p>
          </CardHeader>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t("ipo.date")}</TableHead>
                  <TableHead>{t("ipo.company")}</TableHead>
                  <TableHead>{t("ipo.status")}</TableHead>
                  <TableHead className="text-right">{t("ipo.price.col")}</TableHead>
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
                    <TableCell className="whitespace-nowrap text-right font-mono text-xs tabular-nums">
                      {/* Honest blank: only exact-tier cover parses of the
                          newest ≤80 priced filings carry a value — everything
                          else (budget-clipped, low-confidence, no-match, S-1)
                          renders "—", never a guess. */}
                      {r.offer_price != null ? (
                        fmtOfferPrice(r.offer_price)
                      ) : (
                        <span className="text-muted-foreground">—</span>
                      )}
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

        {/* Sidebar at-a-glance card — the HONEST stand-in for a "top raises"
            widget: proceeds/offer prices live inside the prospectus documents
            and v1 does not parse them, so this surface shows only what the
            form-level data honestly carries (form-type counts + newest
            statutory 424B4 pricings), each linking EDGAR. */}
        <Card className="overflow-hidden py-0">
          <CardHeader className="border-b">
            <CardTitle className="text-base">{t("ipo.widget.title")}</CardTitle>
            <CardDescription className="tabular-nums">
              {f.window.start} → {f.window.end}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 p-4">
            <div className="space-y-2">
              <p className="text-xs font-medium text-muted-foreground">
                {t("ipo.widget.by_form")}
              </p>
              <div className="flex flex-wrap gap-1.5">
                {Object.entries(f.by_form)
                  .sort((a, b) => b[1] - a[1] || (a[0] < b[0] ? -1 : 1))
                  .map(([form, n]) => (
                    <Badge key={form} variant="secondary" className="gap-1.5">
                      <span className="font-mono text-[11px]">{form}</span>
                      <span className="tabular-nums text-muted-foreground">
                        {n.toLocaleString("en-US")}
                      </span>
                    </Badge>
                  ))}
              </div>
            </div>
            <div className="space-y-2">
              <p className="text-xs font-medium text-muted-foreground">
                {t("ipo.widget.recent_priced")}
              </p>
              <div className="divide-y">
                {recentPriced.length === 0 ? (
                  <p className="py-1 text-xs text-muted-foreground">—</p>
                ) : (
                  recentPriced.map((r) => (
                    <div key={r.doc_url || `${r.company}-${r.filed_date}`} className="flex items-center gap-2 py-1.5 text-sm">
                      <span
                        className="shrink-0 font-mono text-xs tabular-nums text-muted-foreground"
                        title={r.filed_date}
                      >
                        {fmtDateShort(r.filed_date)}
                      </span>
                      <span className="min-w-0 flex-1 truncate" title={r.company}>
                        {r.company}
                      </span>
                      {r.offer_price != null && (
                        <span
                          className="shrink-0 font-mono text-xs tabular-nums"
                          title={t("ipo.price.col")}
                        >
                          {fmtOfferPrice(r.offer_price)}
                        </span>
                      )}
                      {r.doc_url ? (
                        <a
                          href={r.doc_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          title="EDGAR"
                          aria-label={`EDGAR filing for ${r.company}`}
                          className="shrink-0 text-primary hover:underline"
                        >
                          <ExternalLinkIcon className="size-3" />
                        </a>
                      ) : (
                        <span className="shrink-0 text-muted-foreground">—</span>
                      )}
                    </div>
                  ))
                )}
              </div>
            </div>
            <p className="text-[11px] leading-relaxed text-muted-foreground">
              {t("ipo.widget.note")}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Form D 豁免发行流 — the primary-market companion under the same
          route: exempt notices stream below the public-registration stream. */}
      <FormDSection />

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
