"use client";

import { ClockIcon } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { useI18n } from "@/i18n/provider";

// Provenance spine (QVeris evidence-first: every material number has a source
// and observation timestamp). A small, uniform "as of" chip rendered across
// views. Accepts any timestamp field the panel carries (snapshot_ts /
// as_of_date / latest_date / ISO string) and an optional source label.
//
// Renders nothing when no timestamp is present — an absent badge is honest
// (we don't fabricate a freshness claim), never a decorative dash.
export function ProvenanceBadge({
  ts,
  source,
  className,
}: {
  ts?: string | null;
  source?: string;
  className?: string;
}) {
  const { t } = useI18n();
  if (!ts) return null;
  // ISO or "YYYY-MM-DD ..." → date portion only.
  const date = ts.includes("T") ? ts.split("T")[0] : ts.split(" ")[0];
  if (!date) return null;
  return (
    <Badge
      variant="outline"
      className={cn(
        "gap-1 px-1.5 py-0 text-[10px] font-normal text-muted-foreground",
        className,
      )}
      title={source ? `${t("provenance.asof")} ${date} · ${source}` : `${t("provenance.asof")} ${date}`}
    >
      <ClockIcon className="size-2.5" />
      {source ? `${source} · ${date}` : date}
    </Badge>
  );
}
