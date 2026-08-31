"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  SearchIcon,
  TrendingUpIcon,
  TrendingDownIcon,
  ArrowRightIcon,
  CornerDownLeftIcon,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useI18n } from "@/i18n/provider";
import {
  HOT_STOCKS,
  SEARCH_PAGES,
  SEARCH_VIEWS,
  matchSearchPage,
  searchStocks,
  type StockNavItem,
  type UniverseStock,
} from "@/lib/search-index";

// The home hero search box, upgraded from a fake-input palette trigger to a
// REAL inline search (owner request 2026-08-31): typing searches right here —
// ranked stock matches over the lazily-loaded frozen universe + page/view
// matches — with keyboard navigation (↑↓ move, Enter open, Esc close) and
// IME-safe Enter (composing CJK input never navigates). The top-nav ⌘K
// command palette stays for keyboard-first users; both consume the same
// lib/search-index so results can't drift.

type Row =
  | { kind: "stock"; stock: StockNavItem }
  | { kind: "page"; label: string; href: string };

const PAGE_ROW_CAP = 6;
const VIEW_ROW_CAP = 4;

export function HomeSearch() {
  const { t } = useI18n();
  const router = useRouter();
  const wrapRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  // Lazy-loaded frozen universe (1,421 rows) — null until first focus, so the
  // shared home bundle stays lean (same chunking as the command palette).
  const [universe, setUniverse] = useState<UniverseStock[] | null>(null);

  useEffect(() => {
    if (!open || universe) return;
    let alive = true;
    import("@/data/aionis/stock-universe")
      .then((m) => {
        if (!alive) return;
        setUniverse(
          m.stockUniverse.stocks.map((s) => ({
            ticker: s.ticker,
            name: s.name || "",
            region: s.region,
          })),
        );
      })
      .catch(() => {
        // Chunk load failure must not brick the box: page search keeps
        // working, stock search degrades to the hot list.
        if (alive) setUniverse([]);
      });
    return () => {
      alive = false;
    };
  }, [open, universe]);

  // Close on any pointer press outside the box.
  useEffect(() => {
    if (!open) return;
    const onDown = (e: PointerEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("pointerdown", onDown);
    return () => document.removeEventListener("pointerdown", onDown);
  }, [open]);

  const q = query.trim();
  const stockRows: StockNavItem[] = useMemo(
    () => (q ? searchStocks(universe ?? [], query) : HOT_STOCKS),
    [q, query, universe],
  );
  const pageRows = useMemo(
    () =>
      q
        ? SEARCH_PAGES.filter((p) => matchSearchPage(p, q, t(p.labelKey))).slice(
            0,
            PAGE_ROW_CAP,
          )
        : [],
    [q, t],
  );
  const viewRows = useMemo(
    () =>
      q
        ? SEARCH_VIEWS.filter((v) => matchSearchPage(v, q, t(v.labelKey))).slice(
            0,
            VIEW_ROW_CAP,
          )
        : [],
    [q, t],
  );

  const rows: Row[] = useMemo(() => {
    const stocks = stockRows.map((stock) => ({ kind: "stock" as const, stock }));
    const pages = [
      ...pageRows.map((p) => ({ kind: "page" as const, label: t(p.labelKey), href: p.href })),
      ...viewRows.map((v) => ({ kind: "page" as const, label: t(v.labelKey), href: v.href })),
    ];
    return q ? [...stocks, ...pages] : stocks;
  }, [stockRows, pageRows, viewRows, q, t]);

  const nothingFound = q.length > 0 && rows.length === 0;

  // Group headings rendered at group boundaries: [hot] / [stock matches] /
  // [pages+views]. Everything keyed off the flat list's indices.
  const headingAt = (i: number): string | null => {
    if (i === 0) return q ? t("palette.stocks.search").replace("{n}", universe ? String(universe.length) : "—") : t("palette.stocks");
    if (q && i === stockRows.length && pageRows.length + viewRows.length > 0) {
      return t("command.group.pages");
    }
    return null;
  };

  const go = (row: Row | undefined) => {
    if (!row) return;
    setOpen(false);
    setQuery("");
    inputRef.current?.blur();
    router.push(row.kind === "stock" ? `/stock/${row.stock.ticker}` : row.href);
  };

  const onKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.nativeEvent.isComposing) return; // IME composition (中文输入) — never navigate
    if (e.key === "ArrowDown") {
      e.preventDefault();
      if (rows.length) setActive((a) => (a + 1) % rows.length);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      if (rows.length) setActive((a) => (a - 1 + rows.length) % rows.length);
    } else if (e.key === "Enter") {
      e.preventDefault();
      go(rows[active] ?? rows[0]);
    } else if (e.key === "Escape") {
      setOpen(false);
      inputRef.current?.blur();
    }
  };

  return (
    <div ref={wrapRef} className="relative mx-auto w-full max-w-[560px]">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          go(rows[active] ?? rows[0]);
        }}
        role="search"
      >
        <SearchIcon className="pointer-events-none absolute left-4 top-1/2 size-[17px] -translate-y-1/2 text-faint" />
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setActive(0);
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={onKeyDown}
          placeholder={t("overview.search.placeholder")}
          aria-label={t("overview.search.placeholder")}
          aria-autocomplete="list"
          role="combobox"
          aria-expanded={open && rows.length > 0}
          aria-controls="aionis-home-search-listbox"
          className="h-12 w-full cursor-text rounded-xl border border-line bg-card pl-11 pr-4 text-left text-[14px] text-ink shadow-[0_1px_2px_rgba(0,0,0,0.04),0_8px_24px_-12px_rgba(0,0,0,0.12)] outline-none transition-colors placeholder:text-mute hover:border-faint focus:border-faint"
        />
      </form>
      {open && rows.length > 0 ? (
        <div
          id="aionis-home-search-listbox"
          role="listbox"
          className="absolute left-0 right-0 top-[calc(100%+8px)] z-30 max-h-[min(420px,60vh)] overflow-y-auto rounded-xl border border-line bg-card p-1.5 shadow-[0_1px_2px_rgba(0,0,0,0.06),0_16px_40px_-16px_rgba(0,0,0,0.25)]"
        >
          {rows.map((row, i) => {
            const selected = i === active;
            const heading = headingAt(i);
            const key =
              row.kind === "stock"
                ? `stock-${row.stock.ticker}`
                : `page-${row.href}`;
            return (
              <div key={key}>
                {heading ? (
                  <p className="px-2.5 pb-1 pt-2 text-[11px] font-medium text-mute">
                    {heading}
                  </p>
                ) : null}
                <button
                  type="button"
                  role="option"
                  aria-selected={selected}
                  onMouseDown={(e) => {
                    // mousedown (not click) so blur/pointerdown-outside
                    // ordering can't swallow the selection.
                    e.preventDefault();
                    go(row);
                  }}
                  onMouseEnter={() => setActive(i)}
                  className={cn(
                    "flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-left text-[13px] transition-colors",
                    selected ? "bg-soft" : "",
                  )}
                >
                  {row.kind === "stock" ? (
                    <>
                      {row.stock.short ? (
                        <TrendingDownIcon className="size-4 flex-none text-down" />
                      ) : (
                        <TrendingUpIcon className="size-4 flex-none text-up" />
                      )}
                      <span className="min-w-0 flex-1 truncate text-ink">
                        {row.stock.name
                          ? `${row.stock.name} (${row.stock.ticker})`
                          : row.stock.ticker}
                      </span>
                      {row.stock.short ? (
                        <span className="badge-down shrink-0 rounded border px-1.5 py-0 text-[11px] font-normal">
                          {t("palette.stocks.short")}
                        </span>
                      ) : null}
                      {row.stock.region ? (
                        <span className="shrink-0 rounded border border-line px-1.5 py-0 text-[11px] font-normal text-mute">
                          {row.stock.region.toUpperCase()}
                        </span>
                      ) : null}
                    </>
                  ) : (
                    <>
                      <ArrowRightIcon className="size-4 flex-none text-mute" />
                      <span className="min-w-0 flex-1 truncate text-ink">
                        {row.label}
                      </span>
                      <span className="shrink-0 font-mono text-[11px] text-mute">
                        {row.href}
                      </span>
                    </>
                  )}
                  {selected ? (
                    <CornerDownLeftIcon className="size-3.5 flex-none text-mute" />
                  ) : null}
                </button>
              </div>
            );
          })}
        </div>
      ) : null}
      {open && nothingFound ? (
        <div className="absolute left-0 right-0 top-[calc(100%+8px)] z-30 rounded-xl border border-line bg-card p-6 text-center text-sm text-muted-foreground shadow-[0_16px_40px_-16px_rgba(0,0,0,0.25)]">
          {t("command.empty")}
        </div>
      ) : null}
    </div>
  );
}
