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
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { TrendingUpIcon, ActivityIcon, CalendarIcon } from "lucide-react";
import { MacroDriversCard } from "./macro-drivers-card";
import { MacroStagflationRead } from "./macro-stagflation-read";

const EVENT_TONE: Record<string, string> = {
  political: "border-blue-400/50 text-blue-700 dark:text-blue-300",
  trade: "border-amber-400/50 text-amber-700 dark:text-amber-300",
  crisis: "border-rose-500/60 text-rose-700 dark:text-rose-300",
  monetary: "border-violet-400/50 text-violet-700 dark:text-violet-300",
  inauguration: "border-emerald-500/70 text-emerald-700 dark:text-emerald-300",
  fed_pressure: "border-orange-500/60 bg-orange-500/10 text-orange-700 dark:text-orange-400",
};

const EVENT_TYPE_LABEL: Record<string, string> = {
  political: "政治",
  trade: "贸易",
  crisis: "危机",
  monetary: "货币",
  inauguration: "就职",
  fed_pressure: "美联储博弈",
};

function RiskStat({ label, value, tone }: { label: string; value: string; tone?: "rose" | "emerald" }) {
  return (
    <div className="flex items-baseline justify-between gap-2">
      <span className="text-xs text-muted-foreground">{label}</span>
      <span
        className={cn(
          "font-mono text-sm font-semibold tabular-nums",
          tone === "rose" && "text-rose-600 dark:text-rose-400",
          tone === "emerald" && "text-emerald-600 dark:text-emerald-400",
        )}
      >
        {value}
      </span>
    </div>
  );
}

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

