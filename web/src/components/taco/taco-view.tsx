"use client";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { fmtDateShort } from "@/lib/format";
import { useI18n } from "@/i18n/provider";
import { aionis } from "@/data/aionis";
import type { DictKey } from "@/i18n/dict";
import {
  Area,
  AreaChart,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { FreightProxySection } from "./freight-proxy-section";

// /taco — family anatomy: page head + count line, one compact stat band
// (their insider-page pattern), a 320px area-fill chart (their chart
// signature), and the events as a date-grouped stream (bg-soft headers,
// direction pills, mono meta) instead of a sparse table.

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
  const toneCls = {
    emerald: "text-up",
    rose: "text-down",
    amber: "text-amber-600 dark:text-amber-400",
  } as const;

  return (
    <div className="flex flex-col gap-4">
      <header>
        <h1 className="text-2xl font-semibold tracking-[-0.032em]">{t("taco.title")}</h1>
        <p className="mt-2 text-[13px] text-mute">
          {t("taco.subtitle")} · {data.length} VIX mo · {taco.events.length} events ·{" "}
          {data[0]?.month} → {data[data.length - 1]?.month}
        </p>
      </header>

      {/* Compact stat band (their single-card insider pattern). */}
      <div className="flex items-center justify-between gap-3 rounded-xl border border-line bg-card px-5 py-4">
        {kpis.map((k, i) => (
          <span key={k.label} className="flex items-center gap-3">
            {i > 0 ? <span className="h-4 w-px bg-line" aria-hidden /> : null}
            <span className="text-[12px] text-mute">{t(k.label)}</span>
            <span className={cn("font-mono text-[17px] leading-none font-bold tabular-nums", toneCls[k.tone])}>
              {k.value}
            </span>
            {k.label === "taco.latest_vix" && taco.latest_date ? (
              // A bare VIX number reads as "right now" — anchor it to the
              // monthly mean it actually is (panel advances monthly).
              <span className="font-mono text-[11px] tabular-nums text-faint">
                {taco.latest_date}
              </span>
            ) : null}
          </span>
        ))}
      </div>

      <Card className="py-0">
        <CardHeader className="border-b">
          <CardTitle className="text-base">VIX</CardTitle>
          <CardDescription>{t("taco.subtitle")}</CardDescription>
        </CardHeader>
        <CardContent className="p-2">
          <div className="h-[320px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={data} margin={{ top: 12, right: 20, bottom: 24, left: 12 }}>
                <defs>
                  <linearGradient id="vix-area" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#ff9300" stopOpacity={0.32} />
                    <stop offset="100%" stopColor="#ff9300" stopOpacity={0} />
                  </linearGradient>
                </defs>
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
                <Area
                  type="monotone"
                  dataKey="vix"
                  stroke="#ff9300"
                  strokeWidth={1.5}
                  fill="url(#vix-area)"
                  dot={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      {/* Events as a date-grouped stream (family anatomy). */}
      <div className="overflow-hidden rounded-xl border border-line bg-card">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 border-b border-line2 px-5 py-4">
          <h2 className="text-[17px] font-semibold tracking-[-0.02em]">
            {t("taco.events.title")}
          </h2>
          <span className="font-mono text-[11px] text-mute tabular-nums">
            {taco.events.length}
          </span>
        </div>
        {taco.events.map((e, i) => {
          const concession = e.type === "concession";
          const prev = i > 0 ? taco.events[i - 1] : null;
          const newDay = !prev || prev.date.slice(0, 7) !== e.date.slice(0, 7);
          return (
            <div key={e.date + e.label}>
              {newDay ? (
                <div className="border-t border-line2 bg-soft px-5 py-1.5 text-[11px] font-semibold text-mute first:border-t-0">
                  {e.date.slice(0, 7)}
                </div>
              ) : null}
              <div className="flex items-baseline gap-3 border-t border-line2 px-5 py-[10px] transition-colors hover:bg-soft">
                <span className="flex-none font-mono text-[12px] text-mute tabular-nums">
                  {fmtDateShort(e.date)}
                </span>
                <span
                  className={cn(
                    "flex-none rounded-full px-[10px] py-[3px] text-[12px] font-semibold",
                    concession ? "bg-brand-tint text-brand" : "bg-red-tint text-red",
                  )}
                >
                  {t(concession ? "taco.event.concession" : "taco.event.escalation")}
                </span>
                <span className="min-w-0 text-[13px] leading-relaxed text-ink">
                  {e.label}
                </span>
              </div>
            </div>
          );
        })}
      </div>

      <FreightProxySection />

      <Card className="border-amber-500/30 bg-amber-500/5 py-0">
        <CardContent className="space-y-1 px-5 py-4">
          <p className="text-[13px] font-semibold text-amber-700 dark:text-amber-400">
            {t("taco.methodology")}
          </p>
          <p className="text-[11px] leading-relaxed text-mute">{t("taco.methodology.body")}</p>
        </CardContent>
      </Card>
    </div>
  );
}
