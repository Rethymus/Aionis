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
import { aionis, type Theme } from "@/data/aionis";
import { ThemeSlice } from "./theme-slice";
import {
  Area,
  CartesianGrid,
  ComposedChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { ActivityIcon, CalendarIcon, TrendingDownIcon, TrendingUpIcon } from "lucide-react";

// /regime#macro — owner directive (2026-08-29): the macro tab's only graphic
// was the ThemeCard sparkline (h-12, decorative); redesign it in the visual
// language of the "市场指数 × VIX" chart on the market tab (gradient area +
// grid + dashed reference line + shared tooltip + KPI row), so the two tabs
// read as one chart system. Same real data source (themes.json macro theme =
// Track-C macro-regime composite z, 60 sessions) — display-only, no new data
// path. Blue hue (not the up/down semantic pair): the composite's polarity is
// not claimed either way, and research charts keep the red/green convention
// out per the editorial-diagram language (2026-08-28).

function MacroTooltip({ active, payload, label }: {
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

function KpiCard({ label, value, tone, icon: Icon }: {
  label: string;
  value: string;
  tone?: "up" | "down";
  icon: React.ComponentType<{ className?: string }>;
}) {
  return (
    <Card>
      <CardContent className="flex flex-col gap-1 p-3">
        <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <Icon className="size-3" />
          {label}
        </div>
        <span
          className={cn(
            "font-mono text-lg font-semibold tabular-nums",
            tone === "up" && "text-up",
            tone === "down" && "text-down",
          )}
        >
          {value}
        </span>
      </CardContent>
    </Card>
  );
}

function MacroRegimeChartInner({ theme }: { theme: Theme }) {
  const { t } = useI18n();
  // Macro rows carry `date` (daily sessions); the fallback keeps the card
  // renderable if the export ever returns the monthly shape instead.
  const points = (theme.series ?? [])
    .filter((p) => typeof p.value === "number")
    .map((p) => ({ date: p.date ?? p.month ?? "", z: p.value as number }));

  if (points.length < 2) {
    // Degenerate series → fall back to the signal card instead of an empty
    // chart (honest absence, no fabricated flat line).
    return <ThemeSlice keys={["macro"]} />;
  }

  const values = points.map((p) => p.z);
  const latest = values[values.length - 1];
  const peak = Math.max(...values);
  const trough = Math.min(...values);
  // Keep zero in frame — the composite is a z-score around a neutral 0.
  const yMin = Math.min(0, trough) - 0.3;
  const yMax = Math.max(0, peak) + 0.3;
  const xInterval = Math.max(1, Math.floor(points.length / 8));

  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <KpiCard label={t("regime.macro.kpi.latest")} value={latest.toFixed(2)} icon={ActivityIcon} />
        <KpiCard label={t("regime.macro.kpi.peak")} value={peak.toFixed(2)} tone="up" icon={TrendingUpIcon} />
        <KpiCard label={t("regime.macro.kpi.trough")} value={trough.toFixed(2)} tone="down" icon={TrendingDownIcon} />
        <KpiCard
          label={t("regime.macro.kpi.days")}
          value={`${points.length}`}
          icon={CalendarIcon}
        />
      </div>

      <Card>
        <CardHeader className="border-b">
          <div className="flex items-center justify-between gap-2">
            <CardTitle className="text-base">{t("themes.signal.macro_regime")}</CardTitle>
            <Badge
              variant="outline"
              className="shrink-0 px-2 py-0.5 text-xs font-normal text-muted-foreground"
            >
              {t("theme.role.context")}
            </Badge>
          </div>
          <CardDescription>{t("regime.macro.chart.desc")}</CardDescription>
          {theme.as_of ? (
            <p className="font-mono text-xs text-muted-foreground tabular-nums">
              {t("themes.as_of")} {theme.as_of} · {points[0].date} → {points[points.length - 1].date}
            </p>
          ) : null}
        </CardHeader>
        <CardContent className="p-2">
          <ResponsiveContainer width="100%" height={320}>
            <ComposedChart data={points} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
                interval={xInterval}
                // Daily 60-session window → MM-DD ticks (YYYY-MM would repeat
                // the same month label across consecutive ticks).
                tickFormatter={(d: string) => d.slice(5)}
              />
              <YAxis
                tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
                domain={[yMin, yMax]}
                tickFormatter={(v: number) => v.toFixed(1)}
              />
              <Tooltip content={<MacroTooltip />} />
              <defs>
                <linearGradient id="macroRegimeGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="oklch(0.62 0.16 250)" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="oklch(0.62 0.16 250)" stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <Area
                type="monotone"
                dataKey="z"
                name={t("regime.macro.legend")}
                stroke="oklch(0.55 0.17 250)"
                strokeWidth={1.5}
                fill="url(#macroRegimeGrad)"
                dot={false}
              />
              {/* Neutral line: the composite is a z-score — 0 is the anchor. */}
              <ReferenceLine
                y={0}
                stroke="var(--muted-foreground)"
                strokeDasharray="4 4"
                strokeWidth={1}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
    </div>
  );
}

export function MacroRegimeChart() {
  const theme = (aionis.themes.themes ?? []).find((tm) => tm.key === "macro");
  if (!theme) return null;
  return <MacroRegimeChartInner theme={theme} />;
}
