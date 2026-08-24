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
import type { DictKey } from "@/i18n/dict";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  XAxis,
  YAxis,
} from "recharts";

const signed = (v: number) => `${v > 0 ? "+" : ""}${v.toFixed(2)}%`;

/**
 * Public-domain freight-activity equivalent of the (commercial, satellite)
 * TACO truck-count block — BTS Freight TSI monthly index + BLS-CES truck
 * employment auxiliary. Caliber degradation is DISCLOSED, never hidden:
 * the amber card says "not satellite data" in plain words.
 */
export function FreightProxySection() {
  const { t } = useI18n();
  const f = aionis.freightTaco;
  if (f?.status !== "ok") return null; // honest absence — no mock panel
  const te = f.truck_employment;

  const kpis: { label: DictKey; value: string; sub: string; tone: "amber" | "plain" }[] = [
    {
      label: "freight.latest_tsi",
      value: f.latest.tsi.toFixed(1),
      sub: f.latest.month,
      tone: "amber",
    },
    { label: "freight.mom", value: signed(f.latest.mom_pct), sub: "", tone: "plain" },
    { label: "freight.yoy", value: signed(f.latest.yoy_pct), sub: "", tone: "plain" },
    {
      label: "freight.truck_emp",
      value: te ? `${te.latest_k.toLocaleString()}k` : "—",
      sub: te ? `${te.latest_month} · ${signed(te.yoy_pct)} YoY` : t("freight.gap"),
      tone: "plain",
    },
  ];

  return (
    <section className="space-y-6">
      <header>
        <h2 className="text-lg font-semibold tracking-tight">{t("freight.title")}</h2>
        <p className="text-sm text-muted-foreground">{t("freight.subtitle")}</p>
      </header>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {kpis.map((k) => (
          <Card key={k.label}>
            <CardContent className="p-4">
              <p className="text-xs text-muted-foreground">{t(k.label)}</p>
              <p
                className={cn(
                  "mt-1 text-2xl font-bold tabular-nums",
                  k.tone === "amber" && "text-amber-600 dark:text-amber-400",
                )}
                title={k.label === "freight.truck_emp" && te ? te.title : undefined}
              >
                {k.value}
              </p>
              {k.sub && <p className="mt-0.5 text-xs text-muted-foreground">{k.sub}</p>}
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader className="border-b">
          <CardTitle className="text-base">{t("freight.series.title")}</CardTitle>
          <CardDescription>
            {t("freight.history.label")}: {f.history.n_months_total}{" "}
            {t("freight.history.months")} ({f.history.first_month} →)
          </CardDescription>
        </CardHeader>
        <CardContent className="p-2">
          <div className="h-[280px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={f.series_24m} margin={{ top: 12, right: 20, bottom: 24, left: 12 }}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                <XAxis dataKey="month" minTickGap={24} className="text-xs" />
                <YAxis domain={["auto", "auto"]} className="text-xs" />
                <Tooltip
                  formatter={(v) => [Number(v).toFixed(1), t("freight.latest_tsi")]}
                  labelFormatter={(l) => String(l)}
                  contentStyle={{ fontSize: "12px" }}
                />
                <Bar dataKey="tsi" fill="#d97706" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      <Card className="border-amber-500/30 bg-amber-500/5">
        <CardContent className="space-y-1 p-4">
          <p className="text-xs font-semibold text-amber-700 dark:text-amber-400">
            {t("freight.degrade.title")}
          </p>
          <p className="text-xs text-muted-foreground">{t("freight.degrade.body")}</p>
          <p className="text-xs text-muted-foreground">{f.degradation.granularity_lost}</p>
          <p className="pt-1 font-mono text-[11px] text-muted-foreground">
            {f.license} · {f.source}
          </p>
        </CardContent>
      </Card>
    </section>
  );
}
