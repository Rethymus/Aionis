"use client";

import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { useI18n } from "@/i18n/provider";
import {
  ShieldCheckIcon,
  ArrowRightIcon,
} from "lucide-react";

// Trust ribbon — the anti-leakage discipline surfaced at the top of the hero,
// next to the verdict it underwrites (paradigm-α: the claim and its trust basis
// are co-located, not separated by a scroll). This is the affirmative complement
// to the hero's "non-investment advice" disclaimer: "here is why you can trust
// this RESULT" (PIT data, embargo, H6 determinism, frozen-before-result config),
// not just "don't trade on it". The full guard band stays at the page bottom
// (it spans the whole chain); this ribbon is the at-a-glance trust anchor.
//
// Reads only static i18n + links to /discipline. Deterministic, no data fetch,
// no external call, leakage-safe. The badges are the same vocabulary the guard
// band uses, so the ribbon reads as a preview of the discipline page.

type GuardKey =
  | "trust.pit"
  | "trust.embargo"
  | "trust.h6"
  | "trust.frozen";

const GUARDS: { key: GuardKey; short: string }[] = [
  { key: "trust.pit", short: "PIT" },
  { key: "trust.embargo", short: "embargo" },
  { key: "trust.h6", short: "H6" },
  { key: "trust.frozen", short: "config" },
];

export function TrustRibbon() {
  const { t } = useI18n();
  return (
    <Link
      href="/discipline"
      className="group flex flex-wrap items-center gap-x-3 gap-y-1.5 rounded-lg border border-emerald-500/20 bg-emerald-500/[0.04] px-3 py-2 transition-colors hover:border-emerald-500/40 hover:bg-emerald-500/[0.07]"
      aria-label={t("trust.aria")}
    >
      <span className="flex items-center gap-1.5 text-xs font-medium text-emerald-700 dark:text-emerald-400">
        <ShieldCheckIcon className="size-3.5" />
        {t("trust.label")}
      </span>
      <span className="flex flex-wrap items-center gap-1">
        {GUARDS.map((g) => (
          <Badge
            key={g.key}
            variant="outline"
            className="gap-1 border-emerald-500/25 bg-transparent px-1.5 py-0 text-xs font-normal text-emerald-700/90 dark:text-emerald-400/90"
            title={t(g.key)}
          >
            {g.short}
          </Badge>
        ))}
      </span>
      <span className="ml-auto flex items-center gap-1 text-xs text-muted-foreground transition-colors group-hover:text-foreground">
        {t("trust.detail")}
        <ArrowRightIcon className="size-3 transition-transform group-hover:translate-x-0.5" />
      </span>
    </Link>
  );
}
