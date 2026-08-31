"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import {
  ArrowDownIcon,
  ArrowUpIcon,
  MinusIcon,
  SearchIcon,
} from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
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
import { stockUniverse, type StockRow } from "@/data/aionis/stock-universe";
import { companiesDir } from "@/data/aionis/companies-dir";
import { ProvenanceBadge } from "@/components/provenance-badge";

// Company directory over the FROZEN universe (reference-style A-Z index):
// region + initial + substring search, all client-side over the same frozen
// per-stock readouts the /stock/[ticker] pages render — zero new data paths,
// zero network. The initial rail is honest about the data's shape instead of
// fabricating pinyin initials: US tickers index by their first letter (A-Z);
// CN codes start with a digit after the exchange prefix (6 = SH main board,
// 0 = SZ main board, 3 = ChiNext) and group under the "0-9" chip.

const PAGE_SIZE = 50;
const LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ".split("");

type RegionFilter = "all" | "us" | "cn";

/** Index char for the A-Z rail: first char of the ticker code (exchange
 * prefix stripped for CN), uppercased; digits collapse into "0-9". */
function initialOfTicker(ticker: string): string {
  const code = ticker.includes(".")
    ? (ticker.split(".").pop() ?? ticker)
    : ticker;
  const c = code.charAt(0).toUpperCase();
  return c >= "A" && c <= "Z" ? c : "0-9";
}

/** Same visual contract as picks' Change: up arrow + up color when > 0. */
function RankChange({ change }: { change: number | null }) {
  if (change === null || change === 0) {
    return <MinusIcon className="size-3 text-muted-foreground/50" aria-hidden />;
  }
  const up = change > 0;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-0.5 text-[11px] font-medium tabular-nums",
        up ? "text-up" : "text-down",
      )}
    >
      {up ? (
        <ArrowUpIcon className="size-3" aria-hidden />
      ) : (
        <ArrowDownIcon className="size-3" aria-hidden />
      )}
      {Math.abs(change)}
    </span>
  );
}


const pillCls = (active: boolean) =>
  cn(
    "rounded-full border px-3 py-1 text-xs font-medium transition-colors",
    active
      ? "border-primary bg-primary text-primary-foreground"
      : "border-border text-muted-foreground hover:bg-muted",
  );

