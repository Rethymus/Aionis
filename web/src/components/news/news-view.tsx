"use client";

import { useMemo } from "react";
import {
  Card,
  CardContent,
} from "@/components/ui/card";
import { LoadMoreFooter, usePaged } from "@/components/stream/stream-kit";
import { useI18n } from "@/i18n/provider";
import { aionis } from "@/data/aionis";

const PAGE_SIZE = 50;

/** GDELT headline stream — metadata + outbound links only. Every title links
 *  out to the publisher's original article (copyright stays there); nothing
 *  is summarized or rewritten. Machine order (GDELT sort=datedesc), not an
 *  editorial ranking; the fixed quoted-phrase query is displayed verbatim.
 *
 *  Aligned-site anatomy: page head with the count line, a live-dot meta row,
 *  then ONE feed card — date-group headers (bg-soft) over single-line
 *  time-stamped rows with a source-colored prefix (brand for English
 *  publishers, amber otherwise — the two prefix tones carry a real signal,
 *  the item's language). */

type Group = { date: string; label: string; rows: typeof aionis.newsFeed.items };

function groupByDate(
  items: typeof aionis.newsFeed.items,
  lang: "zh" | "en",
): Group[] {
  const groups: Group[] = [];
  const byDate = new Map<string, typeof aionis.newsFeed.items>();
  for (const r of items) {
    const d = r.seendate.slice(0, 8); // YYYYMMDD
    if (!byDate.has(d)) byDate.set(d, []);
    byDate.get(d)!.push(r);
  }
  for (const [d, rows] of byDate) {
    const y = +d.slice(0, 4);
    const m = +d.slice(4, 6);
    const day = +d.slice(6, 8);
    const MONTHS_EN = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    const label =
      lang === "zh"
        ? `${m}月${day}日`
        : `${MONTHS_EN[m - 1] ?? m} ${day}, ${y}`;
    groups.push({ date: d, label, rows });
  }
  return groups;
}

export function NewsView() {
  const { t, lang } = useI18n();
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
  const groups = useMemo(() => groupByDate(visible, lang), [visible, lang]);

  if (f.status !== "ok" || rows.length === 0) {
    return (
      <div className="flex flex-col gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-[-0.032em]">
            {t("news.title")}
          </h1>
          <p className="mt-2 text-[13px] text-mute">{t("news.window")}</p>
        </div>
        <Card className="border-amber-500/30 bg-amber-500/5">
          <CardContent className="space-y-1 p-4">
            <p className="text-[13px] font-medium text-amber-700 dark:text-amber-400">
              {t("news.awaiting")}
            </p>
            <p className="text-[11px] text-mute">{f.methodology}</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-[-0.032em]">
          {t("news.title")}
        </h1>
        <p className="mt-2 text-[13px] text-mute">
          {t("news.count_line")
            .replace("{total}", f.total.toLocaleString("en-US"))
            .replace("{sources}", f.n_sources.toLocaleString("en-US"))
            .replace("{days}", String(f.by_day.length))
            .replace("{start}", f.window.start)
            .replace("{end}", f.window.end)}
        </p>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-2">
        <div className="flex flex-wrap gap-2">
          <span className="inline-flex h-8 items-center rounded-md bg-ink px-3 text-[13px] font-medium text-inverse">
            GDELT
          </span>
          <span className="inline-flex h-8 items-center rounded-md border border-line px-3 text-[13px] font-medium text-sub">
            {t("news.chip.dedup")}
          </span>
        </div>
        <div className="ml-auto flex items-center gap-1.5 px-1 text-[11px] text-mute">
          <span className="h-1.5 w-1.5 rounded-full bg-faint" />
          UTC
        </div>
      </div>

      <div className="overflow-hidden rounded-xl border border-line bg-card">
        {groups.map((g) => (
          <div key={g.date}>
            <div className="border-t border-line2 bg-soft px-5 py-1.5 text-[11px] font-semibold text-mute first:border-t-0">
              {g.label}
            </div>
            {g.rows.map((r) => (
              <a
                key={r.url}
                href={r.url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-baseline gap-3 border-t border-line2 px-5 py-[10px] transition-colors hover:bg-soft"
              >
                <span className="flex-none font-mono text-[12px] text-mute">
                  {r.seendate.slice(11, 16)}
                </span>
                <span className="min-w-0 text-[13px] leading-relaxed text-ink">
                  <span
                    className={`font-semibold ${
                      (r.language || "eng") === "eng" ? "text-brand" : "text-amber"
                    }`}
                  >
                    {r.domain || "—"}｜
                  </span>
                  {r.title || r.url}
                </span>
              </a>
            ))}
          </div>
        ))}
        <LoadMoreFooter
          shown={visible.length}
          total={rows.length}
          onLoadMore={loadMore}
          pageSize={PAGE_SIZE}
        />
        {f.total > rows.length && (
          <p className="border-t border-line2 px-5 py-2 text-[11px] text-mute">
            {t("news.limit_note")
              .replace("{total}", f.total.toLocaleString("en-US"))
              .replace("{visible}", rows.length.toLocaleString("en-US"))}
          </p>
        )}
      </div>

      <Card className="py-0">
        <CardContent className="space-y-1 px-5 py-4">
          <p className="text-[13px] font-semibold">{t("news.methodology")}</p>
          <p className="font-mono text-[11px] text-mute">{f.query}</p>
          <p className="text-[11px] leading-relaxed text-mute">{f.methodology}</p>
          <p className="text-[11px] leading-relaxed text-mute">{t("news.stream_note")}</p>
        </CardContent>
      </Card>
    </div>
  );
}
