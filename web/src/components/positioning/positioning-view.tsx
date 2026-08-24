"use client";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
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

function zTone(z: number) {
  if (z >= 1) return "text-up";
  if (z <= -1) return "text-down";
  return "text-muted-foreground";
}

export function PositioningView() {
  const { t } = useI18n();
  const c = aionis.cot;

  if (c.status === "awaiting_fetch") {
    return (
      <div className="flex flex-col gap-4">
        <header>
          <h1 className="text-2xl font-semibold tracking-[-0.032em]">{t("positioning.title")}</h1>
          <p className="mt-2 text-[13px] text-mute">{t("positioning.window")}</p>
        </header>
        <Card className="border-amber-500/30 bg-amber-500/5">
          <CardContent className="space-y-1 p-4">
            <p className="text-sm font-medium text-amber-700 dark:text-amber-400">
              {t("insiders.awaiting")}
            </p>
            <p className="text-xs text-muted-foreground">{c.methodology}</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const comp = c.composite;
  const biasPositive = comp.mean_z >= 0;

  return (
    <div className="flex flex-col gap-4">
      <p className="text-xs font-medium text-primary">{t("positioning.role")}</p>
      <header>
        <h1 className="text-2xl font-semibold tracking-[-0.032em]">{t("positioning.title")}</h1>
        <p className="mt-2 text-[13px] text-mute">{t("positioning.window")}</p>
      </header>

      <div className="grid grid-cols-3 gap-3">
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">{t("positioning.composite")}</p>
            <p
              className={cn(
                "mt-1 text-2xl font-bold tabular-nums",
                biasPositive
                  ? "text-up"
                  : "text-down",
              )}
            >
              {comp.mean_z > 0 ? "+" : ""}
              {comp.mean_z}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">{t("positioning.crowding")}</p>
            <p className="mt-1 text-2xl font-bold tabular-nums text-amber-600 dark:text-amber-400">
              {comp.crowding}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">{t("positioning.latest")}</p>
            <p className="mt-1 text-xl font-bold tabular-nums">{c.latest_date}</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="border-b">
          <CardTitle className="text-base">{t("positioning.series")}</CardTitle>
        </CardHeader>
        <CardContent className="p-2">
          <div className="h-[300px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart
                data={c.composite_series}
                margin={{ top: 12, right: 20, bottom: 24, left: 12 }}
              >
                <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                <XAxis
                  dataKey="date"
                  minTickGap={32}
                  tickFormatter={(v) => String(v).slice(0, 7)}
                  className="text-xs"
                />
                <YAxis domain={[-2, 2]} className="text-xs" />
                <ReferenceLine y={0} stroke="oklch(0.704 0.191 22.216)" strokeDasharray="4 4" />
                <Tooltip
                  formatter={(v) => Number(v).toFixed(2)}
                  labelFormatter={(l) => String(l)}
                  contentStyle={{ fontSize: "12px" }}
                />
                <Line type="monotone" dataKey="z" stroke="#0b3d61" strokeWidth={1.5} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="border-b">
          <CardTitle className="text-base">{t("positioning.markets")}</CardTitle>
          <CardDescription>{t("positioning.window")}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-2.5 p-4">
          {c.markets.map((m) => {
            const pct = Math.min(Math.abs(m.z) / 3, 1) * 50;
            const isLong = m.z > 0;
            return (
              <div key={m.name} className="flex items-center gap-3 text-sm">
                <span className="w-24 shrink-0 truncate">{m.name}</span>
                <div className="relative h-5 flex-1">
                  <div className="absolute left-1/2 top-0 h-full w-px bg-border" />
                  <div
                    className={cn(
                      "absolute top-0 h-full rounded-sm",
                      isLong ? "left-1/2 bg-up-soft" : "right-1/2 bg-down-soft",
                    )}
                    style={{ width: `${pct}%` }}
                  />
                </div>
                <span
                  className={cn(
                    "w-10 shrink-0 text-right font-mono tabular-nums",
                    zTone(m.z),
                  )}
                >
                  {m.z > 0 ? "+" : ""}
                  {m.z}
                </span>
              </div>
            );
          })}
          <div className="flex justify-between pt-1 text-xs text-muted-foreground">
            <span>← {t("positioning.netshort")}</span>
            <span>{t("positioning.netlong")} →</span>
          </div>
        </CardContent>
      </Card>

      <p className="text-xs text-muted-foreground">{c.methodology}</p>
    </div>
  );
}
