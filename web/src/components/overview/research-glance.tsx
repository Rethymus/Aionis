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

// Compact coverage-depth tally. These are FAMILY-DEPTH counts (how many of the
// 5 factor families have a frozen confirmatory result vs are exploratory), NOT
// item counts — see coverage-map.tsx for the full tested/exploratory/gap item
// lists. Kept here as a small auditable constant mirroring FAMILIES.depth.
// If you add/reclassify a family in coverage-map.tsx, update this too.
const COVERAGE_TALLY = { testedFamilies: 3, exploratoryFamilies: 2 } as const;

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
              <Badge
                variant="outline"
                className="px-1.5 py-0 text-[10px] font-normal text-muted-foreground"
                title={t("glance.attribution.ic_tooltip")}
              >
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
                {t("coverage.label.tested")} {COVERAGE_TALLY.testedFamilies}
              </Badge>
              <Badge variant="outline" className="gap-1 px-1.5 py-0 text-[10px] font-normal text-amber-600 dark:text-amber-400">
                {t("coverage.label.exploratory")} {COVERAGE_TALLY.exploratoryFamilies}
              </Badge>
              <Badge variant="outline" className="gap-1 px-1.5 py-0 text-[10px] font-normal text-muted-foreground">
                {t("glance.coverage.families")} 5
              </Badge>
            </div>
          </CardContent>
        </Card>
      </Link>
    </section>
  );
}
