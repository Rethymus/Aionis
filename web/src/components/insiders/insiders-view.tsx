"use client";

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

export function InsidersView() {
  const { t } = useI18n();
  const f = aionis.form4;

  if (f.status === "awaiting_fetch") {
    return (
      <div className="space-y-6 p-4 md:p-6">
        <header className="space-y-1">
          <h1 className="text-2xl font-bold tracking-tight">{t("insiders.title")}</h1>
          <p className="text-sm text-muted-foreground">{t("insiders.window")}</p>
        </header>
        <Card className="border-amber-500/30 bg-amber-500/5">
          <CardContent className="space-y-1 p-4">
            <p className="text-sm font-medium text-amber-700 dark:text-amber-400">
              {t("insiders.awaiting")}
            </p>
            <p className="text-xs text-muted-foreground">{f.methodology}</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-4 md:p-6">
      <p className="text-xs font-medium text-primary">{t("insiders.role")}</p>
      <header className="space-y-1">
        <h1 className="text-2xl font-bold tracking-tight">{t("insiders.title")}</h1>
        <p className="text-sm text-muted-foreground">{t("insiders.window")}</p>
      </header>

      <div className="grid grid-cols-3 gap-3">
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">{t("insiders.buys")}</p>
            <p className="mt-1 text-2xl font-bold tabular-nums text-emerald-600 dark:text-emerald-400">
              {f.buys}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">{t("insiders.sells")}</p>
            <p className="mt-1 text-2xl font-bold tabular-nums text-rose-600 dark:text-rose-400">
              {f.sells}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">{t("insiders.n_insiders")}</p>
            <p className="mt-1 text-2xl font-bold tabular-nums">{f.n_filers}</p>
          </CardContent>
        </Card>
      </div>

      <Card className="overflow-hidden py-0">
        <CardHeader className="border-b">
          <CardTitle className="text-base">{t("insiders.top")}</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="divide-y">
            {f.top_insiders.map((ins, i) => (
              <div key={ins.filer + i} className="flex items-center gap-3 px-4 py-2.5 text-sm">
                <span className="w-6 shrink-0 text-muted-foreground tabular-nums">{i + 1}</span>
                <span className="truncate">{ins.filer}</span>
                <Badge variant="secondary" className="ml-auto shrink-0 tabular-nums">
                  {ins.count}
                </Badge>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card className="overflow-hidden py-0">
        <CardHeader className="border-b">
          <CardTitle className="text-base">{t("insiders.recent")}</CardTitle>
          <CardDescription>{t("insiders.window")}</CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          <div className="divide-y">
            {f.recent.map((r, i) => {
              const buy = r.action === "buy";
              return (
                <div key={i} className="flex items-center gap-3 px-4 py-2.5 text-sm">
                  <span className="w-24 shrink-0 font-mono text-xs text-muted-foreground">
                    {r.date}
                  </span>
                  <Badge
                    variant="outline"
                    className={cn(
                      "shrink-0 px-1.5 py-0 text-[10px]",
                      buy
                        ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                        : "border-rose-500/40 bg-rose-500/10 text-rose-600 dark:text-rose-400",
                    )}
                  >
                    {t(buy ? "insiders.buy" : "insiders.sell")}
                  </Badge>
                  <span className="w-32 shrink-0 truncate text-muted-foreground">{r.filer}</span>
                  <span className="truncate font-medium">{r.ticker}</span>
                  {r.shares != null ? (
                    <span className="ml-auto shrink-0 font-mono text-xs tabular-nums text-muted-foreground">
                      {r.shares.toLocaleString()} @ ${r.price ?? "—"}
                    </span>
                  ) : null}
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      <p className="text-xs text-muted-foreground">{t("insiders.explain")}</p>
    </div>
  );
}
