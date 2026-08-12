"use client";

import Link from "next/link";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ArrowRightIcon, BrainCircuitIcon, MapIcon } from "lucide-react";
import { useI18n } from "@/i18n/provider";
import { aionis } from "@/data/aionis";
import { cn } from "@/lib/utils";

// Research-at-a-glance — a compact summary on the Overview that surfaces the two
// AI display surfaces (attribution + coverage) without duplicating them. The
// flagship page already shows WHAT (the chain + verdict); this shows WHY-null
// (attribution) and WHAT-WAS-TESTED (coverage depth), each with a deep-dive link.
// Deterministic, no external call, leakage-safe (reads only frozen numbers).

// Compact coverage-depth tally (mirrors coverage-map.tsx FAMILIES, kept in sync
// manually — a single source of truth would be better, but these are small,
// auditable constants and duplicating avoids a cross-module import coupling).
const COVERAGE_TALLY = { tested: 3, exploratory: 2, gaps: 5 } as const;

export function ResearchGlance() {
  const { t } = useI18n();
  const m = aionis.metrics;
  const hasCI = m.ci_lo !== null && m.ci_hi !== null;
  const ciHalf = hasCI ? Math.max(Math.abs(m.ci_lo!), Math.abs(m.ci_hi!)) : null;
  const sesoi = m.sesoi ?? 0.01;
  const powerUnattainable = ciHalf !== null && ciHalf > sesoi;

  return (
    <section className="grid gap-3 md:grid-cols-2">
      {/* WHY-null — attribution digest (deep-dive on /track) */}
      <Link href="/track" className="group">
        <Card className="h-full transition-colors group-hover:border-foreground/20">
          <CardHeader className="gap-1.5">
            <CardTitle className="flex items-center justify-between gap-2 text-sm">
              <span className="flex items-center gap-1.5">
                <BrainCircuitIcon className="size-3.5 text-primary" />
                {t("glance.attribution.title")}
              </span>
              <ArrowRightIcon className="size-3 text-muted-foreground/50" />
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-1.5">
            <p className="text-xs leading-relaxed text-muted-foreground">
              {t("glance.attribution.lead")}
            </p>
            <div className="flex flex-wrap gap-1.5 pt-1">
              <Badge variant="outline" className="px-1.5 py-0 text-[10px] font-normal text-muted-foreground">
                IC {m.combined_ic.toFixed(4)}
              </Badge>
              {hasCI ? (
                <Badge variant="outline" className="px-1.5 py-0 text-[10px] font-normal text-muted-foreground">
                  CI [{m.ci_lo!.toFixed(3)}, {m.ci_hi!.toFixed(3)}]
                </Badge>
              ) : null}
              <Badge
                variant="outline"
                className={cn(
                  "px-1.5 py-0 text-[10px] font-normal",
                  powerUnattainable ? "text-amber-600 dark:text-amber-400" : "text-muted-foreground",
                )}
              >
                {powerUnattainable ? t("glance.attribution.power") : "power OK"}
              </Badge>
            </div>
          </CardContent>
        </Card>
      </Link>

      {/* WHAT-tested — coverage digest (deep-dive on /themes) */}
      <Link href="/themes" className="group">
        <Card className="h-full transition-colors group-hover:border-foreground/20">
          <CardHeader className="gap-1.5">
            <CardTitle className="flex items-center justify-between gap-2 text-sm">
              <span className="flex items-center gap-1.5">
                <MapIcon className="size-3.5 text-primary" />
                {t("glance.coverage.title")}
              </span>
              <ArrowRightIcon className="size-3 text-muted-foreground/50" />
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-1.5">
            <p className="text-xs leading-relaxed text-muted-foreground">
              {t("glance.coverage.lead")}
            </p>
            <div className="flex flex-wrap gap-1.5 pt-1">
              <Badge variant="outline" className="gap-1 px-1.5 py-0 text-[10px] font-normal text-emerald-600 dark:text-emerald-400">
                {t("coverage.label.tested")} {COVERAGE_TALLY.tested}
              </Badge>
              <Badge variant="outline" className="gap-1 px-1.5 py-0 text-[10px] font-normal text-amber-600 dark:text-amber-400">
                {t("coverage.label.exploratory")} {COVERAGE_TALLY.exploratory}
              </Badge>
              <Badge variant="outline" className="gap-1 px-1.5 py-0 text-[10px] font-normal text-muted-foreground">
                {t("coverage.label.gaps")} {COVERAGE_TALLY.gaps}
              </Badge>
            </div>
          </CardContent>
        </Card>
      </Link>
    </section>
  );
}
