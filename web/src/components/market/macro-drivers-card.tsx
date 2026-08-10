"use client";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useI18n } from "@/i18n/provider";
import { aionis } from "@/data/aionis";
import {
  CartesianGrid,
  Line,
  LineChart,
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

export function MacroDriversCard() {
  const { t } = useI18n();
  const md = aionis.macroDrivers;

  if (md?.status !== "ok" || !md?.series) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">{t("macro.title")}</CardTitle>
          <CardDescription>{t("macro.hint")}</CardDescription>
        </CardHeader>
        <CardContent className="p-6 text-sm text-muted-foreground">
          {t("market.awaiting")}
        </CardContent>
      </Card>
    );
  }

  const cpiData = md.series.cpi_yoy || [];
  const payrollsData = md.series.payems_yoy || [];
  const fedfundsData = md.series.fedfunds || [];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{t("macro.title")}</CardTitle>
        <CardDescription>{t("macro.hint")}</CardDescription>
      </CardHeader>
      <CardContent className="p-4">
        <div className="grid gap-4 md:grid-cols-3">
          {/* CPI YoY Chart */}
          <div className="space-y-2">
            <h4 className="text-xs font-semibold text-foreground">{t("macro.cpi")}</h4>
            <div className="h-[140px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={cpiData} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                  <XAxis
                    dataKey="month"
                    tick={{ fontSize: 9 }}
                    interval={18}
                    tickFormatter={(m: string) => m.slice(0, 7)}
                  />
                  <YAxis
                    tick={{ fontSize: 10 }}
                    tickFormatter={(v: number) => `${v}%`}
                  />
                  <Tooltip content={<ChartTooltip />} />
                  <Line
                    type="monotone"
                    dataKey="value"
                    name={t("macro.cpi")}
                    stroke="oklch(0.65 0.21 25)"
                    strokeWidth={1.5}
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Payrolls YoY Chart */}
          <div className="space-y-2">
            <h4 className="text-xs font-semibold text-foreground">{t("macro.payrolls")}</h4>
            <div className="h-[140px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={payrollsData} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                  <XAxis
                    dataKey="month"
                    tick={{ fontSize: 9 }}
                    interval={18}
                    tickFormatter={(m: string) => m.slice(0, 7)}
                  />
                  <YAxis
                    tick={{ fontSize: 10 }}
                    tickFormatter={(v: number) => `${v}%`}
                  />
                  <Tooltip content={<ChartTooltip />} />
                  <Line
                    type="monotone"
                    dataKey="value"
                    name={t("macro.payrolls")}
                    stroke="oklch(0.55 0.16 152)"
                    strokeWidth={1.5}
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Fed Funds Chart */}
          <div className="space-y-2">
            <h4 className="text-xs font-semibold text-foreground">{t("macro.fedfunds")}</h4>
            <div className="h-[140px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={fedfundsData} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                  <XAxis
                    dataKey="month"
                    tick={{ fontSize: 9 }}
                    interval={18}
                    tickFormatter={(m: string) => m.slice(0, 7)}
                  />
                  <YAxis
                    tick={{ fontSize: 10 }}
                    tickFormatter={(v: number) => `${v}%`}
                  />
                  <Tooltip content={<ChartTooltip />} />
                  <Line
                    type="monotone"
                    dataKey="value"
                    name={t("macro.fedfunds")}
                    stroke="oklch(0.6 0.15 250)"
                    strokeWidth={1.5}
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}