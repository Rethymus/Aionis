"use client";

import Link from "next/link";
import { useState } from "react";
import { ArrowRightIcon } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { useI18n } from "@/i18n/provider";
import { aionis } from "@/data/aionis";
import {
  CATEGORY_LABEL,
  CATEGORY_ORDER,
  categoryLabelKey,
  fmtUsd,
  type Category,
} from "@/components/institutions/manager-book";

// /institutions = the CATEGORY DIRECTORY over the star-manager 13F registry:
// KPI row + filter chips (all + the 7 editorial categories) + one summary
// card per manager (name / zh label / category / latest quarter / positions /
// top holding / reported value), linking to the /manager/[cik] static detail
// page where the full top-10 book + quarter-over-quarter changes live.
// Everything is client-filtered — no extra data fetch, no server round-trip.

type CategoryFilter = "all" | Category;

export function InstitutionsView() {
  const { t } = useI18n();
  const f = aionis.form13f;
  const [filter, setFilter] = useState<CategoryFilter>("all");

  if (f.status !== "ok" || f.managers.length === 0) {
    return (
      <div className="space-y-6 p-4 md:p-6">
        <header className="space-y-1">
          <h1 className="text-2xl font-bold tracking-tight">
            {t("institutions.title")}
          </h1>
          <p className="text-sm text-muted-foreground">{t("institutions.window")}</p>
        </header>
        <Card className="border-amber-500/30 bg-amber-500/5">
          <CardContent className="space-y-1 p-4">
            <p className="text-sm font-medium text-amber-700 dark:text-amber-400">
              {t("institutions.awaiting")}
            </p>
            <p className="text-xs text-muted-foreground">{f.methodology}</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const combinedValue = f.managers.reduce((acc, m) => acc + m.total_value, 0);
  // Honest per-category counts drive both the chip labels and the filter —
  // categories with zero managers simply render no chip.
  const counts = new Map<string, number>();
  for (const m of f.managers) {
    counts.set(m.category, (counts.get(m.category) ?? 0) + 1);
  }
  const visible =
    filter === "all"
      ? f.managers
      : f.managers.filter((m) => m.category === filter);

  const chipBase =
    "rounded-full border px-3 py-1 text-xs font-medium transition-colors";

  return (
    <div className="space-y-6 p-4 md:p-6">
      <p className="text-xs font-medium text-primary">{t("institutions.role")}</p>
      <header className="space-y-1">
        <h1 className="text-2xl font-bold tracking-tight">{t("institutions.title")}</h1>
        <p className="text-sm text-muted-foreground">{t("institutions.window")}</p>
      </header>

      <div className="grid grid-cols-3 gap-3">
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">{t("institutions.kpi_managers")}</p>
            <p className="mt-1 text-2xl font-bold tabular-nums">{f.managers.length}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">{t("institutions.kpi_quarter")}</p>
            <p className="mt-1 text-2xl font-bold tabular-nums">{f.as_of}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">{t("institutions.kpi_value")}</p>
            <p className="mt-1 text-2xl font-bold tabular-nums">{fmtUsd(combinedValue)}</p>
          </CardContent>
        </Card>
      </div>

      {/* Category filter chips: 全部 + the 7 editorial categories, with the
          honest per-category manager count. Client-side filter only. */}
      <div className="flex flex-wrap items-center gap-1.5">
        <button
          type="button"
          onClick={() => setFilter("all")}
          aria-pressed={filter === "all"}
          className={cn(
            chipBase,
            filter === "all"
              ? "border-primary bg-primary text-primary-foreground"
              : "bg-background text-muted-foreground hover:text-foreground",
          )}
        >
          {t("institutions.cat_all")} ({f.managers.length})
        </button>
        {CATEGORY_ORDER.filter((c) => counts.get(c)).map((c) => (
          <button
            key={c}
            type="button"
            onClick={() => setFilter(c)}
            aria-pressed={filter === c}
            className={cn(
              chipBase,
              filter === c
                ? "border-primary bg-primary text-primary-foreground"
                : "bg-background text-muted-foreground hover:text-foreground",
            )}
          >
            {t(CATEGORY_LABEL[c])} ({counts.get(c)})
          </button>
        ))}
      </div>
      <p className="text-xs text-muted-foreground">{t("institutions.cat_note")}</p>

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {visible.map((m) => (
          <Link key={m.cik} href={`/manager/${m.cik}`} className="group block">
            <Card className="h-full py-0 transition-colors group-hover:border-primary/40">
              <CardHeader className="border-b">
                <div className="flex flex-wrap items-center gap-2">
                  <CardTitle className="text-sm">{m.name}</CardTitle>
                  {m.zh_name ? (
                    <span className="text-xs text-muted-foreground">{m.zh_name}</span>
                  ) : null}
                </div>
                <CardDescription className="flex flex-wrap items-center gap-1.5">
                  <Badge variant="secondary" className="text-[11px]">
                    {t(categoryLabelKey(m.category))}
                  </Badge>
                  <Badge variant="outline" className="tabular-nums text-[11px]">
                    {m.quarter}
                  </Badge>
                  <span className="text-[11px]">
                    {t("institutions.filed")} {m.filed}
                  </span>
                </CardDescription>
              </CardHeader>
              <CardContent className="grid grid-cols-2 gap-x-3 gap-y-2 p-4 text-xs">
                <div>
                  <p className="text-muted-foreground">{t("institutions.n_positions")}</p>
                  <p className="mt-0.5 font-medium tabular-nums">{m.n_positions}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">{t("institutions.total_value")}</p>
                  <p className="mt-0.5 font-medium tabular-nums">
                    {fmtUsd(m.total_value)}
                  </p>
                </div>
                <div className="col-span-2">
                  <p className="text-muted-foreground">{t("institutions.top_holding")}</p>
                  <p className="mt-0.5 truncate font-medium">
                    {m.top10[0] ? m.top10[0].issuer : "—"}
                    {m.top10[0] ? (
                      <span className="ml-1 font-normal text-muted-foreground tabular-nums">
                        {m.top10[0].pct.toFixed(1)}%
                      </span>
                    ) : null}
                  </p>
                </div>
                <p className="col-span-2 mt-1 inline-flex items-center gap-1 text-primary">
                  {t("institutions.view_detail")}
                  <ArrowRightIcon className="size-3 transition-transform group-hover:translate-x-0.5" />
                </p>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>

      <p className="text-xs text-muted-foreground">{t("institutions.explain")}</p>
    </div>
  );
}
