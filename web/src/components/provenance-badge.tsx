"use client";

import { ClockIcon, LockIcon } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { useI18n } from "@/i18n/provider";

// Provenance spine (QVeris evidence-first: every material number has a source
// and observation timestamp). A small, uniform "as of" chip rendered across
// views. Accepts any timestamp field the panel carries (snapshot_ts /
// as_of_date / latest_date / ISO string) and an optional source label.
//
// frozen=true marks panels derived from frozen OOS artifacts: the number does
// NOT advance with the daily refresh — by design (rerunning it would be
// "rerun-to-significance"). Lock (frozen) vs clock (daily) gives the two
// freshness classes an at-a-glance semantic split.
//
// Renders nothing when no timestamp is present — an absent badge is honest
// (we don't fabricate a freshness claim), never a decorative dash.
export function ProvenanceBadge({
  ts,
  source,
  frozen = false,
  className,
}: {
  ts?: string | null;
  source?: string;
  frozen?: boolean;
  className?: string;
}) {
  const { t } = useI18n();
  if (!ts) return null;
  // ISO or "YYYY-MM-DD ..." → date portion only.
  const date = ts.includes("T") ? ts.split("T")[0] : ts.split(" ")[0];
  if (!date) return null;
  const title = frozen
    ? `${t("provenance.frozen")} · ${date}`
    : source
      ? `${t("provenance.asof")} ${date} · ${source}`
      : `${t("provenance.asof")} ${date}`;
  return (
    <Badge
      variant="outline"
      className={cn(
        "gap-1 px-1.5 py-0 text-xs font-normal text-muted-foreground",
        frozen && "text-slate-600 dark:text-slate-300",
        className,
      )}
      title={title}
    >
      {frozen ? <LockIcon className="size-2.5" /> : <ClockIcon className="size-2.5" />}
      {source ? `${source} · ${date}` : date}
    </Badge>
  );
}
