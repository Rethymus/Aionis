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
import type { DictKey } from "@/i18n/dict";
import {
  Line,
  LineChart,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

export function TacoView() {
  const { t } = useI18n();
  const taco = aionis.taco;
  const data = taco.vix_series;
  const kpis: { label: DictKey; value: string; tone: "amber" | "rose" | "emerald" }[] = [
    { label: "taco.climbdowns", value: String(taco.climbdowns_count), tone: "emerald" },
    { label: "taco.escalations", value: String(taco.escalations_count), tone: "rose" },
    {
      label: "taco.latest_vix",
      value: taco.latest_vix != null ? taco.latest_vix.toFixed(2) : "—",
      tone: "amber",
    },
  ];

  return (
    <div className="space-y-6 p-4 md:p-6">
      <p className="text-xs font-medium text-primary">{t("taco.role")}</p>
      <header className="space-y-1">
        <h1 className="text-2xl font-bold tracking-tight">{t("taco.title")}</h1>
        <p className="text-sm text-muted-foreground">{t("taco.subtitle")}</p>
      </header>

      <div className="grid grid-cols-3 gap-3">
        {kpis.map((k) => (
          <Card key={k.label}>
            <CardContent className="p-4">
              <p className="text-xs text-muted-foreground">{t(k.label)}</p>
              <p
                className={cn(
                  "mt-1 text-2xl font-bold tabular-nums",
                  k.tone === "emerald" && "text-emerald-600 dark:text-emerald-400",
                  k.tone === "rose" && "text-rose-600 dark:text-rose-400",
                  k.tone === "amber" && "text-amber-600 dark:text-amber-400",
                )}
              >
                {k.value}
              </p>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader className="border-b">
          <CardTitle className="text-base">VIX</CardTitle>
          <CardDescription>{t("taco.subtitle")}</CardDescription>
        </CardHeader>
        <CardContent className="p-2">
          <div className="h-[320px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data} margin={{ top: 12, right: 20, bottom: 24, left: 12 }}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                <XAxis
                  dataKey="month"
                  minTickGap={32}
                  tickFormatter={(v) => String(v).slice(0, 7)}
                  className="text-xs"
                />
                <YAxis tickFormatter={(v) => Number(v).toFixed(0)} className="text-xs" />
                <Tooltip
                  formatter={(v) => Number(v).toFixed(2)}
                  labelFormatter={(l) => String(l)}
                  contentStyle={{ fontSize: "12px" }}
                />
                <Line type="monotone" dataKey="vix" stroke="#d97706" strokeWidth={1.5} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      <Card className="overflow-hidden py-0">
        <CardHeader className="border-b">
          <CardTitle className="text-base">{t("taco.events.title")}</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="divide-y">
            {taco.events.map((e) => {
              const concession = e.type === "concession";
              return (
                <div key={e.date + e.label} className="flex items-center gap-3 px-4 py-2.5 text-sm">
                  <span className="w-24 shrink-0 font-mono text-xs text-muted-foreground">
                    {e.date}
                  </span>
                  <Badge
                    variant="outline"
                    className={cn(
                      "shrink-0 px-1.5 py-0 text-[10px]",
                      concession
                        ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                        : "border-rose-500/40 bg-rose-500/10 text-rose-600 dark:text-rose-400",
                    )}
                  >
                    {t(concession ? "taco.event.concession" : "taco.event.escalation")}
                  </Badge>
                  <span className="truncate">{e.label}</span>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      <Card className="border-amber-500/30 bg-amber-500/5">
        <CardContent className="space-y-1 p-4">
          <p className="text-xs font-semibold text-amber-700 dark:text-amber-400">
            {t("taco.methodology")}
          </p>
          <p className="text-xs text-muted-foreground">{t("taco.methodology.body")}</p>
        </CardContent>
      </Card>
    </div>
  );
}
