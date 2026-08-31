"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { ExternalLinkIcon, ShieldAlertIcon, TriangleAlertIcon } from "lucide-react";
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
import { AvatarInitials } from "@/components/stream/avatar-initials";
import { useI18n } from "@/i18n/provider";
import { aionis } from "@/data/aionis";
import type { PoliticianTx } from "@/data/aionis";
import { STOCK_PAGE_TICKERS } from "@/components/institutions/manager-book";
import { ProvenanceBadge } from "@/components/provenance-badge";

const PAGE_SIZE = 50;
const TX_PAGE_SIZE = 50;

type PartyFilter = "all" | "R" | "D" | "I";
type TxParty = "all" | "R" | "D" | "unknown";
type TxDirecton = "all" | "buy" | "sell_partial" | "sell_full";
type TxLate = "all" | "late";

/** Party chip, reference-alignment style: US-convention tinted fill (blue for
 *  D, red for R — identity colors, not semantic colors, so the project's
 *  emerald/rose/amber semantics stay untouched). Small square-ish radius,
 *  mono, 11px — matches the measured 10px/600/4px reference. */
function PartyBadge({ party }: { party: string | null }) {
  if (!party) return null;
  const cls =
    party === "D"
      ? "bg-blue-tint text-blue"
      : party === "R"
        ? "bg-red-tint text-red"
        : "bg-soft text-mute";
  return (
    <span
      className={cn(
        "ml-2 inline-block rounded-[4px] px-1.5 py-px font-mono text-[11px] font-semibold leading-4",
        cls,
      )}
    >
      {party}
    </span>
  );
}

/** Direction badge: convention-aware up/down fill (buy = up, sells = down),
 *  partial/full distinguished by label. Same taxonomy as the insiders view. */
function DirectionBadge({ d }: { d: PoliticianTx["direction"] }) {
  const { t } = useI18n();
  const buy = d === "buy";
  return (
    <Badge
      variant="secondary"
      className={cn(
        "shrink-0 font-mono text-[11px] leading-4",
        buy ? "badge-up" : "badge-down",
      )}
    >
      {t(`congress.tx.direction.${d}`)}
    </Badge>
  );
}

/** Statutory amount band — a RANGE, never an exact value (mono badge). */
function AmountBadge({ range }: { range: string }) {
  return (
    <span className="whitespace-nowrap rounded-[4px] bg-muted px-1.5 py-px font-mono text-[11px] leading-4 text-muted-foreground tabular-nums">
      {range}
    </span>
  );
}

/** 交易明细 — transaction-level section (2026 PTR PDFs parsed; the filing
 *  stream above stays the index-level view). Filters: party / direction /
 *  late-only; amount bands as badges; ⚠ marks the 45-day STOCK Act breach. */
