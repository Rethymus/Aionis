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

export function MacroMandateTensionCard() {
  const { t } = useI18n();
  const md = aionis.macroDrivers;
  const unrate = (md?.series?.unrate ?? []) as { month: string; value: number }[];
  const realRate = (md?.series?.real_rate ?? []) as { month: string; value: number }[];

  if (md?.status !== "ok" || unrate.length === 0 || realRate.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">{t("macro.mandate.title")}</CardTitle>
          <CardDescription>{t("macro.mandate.hint")}</CardDescription>
        </CardHeader>
        <CardContent className="p-6 text-sm text-muted-foreground">
          {t("market.awaiting")}
        </CardContent>
      </Card>
    );
  }

  // Merge the two series by month
  const byMonth = new Map<string, { unrate: number | null; real: number | null }>();
  for (const p of unrate) {
    byMonth.set(p.month, { unrate: p.value, real: null });
  }
  for (const p of realRate) {
    const entry = byMonth.get(p.month) ?? { unrate: null, real: null };
    entry.real = p.value;
    byMonth.set(p.month, entry);
  }
  const chartData = [...byMonth.entries()]
    .map(([month, v]) => ({ month, unrate: v.unrate, real: v.real }))
    .sort((a, b) => a.month.localeCompare(b.month));

  const lastReal = realRate.at(-1)!.value;
  const badgeVariant: "outline" | "default" = "outline";
  let badgeClass = "";
  let badgeLabel = "";

  if (lastReal > 0.5) {
    badgeClass = "border-amber-500/40 bg-amber-500/10 text-amber-700 dark:text-amber-400";
    badgeLabel = t("macro.mandate.tight");
  } else if (lastReal < -0.5) {
    badgeClass = "border-emerald-500/40 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400";
    badgeLabel = t("macro.mandate.loose");
  } else {
    badgeClass = "border-muted-foreground/40 bg-muted text-muted-foreground";
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{t("macro.mandate.title")}</CardTitle>
        <CardDescription>{t("macro.mandate.hint")}</CardDescription>
      </CardHeader>
      <CardContent className="p-4">
        <div className="mb-3">
          <Badge variant={badgeVariant} className={cn("px-2 py-0.5 text-xs font-medium", badgeClass)}>
            {badgeLabel || `${lastReal.toFixed(2)}%`}
            {badgeLabel && ` (${lastReal.toFixed(2)}%)`}
          </Badge>
        </div>
        <div className="h-[200px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis
                dataKey="month"
                tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
                interval={18}
                tickFormatter={(m: string) => m.slice(0, 7)}
              />
              <YAxis
                tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
                tickFormatter={(v: number) => `${v}%`}
              />
              <Tooltip content={<ChartTooltip />} />
              <Line
                type="monotone"
                dataKey="unrate"
                name={t("macro.mandate.unrate")}
                stroke="oklch(0.6 0.15 250)"
                strokeWidth={1.5}
                dot={false}
                connectNulls
              />
              <Line
                type="monotone"
                dataKey="real"
                name={t("macro.mandate.real_rate")}
                stroke="oklch(0.65 0.18 40)"
                strokeWidth={1.5}
                dot={false}
                connectNulls
              />
              <ReferenceLine
                y={0}
                stroke="hsl(var(--muted-foreground))"
                strokeDasharray="4 4"
                strokeWidth={1}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
