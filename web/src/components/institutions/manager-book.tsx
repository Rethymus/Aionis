"use client";

import Link from "next/link";
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
import { useI18n } from "@/i18n/provider";
import type { DictKey } from "@/i18n/dict";
import type { Form13fManager } from "@/data/aionis";
import { stockUniverse } from "@/data/aionis/stock-universe";

// Shared rendering for one 13F manager's book (top-10 table + quarter-over-
// quarter changes). Used by BOTH the /institutions directory cards' detail
// target — the /manager/[cik] static page — and any future consumer, so the
// two surfaces can never drift apart.
//
// The terminal is a STATIC export: /stock/[ticker] pages exist only for the
// frozen OOS universe (generateStaticParams). A 13F issuer resolved to a
// ticker OUTSIDE that universe (foreign ADRs, OTC preferreds, ETF trusts)
// must not link — it would 404. We keep the resolved ticker as a plain-text
// label (identity info) and link only when a page exists.
const STOCK_PAGE_TICKERS: ReadonlySet<string> = new Set(
  stockUniverse.stocks.map((s) => s.ticker),
);

// The 7 display-only editorial categories (order = filter-chip order). These
// are human-curated tags from the fetch registry, NOT SEC data-source fields.
export const CATEGORY_ORDER = [
  "value",
  "growth",
  "activist",
  "macro",
  "quant",
  "china_background",
  "other",
] as const;

export type Category = (typeof CATEGORY_ORDER)[number];

// Map a category onto its i18n key (t() takes a strict DictKey — no
// template-literal keys).
export const CATEGORY_LABEL: Record<Category, DictKey> = {
  value: "institutions.cat_value",
  growth: "institutions.cat_growth",
  activist: "institutions.cat_activist",
  macro: "institutions.cat_macro",
  quant: "institutions.cat_quant",
  china_background: "institutions.cat_china_background",
  other: "institutions.cat_other",
};

/** i18n key for any category string; unknown values fall back to "other". */
export function categoryLabelKey(cat: string): DictKey {
  return (CATEGORY_ORDER as readonly string[]).includes(cat)
    ? CATEGORY_LABEL[cat as Category]
    : CATEGORY_LABEL.other;
}

// Canonical money/share formatting now lives in the shared format layer
// (xiaoyinsi P0-1); imported for local use and re-exported so existing
// manager-book consumers keep their imports unchanged.
import { fmtShares, fmtUsd } from "@/lib/format";
export { fmtShares, fmtUsd };

// Quarter-over-quarter change chips. Direction color convention follows the
// project's up/down utility classes (never hardcoded emerald/rose):
// new = primary emphasis, increased = up, reduced = down, exited = muted.
const DIRECTION_CLASS: Record<string, string> = {
  new: "",
  increased: "text-up",
  reduced: "text-down",
  exited: "text-muted-foreground",
};

// Map the JSON direction enum onto i18n keys (t() takes a strict DictKey —
// no template-literal keys).
const DIRECTION_LABEL: Record<string, "institutions.change_new" | "institutions.change_increased" | "institutions.change_reduced" | "institutions.change_exited"> = {
  new: "institutions.change_new",
  increased: "institutions.change_increased",
  reduced: "institutions.change_reduced",
  exited: "institutions.change_exited",
};

function IssuerLabel({
  issuer,
  ticker,
}: {
  issuer: string;
  ticker: string | null;
}) {
  if (ticker && STOCK_PAGE_TICKERS.has(ticker)) {
    return (
      <Link
        href={`/stock/${ticker}`}
        className="font-medium text-primary hover:underline"
      >
        {issuer}
      </Link>
    );
  }
  // No stock page for this ticker (or none resolved — as-filed abbreviations,
  // ETF units) — honest plain text, never a link that would 404.
  return <span className="font-medium">{issuer}</span>;
}

/** Latest-quarter top-10 holdings table for one manager. */
export function Top10Table({ manager }: { manager: Form13fManager }) {
  const { t } = useI18n();
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead className="w-8">#</TableHead>
          <TableHead>{t("institutions.col_issuer")}</TableHead>
          <TableHead className="text-right">{t("institutions.col_value")}</TableHead>
          <TableHead className="text-right">{t("institutions.col_shares")}</TableHead>
          <TableHead className="text-right">{t("institutions.col_pct")}</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {manager.top10.map((h, i) => (
          <TableRow key={`${h.cusip}-${h.option}-${i}`}>
            <TableCell className="text-muted-foreground tabular-nums">
              {i + 1}
            </TableCell>
            <TableCell>
              <IssuerLabel issuer={h.issuer} ticker={h.ticker} />
              {h.option === "CALL" || h.option === "PUT" ? (
                <Badge variant="outline" className="ml-2 px-1.5 py-0 text-[10px]">
                  {h.option === "CALL"
                    ? t("institutions.option_call")
                    : t("institutions.option_put")}
                </Badge>
              ) : null}
            </TableCell>
            <TableCell className="text-right tabular-nums">
              {fmtUsd(h.value)}
            </TableCell>
            <TableCell className="text-right tabular-nums text-muted-foreground">
              {fmtShares(h.shares)}
            </TableCell>
            <TableCell className="text-right tabular-nums font-medium">
              {h.pct.toFixed(2)}%
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

/** Quarter-over-quarter change chips for one manager (frame diff). */
export function ChangesBlock({ manager }: { manager: Form13fManager }) {
  const { t } = useI18n();
  if (manager.changes.length === 0) {
    return (
      <p className="text-xs text-muted-foreground">
        {t("institutions.no_changes")}
      </p>
    );
  }
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {manager.changes.map((c, i) => (
        <span
          key={`${c.cusip}-${c.direction}-${i}`}
          className="inline-flex items-center gap-1 text-sm"
        >
          {c.direction === "new" ? (
            <Badge className="px-1.5 text-[11px]">
              {t("institutions.change_new")}
            </Badge>
          ) : (
            <Badge
              variant="outline"
              className={cn(
                "px-1.5 text-[11px]",
                DIRECTION_CLASS[c.direction],
              )}
            >
              {t(DIRECTION_LABEL[c.direction])}
            </Badge>
          )}
          {c.ticker ? (
            STOCK_PAGE_TICKERS.has(c.ticker) ? (
              <Link
                href={`/stock/${c.ticker}`}
                className="text-primary hover:underline"
              >
                {c.ticker}
              </Link>
            ) : (
              // Resolved identity but no static stock page (ADR / OTC / ETF)
              // — plain-text ticker, never a 404 link.
              <span className="font-mono text-xs text-muted-foreground">
                {c.ticker}
              </span>
            )
          ) : null}
          <span className="text-muted-foreground">{c.issuer}</span>
          {c.option === "CALL" || c.option === "PUT" ? (
            <Badge variant="outline" className="px-1 py-0 text-[10px] text-muted-foreground">
              {c.option === "CALL"
                ? t("institutions.option_call")
                : t("institutions.option_put")}
            </Badge>
          ) : null}
          {c.delta_pct != null ? (
            <span
              className={cn(
                "font-mono text-xs tabular-nums",
                DIRECTION_CLASS[c.direction],
              )}
            >
              {c.delta_pct > 0 ? "+" : ""}
              {c.delta_pct.toFixed(1)}%
            </span>
          ) : null}
        </span>
      ))}
    </div>
  );
}
