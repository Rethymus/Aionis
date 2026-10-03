"use client";

// FreshnessBadge (round 157): a compact data-freshness indicator in the top
// nav — a colored dot + "Xh ago" computed from the data_health snapshot_ts.
// This is the trust visualization for the anti-leakage selling point: "you
// can see how fresh my data is." The dot is green when the last export is
// < 48h old, amber 48–96h, red > 96h (matching the evening lane's expected
// cadence: nightly on trading days, weekend skip by design).

import { useEffect, useMemo, useState } from "react";
import { aionis } from "@/data/aionis";
import { useI18n } from "@/i18n/provider";

type Freshness = { hours: number | null; level: "fresh" | "aging" | "stale" };

function computeFreshness(snapshotTs: string | undefined): Freshness {
  if (!snapshotTs) return { hours: null, level: "stale" };
  const ts = new Date(snapshotTs).getTime();
  if (Number.isNaN(ts)) return { hours: null, level: "stale" };
  const hours = Math.floor((Date.now() - ts) / 3_600_000);
  if (hours < 48) return { hours, level: "fresh" };
  if (hours < 96) return { hours, level: "aging" };
  return { hours, level: "stale" };
}

const DOT = {
  fresh: "bg-emerald-500",
  aging: "bg-amber-500",
  stale: "bg-rose-500",
} as const;

export function FreshnessBadge() {
  const { t } = useI18n();
  const snap = aionis.dataHealth?.snapshot_ts;
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  const { hours, level } = useMemo(() => computeFreshness(snap), [snap]);

  // Static export: Date.now() differs between build and browser, so the
  // hours are computed client-side only. The SSR HTML carries a placeholder
  // to avoid CLS; the badge renders after hydration (correct for a "live"
  // indicator).
  if (!mounted) {
    return <span className="inline-block w-[52px]" aria-hidden="true" />;
  }

  if (hours === null) {
    return (
      <span className="inline-flex items-center gap-1 text-[11px] font-mono text-muted-foreground">
        <span className={`inline-block size-1.5 rounded-full ${DOT.stale}`} />
        —
      </span>
    );
  }

  const label = hours < 24 ? `${hours}h` : `${Math.floor(hours / 24)}d`;

  return (
    <span
      className="inline-flex cursor-default items-center gap-1 text-[11px] font-mono tabular-nums text-muted-foreground"
      title={`${t("nav.freshness")} · ${snap?.slice(0, 16) ?? "—"}`}
    >
      <span className={`inline-block size-1.5 rounded-full ${DOT[level]}`} />
      {label}
    </span>
  );
}