export function CompaniesView() {
  const { t } = useI18n();
  const [region, setRegion] = useState<RegionFilter>("all");
  const [initial, setInitial] = useState<string>("all");
  const [query, setQuery] = useState("");
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE);

  // Any filter change resets the window — the "load more" cursor only ever
  // applies to the current result set.
  const applyRegion = (r: RegionFilter) => {
    setRegion(r);
    setVisibleCount(PAGE_SIZE);
  };
  const applyInitial = (i: string) => {
    setInitial(i);
    setVisibleCount(PAGE_SIZE);
  };
  const applyQuery = (q: string) => {
    setQuery(q);
    setVisibleCount(PAGE_SIZE);
  };

  // Content completeness: the directory spans the FULL named US snapshot
  // (~10.4k, companies_dir) plus the CN universe rows; frozen-universe
  // readouts (score/rank/bar) exist only for universe members — everyone
  // else renders as a plain directory card (honest caliber: the snapshot is
  // current, not point-in-time; scores are the frozen OOS readout).
  const dirRows = useMemo(() => {
    const byTicker = new Map(stockUniverse.stocks.map((s) => [s.ticker, s]));
    type DirRow = {
      ticker: string;
      name: string;
      region: "us" | "cn";
      sector: string;
      stock: StockRow | null;
    };
    const rows: DirRow[] = companiesDir.companies.map((c) => {
      const stock = byTicker.get(c.ticker) ?? null;
      return {
        ticker: c.ticker,
        name: c.name,
        region: "us" as const,
        sector: stock?.sector ?? "",
        stock,
      };
    });
    for (const s of stockUniverse.stocks) {
      if (s.region === "cn") {
        rows.push({ ticker: s.ticker, name: s.name, region: "cn", sector: s.sector, stock: s });
      }
    }
    return rows;
  }, []);

  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return dirRows
      .filter((s) => {
        if (region !== "all" && s.region !== region) return false;
        if (initial !== "all" && initialOfTicker(s.ticker) !== initial) return false;
        if (needle) {
          const hit =
            s.ticker.toLowerCase().includes(needle) ||
            s.name.toLowerCase().includes(needle);
          if (!hit) return false;
        }
        return true;
      })
      // Plain ASCII compare — locale-independent, so the prerendered HTML and
      // the client render agree (no hydration drift on Intl collation).
      // Frozen-universe members (scored cards) sort FIRST — the directory
      // opens on the readout-bearing rows; plain snapshot entries follow.
      .sort((a, b) => {
        const au = a.stock ? 0 : 1;
        const bu = b.stock ? 0 : 1;
        if (au !== bu) return au - bu;
        return a.ticker < b.ticker ? -1 : a.ticker > b.ticker ? 1 : 0;
      });
  }, [region, initial, query]);

  const visible = filtered.slice(0, visibleCount);
  const countLine = t("companies.count")
    .replace("{shown}", visible.length.toLocaleString())
    .replace("{total}", filtered.length.toLocaleString());

  const regionPills: { key: RegionFilter; label: string }[] = [
    { key: "all", label: t("companies.region.all") },
    { key: "us", label: t("companies.region.us") },
    { key: "cn", label: t("companies.region.cn") },
  ];

  return (
    <div className="space-y-4">
      <p className="text-xs font-medium text-primary">{t("companies.role")}</p>
      <header>
        <h1 className="text-2xl font-semibold tracking-[-0.032em]">
          {t("companies.title")}
        </h1>
        <p className="mt-2 text-[13px] text-mute">
          {t("companies.dir.count").replace("{n}", dirRows.length.toLocaleString())}
          {" · "}
          {t("companies.dir.caliber")}
        </p>
      </header>

      {/* Filter toolbar: region + initial rail + search, all client-side. */}
      <Card className="py-0">
        <CardContent className="space-y-3 p-4">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs text-muted-foreground">
              {t("companies.filter.region")}
            </span>
            {regionPills.map((p) => (
              <button
                key={p.key}
                type="button"
                onClick={() => applyRegion(p.key)}
                aria-pressed={region === p.key}
                className={pillCls(region === p.key)}
              >
                {p.label}
              </button>
            ))}
            <span className="ml-auto font-mono text-xs tabular-nums text-muted-foreground">
              {countLine}
            </span>
          </div>
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="mr-0.5 text-xs text-muted-foreground">
              {t("companies.filter.initial")}
            </span>
            <button
              type="button"
              onClick={() => applyInitial("all")}
              aria-pressed={initial === "all"}
              className={pillCls(initial === "all")}
            >
              {t("companies.initial.all")}
            </button>
            <button
              type="button"
              onClick={() => applyInitial("0-9")}
              aria-pressed={initial === "0-9"}
              className={pillCls(initial === "0-9")}
            >
              {t("companies.initial.digits")}
            </button>
            {LETTERS.map((L) => (
              <button
                key={L}
                type="button"
                onClick={() => applyInitial(L)}
                aria-pressed={initial === L}
                aria-label={L}
                className={cn(
                  "size-7 rounded-md border text-center font-mono text-xs font-medium leading-7 transition-colors",
                  initial === L
                    ? "border-primary bg-primary text-primary-foreground"
                    : "border-border text-muted-foreground hover:bg-muted",
                )}
              >
                {L}
              </button>
            ))}
          </div>
          <div className="relative">
            <SearchIcon className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            <input
              value={query}
              onChange={(e) => applyQuery(e.target.value)}
              placeholder={t("companies.search.placeholder")}
              aria-label={t("companies.search.label")}
              className="h-9 w-full rounded-md border bg-transparent pl-9 pr-3 text-sm outline-none placeholder:text-muted-foreground focus-visible:ring-2 focus-visible:ring-ring"
            />
          </div>
          <p className="text-xs text-muted-foreground">
            {t("companies.initial.hint")}
          </p>
        </CardContent>
      </Card>

      {/* Directory table. Honest empty state when the filters match nothing. */}
      <Card className="overflow-hidden py-0">
        <CardHeader className="border-b">
          <CardTitle className="flex flex-wrap items-center gap-2 text-base">
            {t("companies.title")}
            <span className="text-sm font-normal text-muted-foreground">
              {dirRows.length.toLocaleString()}
            </span>
            <span className="ml-auto flex flex-wrap items-center gap-2">
              <ProvenanceBadge
                ts={stockUniverse.as_of.us}
                source="US"
                frozen
              />
              <ProvenanceBadge
                ts={stockUniverse.as_of.cn}
                source="CN"
                frozen
              />
            </span>
          </CardTitle>
          <CardDescription className="font-mono text-xs">
            {countLine}
          </CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          {filtered.length === 0 ? (
            <p className="p-6 text-center text-sm italic text-muted-foreground">
              {t("companies.empty")}
            </p>
          ) : (
            <>
              {/* Aligned-site directory cards: 15px name + mono meta over a
                  divider and a percentile bar (5px, green-fill). */}
              <div className="grid gap-3 p-4 md:grid-cols-2 xl:grid-cols-3">
                {visible.map((s) => {
                  const inner = (
                    <>
                      <div className="flex items-center gap-3">
                        <div className="min-w-0 flex-1">
                          <span className="block truncate text-[15px] font-semibold">
                            {s.name || s.ticker}
                          </span>
                          <span className="block truncate font-mono text-xs text-mute">
                            {s.ticker} · {s.region.toUpperCase()} · {s.sector || "—"}
                          </span>
                        </div>
                        {s.stock ? (
                          <span
                            className={`flex-none font-mono text-[13px] font-semibold tabular-nums ${
                              s.stock.score >= 0 ? "text-up" : "text-down"
                            }`}
                          >
                            {s.stock.score > 0 ? "+" : ""}{s.stock.score.toFixed(2)}
                          </span>
                        ) : null}
                      </div>
                      {s.stock ? (
                        <div className="mt-3 border-t border-line2 pt-3 text-xs text-mute">
                          <div className="flex items-baseline justify-between gap-2">
                            <span>{t("companies.col.rank")}</span>
                            <span className="font-mono tabular-nums">
                              {s.stock.rank} / {s.stock.n_region}
                            </span>
                          </div>
                          <div className="mt-1.5 h-[5px] overflow-hidden rounded bg-line2">
                            <div
                              className="h-full rounded bg-green-fill"
                              style={{ width: `${(s.stock.rank / Math.max(s.stock.n_region, 1)) * 100}%` }}
                            />
                          </div>
                        </div>
                      ) : (
                        <div className="mt-3 border-t border-line2 pt-3 text-xs text-mute">
                          <div className="flex items-baseline justify-between gap-2">
                            <span>{t("companies.col.rank")}</span>
                            <span className="font-mono">{t("companies.outside_universe")}</span>
                          </div>
                        </div>
                      )}
                    </>
                  );
                  const cardCls =
                    "block rounded-xl border border-line bg-card px-5 py-4 transition-colors hover:border-faint";
                  return s.stock ? (
                    <Link key={s.ticker} href={`/stock/${s.ticker}`} className={cardCls}>
                      {inner}
                    </Link>
                  ) : (
                    <div key={s.ticker} className={cardCls}>
                      {inner}
                    </div>
                  );
                })}
              </div>
              {visible.length < filtered.length ? (
                <div className="flex items-center justify-center gap-3 border-t p-3">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setVisibleCount((v) => v + PAGE_SIZE)}
                  >
                    {t("companies.loadmore")} · +{Math.min(
                      PAGE_SIZE,
                      filtered.length - visible.length,
                    )}
                  </Button>
                  <span className="font-mono text-xs tabular-nums text-muted-foreground">
                    {countLine}
                  </span>
                </div>
              ) : null}
            </>
          )}
        </CardContent>
      </Card>

      {/* Methodology: this is a directory of the FROZEN universe, not the
          whole market — the disclosure is part of the page, not a footnote. */}
      <Card className="border-muted">
        <CardHeader>
          <CardTitle className="text-sm">
            {t("companies.methodology.title")}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <p className="text-xs leading-relaxed text-muted-foreground">
            {t("companies.methodology.note").replace(
              "{n}",
              stockUniverse.n_stocks.toLocaleString(),
            )}
          </p>
          <p className="font-mono text-xs leading-relaxed text-muted-foreground">
            {stockUniverse.methodology}
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