function TxSection() {
  const { t } = useI18n();
  const f = aionis.politicianTradesTx;
  const [party, setParty] = useState<TxParty>("all");
  const [dir, setDir] = useState<TxDirecton>("all");
  const [late, setLate] = useState<TxLate>("all");
  const { visibleCount, reset, loadMore } = usePaged(TX_PAGE_SIZE);

  const tx = f.status === "ok" ? f.transactions : [];
  const partyCounts = useMemo(() => {
    const c: Record<string, number> = { R: 0, D: 0, unknown: 0 };
    for (const r of tx) {
      const k = r.party ?? "unknown";
      if (k in c) c[k] += 1;
    }
    return c;
  }, [tx]);
  const dirCounts = useMemo(() => {
    const c: Record<string, number> = { buy: 0, sell_partial: 0, sell_full: 0 };
    for (const r of tx) if (r.direction in c) c[r.direction] += 1;
    return c;
  }, [tx]);
  const nLate = useMemo(
    () => tx.filter((r) => r.days_late !== null && r.days_late > 45).length,
    [tx],
  );

  const filtered = useMemo(() => {
    return tx.filter(
      (r) =>
        (party === "all" || (r.party ?? "unknown") === party) &&
        (dir === "all" || r.direction === dir) &&
        (late !== "late" || (r.days_late !== null && r.days_late > 45)),
    );
  }, [tx, party, dir, late]);
  const visible = filtered.slice(0, visibleCount);

  const apply = <K,>(setter: (k: K) => void) => (k: K) => {
    setter(k);
    reset();
  };

  if (f.status !== "ok" || tx.length === 0) return null;

  return (
    <Card className="min-w-0">
      <CardHeader className="pb-3">
        <CardTitle className="flex flex-wrap items-center gap-1">
          {t("congress.tx.title")}{" "}
          <span className="font-mono text-sm font-normal text-muted-foreground tabular-nums">
            {f.total.toLocaleString("en-US")} · {f.n_members} · {f.year}
          </span>
          {/* The page-level anchor (guard band) carries the v1 index stream's
              date; this card's rows come from the v2 transaction panel — label
              it with its OWN as_of so the two versions are never conflated. */}
          <ProvenanceBadge ts={f.as_of} />
        </CardTitle>
        <CardDescription>{t("congress.tx.note")}</CardDescription>
        <div className="space-y-1 pt-1">
          <FilterPills<TxParty>
            label={t("congress.party.label")}
            value={party}
            onChange={apply(setParty)}
            options={[
              { key: "all", label: t("congress.party.all"), count: tx.length },
              { key: "R", label: t("congress.party.R"), count: partyCounts.R },
              { key: "D", label: t("congress.party.D"), count: partyCounts.D },
              { key: "unknown", label: t("congress.tx.party.unknown"), count: partyCounts.unknown },
            ]}
          />
          <div className="flex flex-wrap items-center gap-2">
            <FilterPills<TxDirecton>
              label={t("congress.tx.direction.label")}
              value={dir}
              onChange={apply(setDir)}
              options={[
                { key: "all", label: t("congress.tx.direction.all"), count: tx.length },
                { key: "buy", label: t("congress.tx.direction.buy"), count: dirCounts.buy },
                { key: "sell_partial", label: t("congress.tx.direction.sell_partial"), count: dirCounts.sell_partial },
                { key: "sell_full", label: t("congress.tx.direction.sell_full"), count: dirCounts.sell_full },
              ]}
            />
            <FilterPills<TxLate>
              label={t("congress.tx.late.label")}
              value={late}
              onChange={apply(setLate)}
              options={[
                { key: "all", label: t("congress.tx.late.all") },
                { key: "late", label: "⚠ >45d", count: nLate },
              ]}
            />
          </div>
        </div>
      </CardHeader>
      <CardContent className="p-0">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>{t("congress.member")}</TableHead>
              <TableHead>{t("congress.tx.asset")}</TableHead>
              <TableHead>{t("congress.tx.direction.label")}</TableHead>
              <TableHead>{t("congress.tx.amount")}</TableHead>
              <TableHead>{t("congress.tx.tx_date")}</TableHead>
              <TableHead className="text-right">{t("congress.tx.days_late")}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {visible.map((r) => (
              <TableRow key={`${r.doc_url}-${r.transaction_date}-${r.asset}-${r.direction}`}>
                <TableCell>
                  <a
                    href={r.doc_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="font-semibold text-ink hover:text-brand"
                    title={r.doc_url}
                  >
                    {r.member}
                  </a>
                  <PartyBadge party={r.party} />
                </TableCell>
                <TableCell className="max-w-[280px]">
                  <div className="flex items-center gap-1.5">
                    {r.ticker && STOCK_PAGE_TICKERS.has(r.ticker) ? (
                      <Link
                        href={`/stock/${r.ticker}`}
                        className="shrink-0 font-mono text-xs font-semibold text-ink hover:text-brand"
                      >
                        {r.ticker}
                      </Link>
                    ) : null}
                    <span className="truncate text-muted-foreground" title={r.asset}>
                      {r.asset}
                    </span>
                  </div>
                </TableCell>
                <TableCell>
                  <DirectionBadge d={r.direction} />
                </TableCell>
                <TableCell>
                  <AmountBadge range={r.amount_range} />
                </TableCell>
                <TableCell className="whitespace-nowrap tabular-nums text-muted-foreground">
                  {fmtDateShort(r.transaction_date)}
                </TableCell>
                <TableCell className="whitespace-nowrap text-right font-mono text-xs tabular-nums">
                  {(r.days_late ?? 0) > 45 ? (
                    <span
                      className="inline-flex items-center gap-0.5 font-semibold text-amber-600 dark:text-amber-400"
                      title={t("congress.tx.late.hint")}
                    >
                      <TriangleAlertIcon className="size-3" />
                      {r.days_late}d
                    </span>
                  ) : (
                    <span className="text-muted-foreground">{r.days_late}d</span>
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
          pageSize={TX_PAGE_SIZE}
        />
        <div className="border-t px-4 py-2 font-mono text-[11px] leading-relaxed text-muted-foreground/80">
          {t("congress.tx.parse_note")
            .replace("{parsed}", f.parse.rows_parsed.toLocaleString("en-US"))
            .replace("{excluded}", f.parse.rows_exchanged.toLocaleString("en-US"))
            .replace("{failed}", f.parse.parse_failures.toLocaleString("en-US"))
            .replace("{notext}", f.parse.no_text_pdfs.toLocaleString("en-US"))
            .replace("{filings}", f.parse.filings_processed.toLocaleString("en-US"))}
        </div>
      </CardContent>
    </Card>
  );
}

/** 政党对立指数 + 两党跟单组合 — derived panel over the transaction set
 *  (zero new fetches): monthly D-vs-R net-direction opposition share and the
 *  trailing-90d top net-buy books per party. Count-weighted SIGNAL lists
 *  only — no prices, no returns, no performance claim (display lane). */
function PartyIndexSection() {
  const { t } = useI18n();
  const f = aionis.partyIndex;
  if (f.status !== "ok" || f.months.length === 0) return null;

  const months = f.months.slice(-12).reverse();
  const pct = (n: number, d: number) => (d > 0 ? `${Math.round((n / d) * 100)}%` : "—");

  const netChip = (party: "D" | "R", net: number) => (
    <span
      className={cn(
        "font-mono text-[11px] font-semibold tabular-nums",
        party === "D" ? "text-blue" : "text-red",
      )}
    >
      {party}
      {net > 0 ? " +" : " "}
      {net}
    </span>
  );

  const tickerRow = (
    r: { ticker: string; d_net: number; r_net: number },
    i: number,
  ) => (
    <span
      key={`${r.ticker}-${i}`}
      className="inline-flex items-center gap-1.5 rounded-[4px] bg-muted/60 px-2 py-1"
    >
      {/* Same static-export guard as HotTickerStrip: link only where a
          /stock/[ticker] page exists, else keep the ticker as plain text. */}
      {STOCK_PAGE_TICKERS.has(r.ticker) ? (
        <Link
          href={`/stock/${r.ticker}`}
          className="font-mono text-xs font-semibold text-ink hover:text-brand"
        >
          {r.ticker}
        </Link>
      ) : (
        <span className="font-mono text-xs font-semibold">{r.ticker}</span>
      )}
      {netChip("D", r.d_net)}
      {netChip("R", r.r_net)}
    </span>
  );

  return (
    <div className="grid items-start gap-6 lg:grid-cols-2">
      <Card className="min-w-0">
        <CardHeader className="pb-3">
          <CardTitle>{t("congress.pi.title")}</CardTitle>
          <CardDescription>{t("congress.pi.note")}</CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t("congress.pi.month")}</TableHead>
                <TableHead className="text-right">
                  {t("congress.pi.d_buy_share")}
                </TableHead>
                <TableHead className="text-right">
                  {t("congress.pi.r_buy_share")}
                </TableHead>
                <TableHead className="text-right">
                  {t("congress.pi.opposition")}
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {months.map((m) => (
                <TableRow key={m.month}>
                  <TableCell className="font-mono text-xs tabular-nums text-muted-foreground">
                    {m.month}
                  </TableCell>
                  <TableCell className="text-right font-mono text-xs tabular-nums">
                    {pct(m.d_buy, m.d_tx)}
                  </TableCell>
                  <TableCell className="text-right font-mono text-xs tabular-nums">
                    {pct(m.r_buy, m.r_tx)}
                  </TableCell>
                  <TableCell className="text-right">
                    {m.opposition === null ? (
                      <span className="font-mono text-xs text-muted-foreground">—</span>
                    ) : (
                      <span className="inline-flex items-center justify-end gap-1.5">
                        <span className="h-1.5 w-10 overflow-hidden rounded-full bg-muted">
                          <span
                            className="block h-full rounded-full bg-primary/50"
                            style={{ width: `${Math.round(m.opposition * 100)}%` }}
                          />
                        </span>
                        <span className="font-mono text-xs font-semibold tabular-nums">
                          {m.opposition.toFixed(2)}
                        </span>
                        <span className="font-mono text-[11px] text-muted-foreground tabular-nums">
                          ({m.n_opposed}/{m.n_directional})
                        </span>
                      </span>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          {f.latest.opposed.length > 0 || f.latest.consensus.length > 0 ? (
            <div className="space-y-2 border-t px-4 py-3">
              <p className="text-xs text-muted-foreground">
                {t("congress.pi.opposed")} · {f.latest.month}
              </p>
              <div className="flex flex-wrap gap-1.5">
                {f.latest.opposed.length > 0 ? (
                  f.latest.opposed.map(tickerRow)
                ) : (
                  <span className="text-xs text-muted-foreground">
                    {t("congress.pi.empty")}
                  </span>
                )}
              </div>
              {f.latest.consensus.length > 0 ? (
                <>
                  <p className="pt-1 text-xs text-muted-foreground">
                    {t("congress.pi.consensus")}
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {f.latest.consensus.map(tickerRow)}
                  </div>
                </>
              ) : null}
            </div>
          ) : null}
        </CardContent>
      </Card>

      <Card className="min-w-0">
        <CardHeader className="pb-3">
          <CardTitle>{t("congress.pi.portfolio_title")}</CardTitle>
          <CardDescription>
            {t("congress.pi.portfolio_note").replace("{days}", String(f.window_days))}
          </CardDescription>
        </CardHeader>
        <CardContent className="grid grid-cols-1 gap-0 p-0 sm:grid-cols-2">
          {(["D", "R"] as const).map((p) => {
            const book = f.portfolios[p];
            return (
              <div key={p} className="min-w-0 border-t sm:border-l">
                <div className="flex items-center gap-1.5 px-4 py-2.5">
                  <PartyBadge party={p} />
                  <span className="ml-auto font-mono text-[11px] text-muted-foreground tabular-nums">
                    {t("congress.pi.n_tx")} {book.n_tx} · {t("congress.pi.n_members")}{" "}
                    {book.n_members}
                  </span>
                </div>
                <div className="divide-y border-t">
                  {book.holdings.map((h, i) => (
                    <div
                      key={h.ticker}
                      className="flex items-center gap-2 px-4 py-1.5"
                    >
                      <span className="w-4 shrink-0 font-mono text-[11px] text-muted-foreground tabular-nums">
                        {i + 1}
                      </span>
                      <div className="min-w-0 flex-1">
                        {STOCK_PAGE_TICKERS.has(h.ticker) ? (
                          <Link
                            href={`/stock/${h.ticker}`}
                            className="font-mono text-xs font-semibold text-ink hover:text-brand"
                          >
                            {h.ticker}
                          </Link>
                        ) : (
                          <span className="font-mono text-xs font-semibold">{h.ticker}</span>
                        )}
                        <p
                          className="truncate text-[11px] text-muted-foreground"
                          title={h.asset}
                        >
                          {h.asset || "—"}
                        </p>
                      </div>
                      <div className="shrink-0 text-right">
                        <Badge
                          variant="secondary"
                          className={cn(
                            "font-mono text-[11px] leading-4",
                            h.net_buy > 0 ? "badge-up" : "badge-down",
                          )}
                        >
                          +{h.net_buy}
                        </Badge>
                        <p className="mt-0.5 font-mono text-[11px] text-muted-foreground tabular-nums">
                          {h.n_buy}/{h.n_sell} · ×{h.n_members}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </CardContent>
      </Card>
    </div>
  );
}


/** 热门标的芯片行 — deployed-terminal alignment: the congress page carries
 *  a top-tickers chip strip aggregated CLIENT-SIDE from the transaction
 *  panel (zero new exports). Tickers link to /stock pages only where a
 *  static page exists; counts are honest transaction counts. */
function HotTickerStrip() {
  const { t } = useI18n();
  const f = aionis.politicianTradesTx;
  const rows = f.status === "ok" ? f.transactions : [];
  const top = useMemo(() => {
    const counts = new Map<string, number>();
    for (const r of rows) {
      if (r.ticker) counts.set(r.ticker, (counts.get(r.ticker) ?? 0) + 1);
    }
    return [...counts.entries()]
      .sort((a, b) => b[1] - a[1] || (a[0] < b[0] ? -1 : 1))
      .slice(0, 10);
  }, [rows]);
  if (top.length === 0) return null;
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      <span className="text-xs text-muted-foreground">{t("congress.hot_tickers")}</span>
      {top.map(([tk, n]) =>
        STOCK_PAGE_TICKERS.has(tk) ? (
          <Link
            key={tk}
            href={`/stock/${tk}`}
            className="rounded-[4px] bg-soft px-2 py-0.5 font-mono text-xs font-semibold text-ink hover:text-brand"
          >
            {tk}
            <span className="ml-1 font-normal text-muted-foreground tabular-nums">{n}</span>
          </Link>
        ) : (
          <span
            key={tk}
            className="rounded-[4px] bg-muted/60 px-2 py-0.5 font-mono text-xs font-semibold"
          >
            {tk}
            <span className="ml-1 font-normal text-muted-foreground tabular-nums">{n}</span>
          </span>
        ),
      )}
    </div>
  );
}

export function CongressView() {
  const { t } = useI18n();
  const f = aionis.politicianTrades;
  const [party, setParty] = useState<PartyFilter>("all");
  const { visibleCount, reset, loadMore } = usePaged(PAGE_SIZE);

  const filings = f.status === "ok" ? f.house.filings : [];
  const partyCounts = useMemo(() => {
    const c: Record<string, number> = { R: 0, D: 0, I: 0 };
    for (const p of filings) {
      if (p.party && p.party in c) c[p.party] += 1;
    }
    return c;
  }, [filings]);

  const filtered = useMemo(
    () => (party === "all" ? filings : filings.filter((p) => p.party === party)),
    [filings, party],
  );
  const visible = filtered.slice(0, visibleCount);

  const applyParty = (k: PartyFilter) => {
    setParty(k);
    reset();
  };

  if (f.status !== "ok" || filings.length === 0) {
    return (
      <div className="flex flex-col gap-4">
        <header>
          <h1 className="text-2xl font-semibold tracking-[-0.032em]">
            {t("congress.title")}
          </h1>
          <p className="mt-2 text-[13px] text-mute">{t("congress.window")}</p>
        </header>
        <Card className="border-amber-500/30 bg-amber-500/5">
          <CardContent className="space-y-1 p-4">
            <p className="text-sm font-medium text-amber-700 dark:text-amber-400">
              {t("congress.awaiting")}
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
          stream section) — sr-only h1 keeps heading navigation usable. */}
      <h1 className="sr-only">{t("nav.congress")}</h1>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>{t("congress.total")}</CardDescription>
            <CardTitle className="text-2xl tabular-nums">{f.house.total}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>{t("congress.members")}</CardDescription>
            <CardTitle className="text-2xl tabular-nums">{f.house.members}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>{t("congress.window_label")}</CardDescription>
            <CardTitle className="text-sm font-medium tabular-nums">
              {f.window_years.join(" · ")}
            </CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>{t("congress.by_year")}</CardDescription>
            <CardTitle className="text-sm font-medium tabular-nums">
              {Object.entries(f.house.by_year)
                .map(([y, n]) => `${y}: ${n}`)
                .join(" / ")}
            </CardTitle>
          </CardHeader>
        </Card>
      </div>

      <HotTickerStrip />

      {/* 政党对立指数 + 两党跟单组合 (derived, zero new data): the analytical
          layer ABOVE the raw streams — index first, then filings/rows. */}
      <PartyIndexSection />

      <div className="grid items-start gap-6 lg:grid-cols-[1fr_320px]">
        <Card className="min-w-0">
          <CardHeader className="pb-3">
            <CardTitle>{t("congress.stream_title")}</CardTitle>
            <CardDescription>{t("congress.stream_note")}</CardDescription>
            <div className="pt-1">
              <FilterPills<PartyFilter>
                label={t("congress.party.label")}
                value={party}
                onChange={applyParty}
                options={[
                  { key: "all", label: t("congress.party.all"), count: filings.length },
                  { key: "R", label: t("congress.party.R"), count: partyCounts.R },
                  { key: "D", label: t("congress.party.D"), count: partyCounts.D },
                  { key: "I", label: t("congress.party.I"), count: partyCounts.I },
                ]}
              />
            </div>
          </CardHeader>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t("congress.member")}</TableHead>
                  <TableHead>{t("congress.office")}</TableHead>
                  <TableHead>{t("congress.type")}</TableHead>
                  <TableHead>{t("congress.date")}</TableHead>
                  <TableHead className="text-right">{t("congress.source")}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {visible.map((p) => (
                  <TableRow key={p.doc_url}>
                    <TableCell>
                      <a
                        href={p.doc_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="font-semibold text-ink hover:text-brand"
                      >
                        {p.member}
                      </a>
                      <PartyBadge party={p.party} />
                    </TableCell>
                    <TableCell className="font-mono text-xs text-muted-foreground">
                      {p.office}
                    </TableCell>
                    <TableCell>
                      <Badge variant="secondary">{p.filing_type}</Badge>
                    </TableCell>
                    <TableCell
                      className="whitespace-nowrap tabular-nums text-muted-foreground"
                      title={p.filing_date ?? undefined}
                    >
                      {fmtDateShort(p.filing_date)}
                    </TableCell>
                    <TableCell className="text-right">
                      <a
                        href={p.doc_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-ink hover:text-brand"
                      >
                        PDF
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
              pageSize={PAGE_SIZE}
            />
          </CardContent>
        </Card>

        {/* "Most active filers" sidebar (reference-style person list): avatar
            initials + member + district + filing count. top_members carries NO
            party field (member/office/count only) — party chips stay on the
            stream rows where the join is per-filing, never fabricated here. */}
        <Card className="overflow-hidden py-0">
          <CardHeader className="border-b">
            <CardTitle className="text-base">{t("congress.top_filers")}</CardTitle>
            <CardDescription>{t("congress.top_filers_note")}</CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            <div className="divide-y">
              {f.house.top_members.map((m) => (
                <div
                  key={`${m.member}-${m.office}`}
                  className="flex items-center gap-2.5 px-4 py-2"
                >
                  <AvatarInitials name={m.member} />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium" title={m.member}>
                      {m.member}
                    </p>
                    <p className="font-mono text-[11px] text-muted-foreground">
                      {m.office}
                    </p>
                  </div>
                  <span className="ml-auto shrink-0 font-mono text-xs tabular-nums text-muted-foreground">
                    ×{m.count}
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Transaction detail (D4 granularity): per-row PTR PDF parse of the
          2026 filings. Sits BELOW the filing stream — the index view above
          keeps its own contract untouched. */}
      <TxSection />

      <Card className="border-amber-500/30 bg-amber-500/5">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <ShieldAlertIcon className="size-4 text-amber-600 dark:text-amber-400" />
            {t("congress.senate_blocked")}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-xs leading-relaxed text-muted-foreground">
            {f.senate.note}
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle>{t("congress.methodology")}</CardTitle>
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