export function MarketView() {
  const { t } = useI18n();
  const mc = aionis.marketContext;
  if (!mc?.market_series?.length) {
    return (
      <div className="space-y-6 p-4 md:p-6">
        <h1 className="text-2xl font-bold tracking-tight">{t("module.market.title")}</h1>
        <Card><CardContent className="p-6 text-sm text-muted-foreground">{t("market.awaiting")}</CardContent></Card>
      </div>
    );
  }

  // Merge VIX + market index by month for the dual-axis chart.
  const vixByMonth = new Map(mc.vix_series.map((v) => [v.month, v.vix]));
  const chartData = mc.market_series.map((m) => ({
    month: m.month,
    index: m.index,
    vix: vixByMonth.get(m.month) ?? null,
  }));

  const startIndex = mc.market_series[0].index;
  const lastIndex = mc.market_series[mc.market_series.length - 1];
  const totalReturn = ((lastIndex.index / startIndex - 1) * 100);
  const peakVix = Math.max(...mc.vix_series.map((v) => v.vix));
  const peakIndex = Math.max(...mc.market_series.map((m) => m.index));

  const kpis = [
    { label: t("market.kpi.total_return"), value: `+${totalReturn.toFixed(0)}%`, tone: "text-emerald-600 dark:text-emerald-400", icon: TrendingUpIcon },
    { label: t("market.kpi.peak_index"), value: peakIndex.toFixed(0), tone: "text-foreground", icon: TrendingUpIcon },
    { label: t("market.kpi.peak_vix"), value: peakVix.toFixed(1), tone: "text-rose-600 dark:text-rose-400", icon: ActivityIcon },
    { label: t("market.kpi.span"), value: `${mc.n_months} ${t("market.kpi.months")}`, tone: "text-foreground", icon: CalendarIcon },
  ];

  return (
    <div className="space-y-6 p-4 md:p-6">
      <p className="text-xs font-medium text-primary">{t("market.role")}</p>
      <header className="space-y-2">
        <h1 className="text-2xl font-bold tracking-tight">{t("module.market.title")}</h1>
        <p className="max-w-2xl text-sm text-muted-foreground">{t("market.intro")}</p>
        <Badge variant="outline" className="w-fit border-amber-400/50 text-amber-700 dark:text-amber-300">
          {mc.start_label}
        </Badge>
      </header>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {kpis.map((k) => (
          <Card key={k.label}>
            <CardContent className="flex flex-col gap-1 p-3">
              <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground">
                <k.icon className="size-3" />
                {k.label}
              </div>
              <span className={cn("font-mono text-lg font-semibold tabular-nums", k.tone)}>
                {k.value}
              </span>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader className="border-b">
          <CardTitle className="text-base">{t("market.chart.title")}</CardTitle>
          <CardDescription>{t("market.chart.desc")}</CardDescription>
        </CardHeader>
        <CardContent className="p-2">
          <ResponsiveContainer width="100%" height={320}>
            <ComposedChart data={chartData} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis
                dataKey="month"
                tick={{ fontSize: 10 }}
                interval={11}
                tickFormatter={(m: string) => m.slice(0, 7)}
              />
              <YAxis
                yAxisId="index"
                orientation="left"
                tick={{ fontSize: 10 }}
                domain={["dataMin - 20", "dataMax + 20"]}
              />
              <YAxis
                yAxisId="vix"
                orientation="right"
                tick={{ fontSize: 10 }}
                domain={[0, "dataMax + 10"]}
              />
              <Tooltip content={<ChartTooltip />} />
              <defs>
                <linearGradient id="indexGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="oklch(0.72 0.17 152)" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="oklch(0.72 0.17 152)" stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <Area
                yAxisId="index"
                type="monotone"
                dataKey="index"
                name={t("market.legend.index")}
                stroke="oklch(0.55 0.16 152)"
                strokeWidth={1.5}
                fill="url(#indexGrad)"
                dot={false}
              />
              <Line
                yAxisId="vix"
                type="monotone"
                dataKey="vix"
                name={t("market.legend.vix")}
                stroke="oklch(0.65 0.21 25)"
                strokeWidth={1.2}
                dot={false}
              />
              {/* 川普元年 start marker */}
              <ReferenceLine
                yAxisId="index"
                x="2016-11"
                stroke="oklch(0.6 0.15 250)"
                strokeDasharray="4 4"
                strokeWidth={1}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {mc.risk ? (
        <Card>
          <CardHeader className="border-b">
            <CardTitle className="text-base">{t("market.risk.title")}</CardTitle>
            <CardDescription>{t("market.risk.hint")}</CardDescription>
          </CardHeader>
          <CardContent className="p-4">
            <div className="grid grid-cols-2 gap-x-4 gap-y-2 md:grid-cols-4">
              <RiskStat label="Sharpe" value={mc.risk.sharpe.toFixed(2)} />
              <RiskStat label="Sortino" value={mc.risk.sortino.toFixed(2)} />
              <RiskStat label="Max Drawdown" value={`${(mc.risk.max_drawdown * 100).toFixed(1)}%`} tone="rose" />
              <RiskStat label="Calmar" value={mc.risk.calmar.toFixed(2)} />
              <RiskStat label="VaR 95%" value={`${(mc.risk.var_95 * 100).toFixed(1)}%`} tone="rose" />
              <RiskStat label="CVaR 95%" value={`${(mc.risk.cvar_95 * 100).toFixed(1)}%`} tone="rose" />
              <RiskStat label="Annual return" value={`${(mc.risk.annual_return * 100).toFixed(1)}%`} tone="emerald" />
              <RiskStat label="Months" value={String(mc.risk.n_periods)} />
            </div>
          </CardContent>
        </Card>
      ) : null}

      <Card className="overflow-hidden py-0">
        <CardHeader className="border-b">
          <CardTitle className="text-base">{t("market.events.title")}</CardTitle>
          <CardDescription>{t("market.events.desc")}</CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          <div className="divide-y">
            {mc.events.map((e) => (
              <div key={`${e.date}-${e.label}`} className="flex items-center gap-3 px-4 py-2.5">
                <span className="w-24 shrink-0 font-mono text-xs text-muted-foreground">{e.date}</span>
                <Badge
                  variant="outline"
                  className={cn("shrink-0 px-1.5 py-0 text-[9px] font-normal uppercase", EVENT_TONE[e.type] ?? "")}
                >
                  {EVENT_TYPE_LABEL[e.type] ?? e.type}
                </Badge>
                <span className="flex-1 text-sm">{e.label}</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <MacroDriversCard />
      <MacroStagflationRead />

      <Card>
        <CardContent className="p-4 text-xs text-muted-foreground">
          <p className="font-medium text-foreground">{t("market.methodology_title")}</p>
          <p className="mt-1 leading-relaxed">{mc.methodology}</p>
        </CardContent>
      </Card>
    </div>
  );
}
