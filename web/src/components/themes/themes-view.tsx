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
import { ShieldCheckIcon } from "lucide-react";

// Literal-keyed maps so the strict `t(key)` union accepts them (template
// literals like `themes.${key}` are not assignable to the dict key union).
type ThemeLabelKey =
  | "themes.price"
  | "themes.macro"
  | "themes.fundamentals"
  | "themes.news_sentiment"
  | "themes.risk"
  | "themes.net_cost"
  | "themes.market_structure";
const THEME_LABEL: Record<string, ThemeLabelKey> = {
  price: "themes.price",
  macro: "themes.macro",
  fundamentals: "themes.fundamentals",
  news_sentiment: "themes.news_sentiment",
  risk: "themes.risk",
  net_cost: "themes.net_cost",
  market_structure: "themes.market_structure",
};

type StatusKey =
  | "themes.status.live"
  | "themes.status.partial"
  | "themes.status.forward_only"
  | "themes.status.needs_work";
const STATUS_KEY: Record<string, StatusKey> = {
  live: "themes.status.live",
  partial: "themes.status.partial",
  forward_only: "themes.status.forward_only",
  needs_work: "themes.status.needs_work",
};
const STATUS_STYLE: Record<string, string> = {
  live: "border-emerald-500/40 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400",
  partial: "border-amber-500/40 bg-amber-500/10 text-amber-700 dark:text-amber-400",
  forward_only: "border-muted-foreground/30 bg-muted/40 text-muted-foreground",
  needs_work: "border-rose-500/40 bg-rose-500/10 text-rose-700 dark:text-rose-400",
};

function Sparkline({ data, className }: { data: number[]; className?: string }) {
  if (data.length < 2) return null;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const w = 100;
  const h = 24;
  const pts = data
    .map((v, i) => `${(i / (data.length - 1)) * w},${h - ((v - min) / range) * h}`)
    .join(" ");
  return (
    <svg
      viewBox={`0 0 ${w} ${h}`}
      className={cn("h-6 w-full", className)}
      preserveAspectRatio="none"
      aria-hidden
    >
      <polyline
        points={pts}
        fill="none"
        stroke="currentColor"
        strokeWidth={1.5}
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  );
}

export function ThemesView() {
  const { t } = useI18n();
  const th = aionis.themes;
  const themes = th.themes ?? [];

  return (
    <div className="space-y-6 p-4 md:p-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-bold tracking-tight">{t("themes.title")}</h1>
        <p className="text-sm text-muted-foreground">
          {t("themes.window")}
          {th.as_of_date ? ` · ${t("themes.asof")} ${th.as_of_date}` : ""}
        </p>
      </header>

      {th.status !== "ok" || themes.length === 0 ? (
        <Card className="border-amber-500/30 bg-amber-500/5">
          <CardContent className="p-4 text-sm text-muted-foreground">
            {t("themes.awaiting")}
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {themes.map((theme) => {
            const seriesVals = (theme.series ?? [])
              .map((s) => s.value)
              .filter((v): v is number => typeof v === "number");
            return (
              <Card key={theme.key} className="overflow-hidden py-0">
                <CardHeader className="border-b">
                  <CardTitle className="flex items-center justify-between gap-2 text-base">
                    <span>{t(THEME_LABEL[theme.key] ?? "themes.risk")}</span>
                    <Badge
                      variant="outline"
                      className={cn(STATUS_STYLE[theme.status] ?? "", "shrink-0")}
                    >
                      {t(STATUS_KEY[theme.status] ?? "themes.status.needs_work")}
                    </Badge>
                  </CardTitle>
                  {theme.headline ? (
                    <CardDescription>{theme.headline}</CardDescription>
                  ) : null}
                </CardHeader>
                <CardContent className="p-4">
                  {(theme.signals ?? []).length > 0 ? (
                    <div className="space-y-2">
                      {(theme.signals ?? []).map((s) => (
                        <div
                          key={s.name}
                          className="flex items-center justify-between text-sm"
                        >
                          <span className="truncate font-mono text-xs text-muted-foreground">
                            {s.name}
                          </span>
                          <span className="ml-2 shrink-0 tabular-nums font-medium">
                            {s.value === null || s.value === undefined
                              ? "—"
                              : s.value}
                          </span>
                        </div>
                      ))}
                      {seriesVals.length >= 2 ? (
                        <Sparkline
                          className="text-emerald-600 dark:text-emerald-400"
                          data={seriesVals}
                        />
                      ) : null}
                    </div>
                  ) : (
                    <p className="text-xs italic text-muted-foreground">
                      {t("themes.awaiting")}
                    </p>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      <Card className="border-dashed">
        <CardHeader className="border-b">
          <CardTitle className="flex items-center gap-2 text-base">
            <ShieldCheckIcon className="size-4" /> {t("themes.methodology_title")}
          </CardTitle>
        </CardHeader>
        <CardContent className="p-4">
          <p className="text-xs text-muted-foreground">{th.methodology}</p>
        </CardContent>
      </Card>
    </div>
  );
}
