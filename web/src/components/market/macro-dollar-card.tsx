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
import { cn } from "@/lib/utils";
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

export function MacroDollarCard() {
  const { t } = useI18n();
  const md = aionis.macroDrivers;
  const dxy = (md?.series?.dxy ?? []) as { month: string; value: number }[];

  if (md?.status !== "ok" || dxy.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">{t("macro.dollar.title")}</CardTitle>
          <CardDescription>{t("macro.dollar.hint")}</CardDescription>
        </CardHeader>
        <CardContent className="p-6 text-sm text-muted-foreground">
          {t("market.awaiting")}
        </CardContent>
      </Card>
    );
  }

  const first = dxy[0].value;
  const last = dxy.at(-1)!.value;
  const pct = (last / first - 1) * 100;

  const tone =
    pct > 3
      ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400"
      : pct < -3
      ? "border-rose-500/40 bg-rose-500/10 text-rose-600 dark:text-rose-400"
      : "text-muted-foreground";

  const label =
    pct > 3
      ? t("macro.dollar.strong")
      : pct < -3
      ? t("macro.dollar.weak")
      : t("macro.dollar.neutral");

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-base">{t("macro.dollar.title")}</CardTitle>
            <CardDescription>{t("macro.dollar.hint")}</CardDescription>
          </div>
          <Badge variant="outline" className={cn("shrink-0", tone)}>
            {label} {pct >= 0 ? "+" : ""}{pct.toFixed(1)}%
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="p-4">
        <div className="h-[180px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={dxy} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis
                dataKey="month"
                tick={{ fontSize: 9 }}
                interval={18}
                tickFormatter={(m: string) => m.slice(0, 7)}
              />
              <YAxis
                tick={{ fontSize: 10 }}
                tickFormatter={(v: number) => v.toFixed(0)}
              />
              <Tooltip content={<ChartTooltip />} />
              <ReferenceLine
                y={first}
                stroke="hsl(var(--muted-foreground))"
                strokeDasharray="3 3"
                strokeWidth={1}
              />
              <Line
                type="monotone"
                dataKey="value"
                name={t("macro.dollar.label")}
                stroke="oklch(0.6 0.15 250)"
                strokeWidth={1.5}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <p className="mt-2 text-xs text-muted-foreground">
          {t("macro.dollar.vs_start")}: {pct >= 0 ? "+" : ""}{pct.toFixed(1)}%
        </p>
      </CardContent>
    </Card>
  );
}