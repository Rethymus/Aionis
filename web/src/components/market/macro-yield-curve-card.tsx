"use client";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useI18n } from "@/i18n/provider";
import { aionis } from "@/data/aionis";
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { cn } from "@/lib/utils";

function ChartTooltip({ active, payload, label }: {
  active?: boolean;
  payload?: { name?: string; value?: number; color?: string }[];
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-md border bg-background p-2 text-xs shadow-sm">
      <div className="mb-1 font-mono font-medium">{label}</div>
      {payload.map((p, i) => (
        <div key={i} className="flex items-center gap-1.5" style={{ color: p.color }}>
          <span className="font-medium">{p.name}:</span>
          <span className="font-mono tabular-nums">
            {typeof p.value === "number" ? p.value.toFixed(2) : p.value}
          </span>
        </div>
      ))}
    </div>
  );
}

export function MacroYieldCurveCard() {
  const { t } = useI18n();
  const md = aionis.macroDrivers;

  if (md?.status !== "ok" || !md?.series) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">{t("macro.yield.title")}</CardTitle>
          <CardDescription>{t("macro.yield.hint")}</CardDescription>
        </CardHeader>
        <CardContent className="p-6 text-sm text-muted-foreground">
          {t("market.awaiting")}
        </CardContent>
      </Card>
    );
  }

  const t10y2y = (md?.series?.t10y2y ?? []) as { month: string; value: number }[];
  if (t10y2y.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">{t("macro.yield.title")}</CardTitle>
          <CardDescription>{t("macro.yield.hint")}</CardDescription>
        </CardHeader>
        <CardContent className="p-6 text-sm text-muted-foreground">
          {t("market.awaiting")}
        </CardContent>
      </Card>
    );
  }

  const last = t10y2y.at(-1)!.value;
  const isCurrentlyInverted = last < 0;
  const last12Points = t10y2y.slice(-12);
  const invertedLast12 = last12Points.filter((p) => p.value < 0).length;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{t("macro.yield.title")}</CardTitle>
        <CardDescription>{t("macro.yield.hint")}</CardDescription>
      </CardHeader>
      <CardContent className="p-4 space-y-3">
        <div className="flex items-center justify-between">
          <Badge
            variant="outline"
            className={cn(
              "border",
              isCurrentlyInverted
                ? "border-rose-500/40 bg-rose-500/10 text-rose-700 dark:text-rose-400"
                : "border-emerald-500/40 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400"
            )}
          >
            {isCurrentlyInverted ? t("macro.yield.inverted") : t("macro.yield.normal")}: {last.toFixed(2)}
          </Badge>
          <span className="text-xs text-muted-foreground">
            {t("macro.yield.inverted_months")}: {invertedLast12}/12
          </span>
        </div>
        <div className="h-[180px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={t10y2y} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis
                dataKey="month"
                tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
                interval={18}
                tickFormatter={(m: string) => m.slice(0, 7)}
              />
              <YAxis
                tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
                tickFormatter={(v: number) => v.toFixed(0)}
              />
              <Tooltip content={<ChartTooltip />} />
              <ReferenceLine
                y={0}
                stroke="oklch(0.6 0.18 25)"
                strokeDasharray="5 5"
                label={{ value: "0", position: "insideBottomRight", fontSize: 10, fill: "oklch(0.6 0.18 25)" }}
              />
              <Line
                type="monotone"
                dataKey="value"
                name={t("macro.yield.label")}
                stroke="oklch(0.65 0.18 40)"
                strokeWidth={1.5}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
