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
import type { Form13fManager } from "@/data/aionis/form13f";
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
export const STOCK_PAGE_TICKERS: ReadonlySet<string> = new Set(
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

/** Latest-quarter visible book (up to 50 positions) for one manager. */
export function PositionsTable({ manager }: { manager: Form13fManager }) {
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
        {manager.positions.map((h, i) => (
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

/** Top-6 concentration bars over the visible book (xiaoyinsi-style widget).
 *  Shares are renormalized over the page's visible positions total — the
 *  same 口径 footnote the reference site uses ("按本页前 N 大持仓市值合计")
 *  — NOT over the as-filed total, so a >50-position book stays honest. */
export function ConcentrationBlock({ manager }: { manager: Form13fManager }) {
  const { t } = useI18n();
  const positions = manager.positions;
  if (positions.length === 0) return null;
  const visibleTotal = positions.reduce((s, h) => s + h.value, 0);
  if (visibleTotal <= 0) return null;
  const top6 = positions.slice(0, 6);
  const top6Share = top6.reduce((s, h) => s + h.value, 0) / visibleTotal;
  const otherShare = Math.max(0, 1 - top6Share);
  const barCls = "h-2 rounded-full bg-primary/70";
  const otherCls = "h-2 rounded-full bg-muted";
  return (
    <div className="space-y-2 p-4">
      <p className="text-xs font-medium text-muted-foreground">
        {t("institutions.concentration.title")} ·{" "}
        <span className="tabular-nums font-semibold text-foreground">
          {(top6Share * 100).toFixed(0)}%
        </span>
      </p>
      {top6.map((h, i) => (
        <div key={`${h.cusip}-${h.option}-${i}`} className="flex items-center gap-2 text-xs">
          <span className="w-40 shrink-0 truncate text-muted-foreground" title={h.issuer}>
            {h.issuer}
          </span>
          <div className="h-2 flex-1 overflow-hidden rounded-full bg-muted/40">
            <div
              className={barCls}
              style={{ width: `${(h.value / visibleTotal) * 100}%` }}
            />
          </div>
          <span className="w-12 shrink-0 text-right font-mono tabular-nums">
            {((h.value / visibleTotal) * 100).toFixed(1)}%
          </span>
        </div>
      ))}
      <div className="flex items-center gap-2 text-xs">
        <span className="w-40 shrink-0 text-muted-foreground">
          {t("institutions.concentration.other")}
        </span>
        <div className="h-2 flex-1 overflow-hidden rounded-full bg-muted/40">
          <div className={otherCls} style={{ width: `${otherShare * 100}%` }} />
        </div>
        <span className="w-12 shrink-0 text-right font-mono tabular-nums text-muted-foreground">
          {(otherShare * 100).toFixed(1)}%
        </span>
      </div>
      <p className="text-[11px] text-muted-foreground">
        {t("institutions.concentration.footnote")}
      </p>
    </div>
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
          {/* Whole-USD value delta beside the share %; absent until the next
              mainline re-export (old JSON rows predate the key — honest "—").
              Sign may OPPOSE delta_pct on increased/reduced (price drift). */}
          {(() => {
            const dv = c.delta_value ?? null;
            return dv != null ? (
              <span
                className={cn(
                  "font-mono text-xs tabular-nums",
                  DIRECTION_CLASS[c.direction],
                )}
              >
                {dv > 0 ? "+" : ""}
                {fmtUsd(dv)}
              </span>
            ) : null;
          })()}
        </span>
      ))}
    </div>
  );
}
