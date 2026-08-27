"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { fmtDateShort } from "@/lib/format";
import { LoadMoreFooter, usePaged } from "@/components/stream/stream-kit";
import { useI18n } from "@/i18n/provider";
import { aionis } from "@/data/aionis";
import { stockUniverse } from "@/data/aionis/stock-universe";

// /stakes — 举牌 stream (their /stakes: active or passive large-stake
// disclosures). Two existing panels, ZERO new data paths:
//   * stakes13g (7,419 SC 13G + 8,563 SC 13G/A declared, 150 visible) —
//     PASSIVE stakes with parsed ownership percentages;
//   * filingStream filtered to SC 13D(/A) — ACTIVE stakes (intent to
//     influence), link-out metadata only (13D percentages live inside the
//     filing documents; honest empty, never guessed).
// Merged client-side into one date-grouped stream (insider-page anatomy):
// date bg-soft headers over two-line rows — target + pct pill on line 1,
// mono filer · form · ticker meta on line 2.

const PAGE_SIZE = 50;

type StakeRow = {
  key: string;
  filer: string;
  target: string;
  ticker: string;
  date: string;
  form: string;
  doc_url: string;
  pct: number | null;
  pctStatus: string | null;
  passive: boolean;
};

// Link tickers to /stock pages only where a static page exists.
const STOCK_PAGE_TICKERS_SET: ReadonlySet<string> = new Set(
  stockUniverse.stocks.map((s) => s.ticker),
);

export function StakesView() {
  const { t } = useI18n();
  const [kind, setKind] = useState<"all" | "passive" | "active">("all");
  const { visibleCount, loadMore } = usePaged(PAGE_SIZE);

  const g = aionis.stakes13g;
  const fs = aionis.filingStream;

  const rows = useMemo<StakeRow[]>(() => {
    const out: StakeRow[] = [];
    if (g.status === "ok") {
      for (const r of g.filings) {
        out.push({
          key: `g-${r.doc_url}-${r.filer}`,
          filer: r.filer,
          target: r.target,
          ticker: r.ticker || "",
          date: r.date,
          form: r.form,
          doc_url: r.doc_url,
          pct: r.pct_now ?? null,
          pctStatus: r.pct_status ?? null,
          passive: true,
        });
      }
    }
    if (fs.status === "ok") {
      for (const r of fs.filings) {
        if (!/^SC 13D/.test(r.form)) continue;
        // filing_stream rows carry "FILER → TARGET" for stakes forms.
        const arrow = r.who.indexOf(" → ");
        const filer = arrow >= 0 ? r.who.slice(0, arrow) : r.who;
        const target = arrow >= 0 ? r.who.slice(arrow + 3) : "";
        out.push({
          key: `d-${r.doc_url}-${filer}`,
          filer,
          target,
          ticker: r.ticker || "",
          date: r.filed_date,
          form: r.form,
          doc_url: r.doc_url,
          pct: null,
          pctStatus: null,
          passive: false,
        });
      }
    }
    return out.sort((a, b) => (a.date < b.date ? 1 : a.date > b.date ? -1 : 0));
  }, [g.status, g.filings, fs.status, fs.filings]);

  const filtered = useMemo(
    () =>
      kind === "all"
        ? rows
        : rows.filter((r) => (kind === "passive" ? r.passive : !r.passive)),
    [rows, kind],
  );
  const visible = useMemo(
    () => filtered.slice(0, visibleCount),
    [filtered, visibleCount],
  );

  const nPassive = rows.filter((r) => r.passive).length;
  const nActive = rows.length - nPassive;

  const chipBase = "rounded-full border px-3 py-1 text-xs font-medium transition-colors";

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-[-0.032em]">{t("stakes.title")}</h1>
        <p className="mt-2 text-[13px] text-mute">
          {t("stakes.subtitle")}
          {g.status === "ok" && g.window
            ? ` · ${g.total.toLocaleString("en-US")} 13G · ${g.window.start}→${g.window.end}`
            : ""}
        </p>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-2">
        <div className="flex flex-wrap gap-2">
          {(
            [
              ["all", t("stakes.kind.all"), rows.length],
              ["passive", t("stakes.kind.passive"), nPassive],
              ["active", t("stakes.kind.active"), nActive],
            ] as const
          ).map(([k, label, n]) => (
            <button
              key={k}
              type="button"
              onClick={() => setKind(k)}
              aria-pressed={kind === k}
              className={cn(
                chipBase,
                kind === k
                  ? "border-brand bg-brand-tint font-mono font-semibold text-brand"
                  : "border-line bg-card font-mono font-semibold text-sub hover:border-faint hover:text-ink",
              )}
            >
              {label} ({n})
            </button>
          ))}
        </div>
      </div>

      <div className="overflow-hidden rounded-xl border border-line bg-card">
        {visible.map((r, i) => {
          const prev = i > 0 ? visible[i - 1] : null;
          const newDay = !prev || prev.date !== r.date;
          const pctKnown = r.pct !== null && r.pct !== undefined;
          return (
            <div key={r.key}>
              {newDay ? (
                <div className="border-t border-line2 bg-soft px-5 py-1.5 text-[11px] font-semibold text-mute first:border-t-0">
                  {fmtDateShort(r.date)}
                </div>
              ) : null}
              <a
                href={r.doc_url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex flex-col gap-2 border-t border-line2 px-4 py-3 transition-colors hover:bg-soft"
              >
                <div className="flex items-center gap-2.5">
                  <span
                    className={cn(
                      "flex-none rounded-full px-[10px] py-[3px] text-[12px] font-semibold",
                      r.passive ? "bg-soft text-sub" : "bg-brand-tint text-brand",
                    )}
                  >
                    {r.passive ? "13G" : "13D"}
                  </span>
                  <span className="min-w-0 flex-1 truncate text-[13px] font-semibold">
                    {r.target || r.ticker || r.filer}
                  </span>
                  {pctKnown ? (
                    <span className="flex-none font-mono text-[13px] font-semibold text-up tabular-nums">
                      {r.pct}%
                    </span>
                  ) : null}
                </div>
                <span className="flex flex-wrap items-center gap-x-1.5 pl-10 font-mono text-[12px] text-mute tabular-nums">
                  <span className="truncate">{r.filer}</span>·<b className="font-semibold text-ink">{r.form}</b>
                  {r.ticker ? (
                    <>
                      ·
                      {STOCK_PAGE_TICKERS_SET.has(r.ticker) ? (
                        <Link
                          href={`/stock/${r.ticker}`}
                          onClick={(e) => e.stopPropagation()}
                          className="font-semibold text-brand hover:text-brand-hover"
                        >
                          {r.ticker}
                        </Link>
                      ) : (
                        <b className="font-semibold text-ink">{r.ticker}</b>
                      )}
                    </>
                  ) : null}
                </span>
              </a>
            </div>
          );
        })}
        <LoadMoreFooter
          shown={visible.length}
          total={filtered.length}
          onLoadMore={loadMore}
          pageSize={PAGE_SIZE}
        />
      </div>

      <div className="rounded-xl border border-line bg-card px-5 py-4">
        <p className="text-[13px] font-semibold">{t("stakes.methodology.title")}</p>
        <p className="mt-1 text-[11px] leading-relaxed text-mute">
          {t("stakes.methodology.note")}
        </p>
        {g.status === "ok" ? (
          <p className="mt-1 font-mono text-[11px] leading-relaxed text-mute">
            {g.methodology}
          </p>
        ) : null}
      </div>
    </div>
  );
}
