"use client";

import { Card, CardContent } from "@/components/ui/card";
import { CheckCircle2Icon } from "lucide-react";
import { useI18n } from "@/i18n/provider";
import { cn } from "@/lib/utils";

type Item = {
  title: string;
  detail: string;
  badge: string;
};

export function DisciplineView() {
  const { t } = useI18n();

  const items: Item[] = [
    { title: "Point-in-time data", detail: "Fundamentals via filed date · macro via ALFRED vintage · VIX no-revision", badge: "PIT" },
    { title: "PurgedGroupKFold + embargo", detail: "group=month · 21-session embargo · no label leakage", badge: "21" },
    { title: "H₆ determinism", detail: "n_jobs=1 · all seeds 0 · version-pinned (uv.lock) · bit-identical", badge: "H6" },
    { title: "config_committed BEFORE result", detail: "Frozen config sha256 appended to ledger before any OOS metric", badge: "ledger" },
    { title: "Two-tailed pre-registration", detail: "One pre-reg per phase · treatment-vs-baseline differential is the claim", badge: "2-tail" },
    { title: "Multiplicity budget = 1", detail: "Pre-specified interaction only · no K-family inflation", badge: "k=1" },
  ];

  return (
    <div className="space-y-6 p-4 md:p-6">
      <header className="space-y-2">
        <h1 className="text-2xl font-bold tracking-tight">{t("module.discipline.title")}</h1>
        <p className="max-w-2xl text-sm text-muted-foreground">{t("discipline.intro")}</p>
      </header>

      <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
        {items.map((it) => (
          <Card key={it.title} className="overflow-hidden">
            <CardContent className="space-y-2 p-4">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">{it.title}</span>
                <span className="rounded bg-emerald-500/10 px-1.5 py-0.5 font-mono text-[10px] text-emerald-600 dark:text-emerald-400">
                  {it.badge}
                </span>
              </div>
              <p className="text-xs text-muted-foreground">{it.detail}</p>
              <div
                className={cn(
                  "inline-flex items-center gap-1 text-xs font-medium text-emerald-600 dark:text-emerald-400",
                )}
              >
                <CheckCircle2Icon className="size-3.5" />
                PASS
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
