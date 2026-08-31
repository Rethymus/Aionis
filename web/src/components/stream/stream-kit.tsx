"use client";

import { useCallback, useState } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useI18n } from "@/i18n/provider";

// Shared stream-panel interaction kit (reference alignment P0-2), extracted
// from the /companies precedent so every stream panel (congress / insiders /
// ipo / events / smart-money) gets the same filter-pills + load-more +
// "shown / total" counter pattern without re-implementing it. Client-side
// state only — the terminal is a static export, filters never hit a server.

export const pillCls = (active: boolean) =>
  cn(
    "rounded-full border px-3 py-1 text-xs font-medium transition-colors",
    active
      ? "border-primary bg-primary text-primary-foreground"
      : "border-border text-muted-foreground hover:bg-muted",
  );

export type PillOption<K extends string> = {
  key: K;
  label: string;
  count?: number;
};

/** Row of enum filter pills with optional honest per-option counts. */
export function FilterPills<K extends string>({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: PillOption<K>[];
  value: K;
  onChange: (k: K) => void;
}) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="text-xs text-muted-foreground">{label}</span>
      {options.map((o) => (
        <button
          key={o.key}
          type="button"
          onClick={() => onChange(o.key)}
          aria-pressed={value === o.key}
          className={pillCls(value === o.key)}
        >
          {o.label}
          {typeof o.count === "number" ? (
            <span
              className={cn(
                "ml-1.5 font-mono text-[11px] tabular-nums",
                value === o.key ? "opacity-80" : "text-muted-foreground",
              )}
            >
              {o.count.toLocaleString("en-US")}
            </span>
          ) : null}
        </button>
      ))}
    </div>
  );
}

/** Load-more footer with the "{shown} / {total}" counter (reference P5). */
export function LoadMoreFooter({
  shown,
  total,
  onLoadMore,
  pageSize,
}: {
  shown: number;
  total: number;
  onLoadMore: () => void;
  pageSize: number;
}) {
  const { t } = useI18n();
  const countLine = t("stream.count")
    .replace("{shown}", shown.toLocaleString("en-US"))
    .replace("{total}", total.toLocaleString("en-US"));
  if (shown >= total) {
    return (
      <div className="border-t p-3 text-center font-mono text-xs tabular-nums text-muted-foreground">
        {countLine}
      </div>
    );
  }
  return (
    <div className="flex items-center justify-center gap-3 border-t p-3">
      <Button variant="outline" size="sm" onClick={onLoadMore}>
        {t("stream.loadmore")} · +{Math.min(pageSize, total - shown)}
      </Button>
      <span className="font-mono text-xs tabular-nums text-muted-foreground">
        {countLine}
      </span>
    </div>
  );
}

/** Filter + pagination state pair: the "load more" window only ever applies
 *  to the CURRENT filtered set — any filter change must reset it (the
 *  /companies discipline, now enforced by the hook instead of each view). */
export function usePaged(pageSize: number) {
  const [visibleCount, setVisibleCount] = useState(pageSize);
  const reset = useCallback(() => setVisibleCount(pageSize), [pageSize]);
  const loadMore = useCallback(
    () => setVisibleCount((v) => v + pageSize),
    [pageSize],
  );
  return { visibleCount, reset, loadMore };
}
