"use client";

import {
  Card,
  CardContent,
  CardHeader,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { useI18n } from "@/i18n/provider";
import { aionis, type Evidence } from "@/data/aionis";
import type { DictKey } from "@/i18n/dict";

function gradeStyle(grade: Evidence["grade"]): {
  labelKey: DictKey;
  className: string;
} {
  switch (grade) {
    case "CONFIRMATORY":
      return {
        labelKey: "evidence.grade.CONFIRMATORY",
        className: "border-destructive/40 bg-destructive/10 text-destructive",
      };
    case "CV-proxy":
      return {
        labelKey: "evidence.grade.CV-proxy",
        className: "bg-muted text-muted-foreground",
      };
    default:
      return {
        labelKey: "evidence.grade.chron",
        className: "border-primary/30 bg-primary/10 text-primary",
      };
  }
}

function Stat({ label, value, tone }: { label: string; value: number; tone: "muted" | "destructive" | "primary" }) {
  return (
    <div className="space-y-0.5">
      <p
        className={cn(
          "text-2xl font-bold tabular-nums",
          tone === "destructive" && "text-destructive",
          tone === "primary" && "text-primary",
        )}
      >
        {value}
      </p>
      <p className="text-xs text-muted-foreground">{label}</p>
    </div>
  );
}

export function EvidenceView() {
  const { t } = useI18n();
  const ev = aionis.evidence;
  const counts = {
    total: ev.length,
    confirmatory: ev.filter((e) => e.grade === "CONFIRMATORY").length,
    cvproxy: ev.filter((e) => e.grade === "CV-proxy").length,
    chron: ev.filter((e) => e.grade !== "CV-proxy" && e.grade !== "CONFIRMATORY").length,
  };

  return (
    <div className="space-y-6 p-4 md:p-6">
      <header className="space-y-2">
        <h1 className="text-2xl font-bold tracking-tight">{t("module.evidence.title")}</h1>
        <p className="max-w-2xl text-sm text-muted-foreground">{t("evidence.intro")}</p>
        <div className="flex flex-wrap gap-x-8 gap-y-2 pt-2">
          <Stat label={t("nav.evidence")} value={counts.total} tone="muted" />
          <Stat label={t("evidence.grade.CONFIRMATORY")} value={counts.confirmatory} tone="destructive" />
          <Stat label={t("evidence.grade.CV-proxy")} value={counts.cvproxy} tone="primary" />
          <Stat label={t("evidence.grade.chron")} value={counts.chron} tone="muted" />
        </div>
      </header>

      <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
        {ev.map((e) => {
          const g = gradeStyle(e.grade);
          const hasCI = e.ci_lo !== null && e.ci_hi !== null;
          const bracketsZero = hasCI && e.ci_lo! < 0 && e.ci_hi! > 0;
          return (
            <Card key={e.n} className="overflow-hidden">
              <CardHeader className="gap-2">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs text-muted-foreground">#{e.n}</span>
                  <Badge variant="outline" className={cn("px-2 py-0 text-[10px]", g.className)}>
                    {t(g.labelKey)}
                  </Badge>
                </div>
                <p className="text-sm font-medium leading-tight">{e.result}</p>
              </CardHeader>
              <CardContent className="space-y-1.5">
                <div className="flex items-baseline gap-2">
                  <span className="text-2xl font-bold tabular-nums">
                    {e.estimate > 0 ? "+" : ""}
                    {e.estimate.toFixed(4)}
                  </span>
                  {hasCI ? (
                    <span
                      className={cn(
                        "text-xs tabular-nums",
                        bracketsZero ? "text-muted-foreground" : "text-amber-600 dark:text-amber-400",
                      )}
                    >
                      CI [{e.ci_lo!.toFixed(4)}, {e.ci_hi!.toFixed(4)}]
                    </span>
                  ) : null}
                </div>
                <div className="flex items-center gap-3 text-xs text-muted-foreground">
                  {e.p !== null ? <span className="tabular-nums">p = {e.p.toFixed(3)}</span> : null}
                  <span className="tabular-nums">{e.n_months} mo</span>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
