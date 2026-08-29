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
  Legend,
} from "recharts";

export function ConvictionView() {
  const { t } = useI18n();
  const pc = aionis.pickConviction;
  const high = pc.conviction === "high";
  const latest = pc.latest;

  const kpis: { label: DictKey; value: string; tone: "emerald" | "amber" | "muted" }[] = [
    {
      label: "conviction.latest",
      value: high ? t("conviction.high") : t("conviction.low"),
      tone: high ? "emerald" : "amber",
    },
    {
      label: "conviction.window",
      value: latest ? latest.std.toFixed(3) : "—",
      tone: "muted",
    },
    {
      label: "conviction.trailing",
      value: pc.trailing_std_mean != null ? pc.trailing_std_mean.toFixed(3) : "—",
      tone: "muted",
    },
  ];

  return (
    <div className="flex flex-col gap-4">
      <p className="text-xs font-medium text-primary">{t("conviction.role")}</p>
      <header>
        <h1 className="text-2xl font-semibold tracking-[-0.032em]">{t("conviction.title")}</h1>
        <p className="mt-2 text-[13px] text-mute">{t("conviction.window")}</p>
      </header>

      <div className="grid grid-cols-3 gap-3">
        {kpis.map((k) => (
          <Card key={k.label}>
            <CardContent className="p-4">
              <p className="text-xs text-muted-foreground">{t(k.label)}</p>
              <p
                className={cn(
                  "mt-1 text-xl font-bold tracking-tight tabular-nums md:text-2xl",
                  k.tone === "emerald" && "text-emerald-600 dark:text-emerald-400",
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
          <CardTitle className="text-base">{t("conviction.series")}</CardTitle>
          <CardDescription>
            {/* std dot mirrors the Line stroke below (oklch blue) — the old
                hardcoded navy #0b3d61 was invisible on the dark card. */}
            std <span style={{ color: "oklch(0.55 0.17 250)" }}>●</span> · decile spread{" "}
            <span className="text-amber-500">●</span>
          </CardDescription>
        </CardHeader>
        <CardContent className="p-2">
          <div className="h-[340px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={pc.series} margin={{ top: 12, right: 20, bottom: 24, left: 12 }}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                <XAxis
                  dataKey="date"
                  minTickGap={28}
                  tickFormatter={(v) => String(v).slice(0, 7)}
                  className="text-xs"
                />
                <YAxis tickFormatter={(v) => Number(v).toFixed(1)} className="text-xs" />
                <Tooltip
                  formatter={(v) => Number(v).toFixed(3)}
                  labelFormatter={(l) => String(l)}
                  contentStyle={{ fontSize: "12px" }}
                />
                <Legend wrapperStyle={{ fontSize: "12px" }} />
                {/* Theme-safe blue (same hue family as the macro-regime chart):
                    the old #0b3d61 navy read only on light cards — on dark the
                    line AND its recharts legend label dropped to ~1.7:1. */}
                <Line type="monotone" dataKey="std" name="std" stroke="oklch(0.55 0.17 250)" strokeWidth={1.8} dot={false} />
                <Line type="monotone" dataKey="decile_spread" name="decile spread" stroke="#d97706" strokeWidth={1.5} dot={false} strokeDasharray="4 4" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      <Card className="border-primary/20 bg-primary/5">
        <CardContent className="space-y-1 p-4">
          <p className="text-xs font-semibold text-primary">{t("conviction.title")}</p>
          <p className="text-xs text-muted-foreground">{t("conviction.explain")}</p>
        </CardContent>
      </Card>
    </div>
  );
}
