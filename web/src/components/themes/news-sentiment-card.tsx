"use client";

import { useMemo } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { TrendingDown, TrendingUp } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { useI18n } from "@/i18n/provider";
import { type Theme } from "@/data/aionis";
import type { DictKey } from "@/i18n/dict";

/** The news_sentiment theme card — the GDELT tone panel in the project's own
 *  display language. The generic ThemeCard KV-list + gray sparkline rendered
 *  the tone series as an unlabelled squiggle and carried a permanently-0
 *  "article volume" signal; this card gives the panel the family anatomy its
 *  siblings (insider KPI band, TACO area chart) already speak: a compact
 *  directional stat band (text-up/text-down — swap-safe under the CN
 *  red-up/green-up convention), the monthly tone as an amber area chart with a
 *  dashed zero baseline (GDELT family accent), and an honest direction pill.
 *  Signals that are absent (or the historical volume=0 artifact) drop out
 *  instead of rendering a fake zero. */

const signed = (v: number) => `${v > 0 ? "+" : ""}${v.toFixed(2)}`;

function signalValue(theme: Theme, name: string): number | null {
  const s = (theme.signals ?? []).find((x) => x.name === name);
  return s && s.value !== null && s.value !== undefined ? Number(s.value) : null;
}

export function NewsSentimentCard({ theme }: { theme: Theme }) {
  const { t } = useI18n();
  const toneLatest = signalValue(theme, "tone_latest");
  const toneMean = signalValue(theme, "tone_mean");
  const toneMin = signalValue(theme, "tone_min");
  const volumeLatest = signalValue(theme, "volume_latest");
  const nMonths = signalValue(theme, "n_months");

  const data = useMemo(
    () =>
      (theme.series ?? [])
        .filter((r) => typeof r.value === "number")
        .map((r) => ({ month: r.month ?? r.date ?? "", value: r.value as number })),
    [theme.series],
  );

  const warm = (toneLatest ?? 0) >= 0;
  const kpis: {
    label: DictKey;
    gloss: DictKey;
    value: string;
    tone: "up" | "down" | "ink";
  }[] = [];
  if (toneLatest !== null)
    kpis.push({
      label: "themes.sentiment.tone_latest",
      gloss: "themes.signal.tone_latest",
      value: signed(toneLatest),
      tone: warm ? "up" : "down",
    });
  if (toneMean !== null)
    kpis.push({
      label: "themes.sentiment.tone_mean",
      gloss: "themes.signal.tone_mean",
      value: signed(toneMean),
      tone: toneMean >= 0 ? "up" : "down",
    });
  if (toneMin !== null)
    kpis.push({
      label: "themes.sentiment.tone_min",
      gloss: "themes.signal.tone_min",
      value: signed(toneMin),
      tone: "down",
    });
  if (volumeLatest !== null && volumeLatest > 0)
    kpis.push({
      label: "themes.sentiment.attention",
      gloss: "themes.signal.volume_latest",
      value: `${volumeLatest.toFixed(1)}/100`,
      tone: "ink",
    });
  if (nMonths !== null)
    kpis.push({
      label: "themes.sentiment.months",
      gloss: "themes.signal.n_months",
      value: String(Math.round(nMonths)),
      tone: "ink",
    });

  const toneCls = { up: "text-up", down: "text-down", ink: "text-ink" } as const;

  return (
    <Card className="overflow-hidden py-0">
      <div className="flex items-center justify-between gap-2 border-b border-line px-5 py-4">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <h2 className="text-[17px] font-semibold tracking-[-0.02em]">
              {t("themes.news_sentiment")}
            </h2>
            {toneLatest !== null ? (
              <span
                className={cn(
                  "inline-flex items-center gap-1 rounded-full bg-soft px-2.5 py-0.5 text-[12px] font-semibold",
                  warm ? "text-up" : "text-down",
                )}
              >
                {warm ? (
                  <TrendingUp className="size-3.5" aria-hidden />
                ) : (
                  <TrendingDown className="size-3.5" aria-hidden />
                )}
                {t(warm ? "themes.sentiment.warm" : "themes.sentiment.cold")}
              </span>
            ) : null}
          </div>
          {theme.headline ? (
            <p className="mt-1 text-[12px] leading-relaxed text-mute">{theme.headline}</p>
          ) : null}
        </div>
        <Badge
          variant="outline"
          className="shrink-0 border-line px-2 py-0.5 text-xs font-normal text-mute"
        >
          {t("theme.role.corroboration")}
        </Badge>
      </div>

      {kpis.length > 0 ? (
        <div className="flex flex-wrap items-center gap-x-3 gap-y-2 border-b border-line2 bg-card px-5 py-3">
          {kpis.map((k, i) => (
            <span key={k.label} className="flex items-center gap-2.5">
              {i > 0 ? <span className="h-4 w-px bg-line" aria-hidden /> : null}
              <span className="text-[12px] text-mute" title={t(k.gloss)}>
                {t(k.label)}
              </span>
              <span
                className={cn(
                  "font-mono text-[16px] font-bold leading-none tabular-nums",
                  toneCls[k.tone],
                )}
              >
                {k.value}
              </span>
            </span>
          ))}
          {theme.as_of ? (
            <span className="ml-auto font-mono text-[11px] tabular-nums text-faint">
              {t("themes.as_of")} {theme.as_of}
            </span>
          ) : null}
        </div>
      ) : (
        <CardContent className="p-5">
          <p className="text-sm italic text-mute">{t("themes.awaiting")}</p>
        </CardContent>
      )}

      {data.length >= 2 ? (
        <div className="p-2">
          <div className="h-[180px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={data} margin={{ top: 12, right: 20, bottom: 4, left: 0 }}>
                <defs>
                  <linearGradient id="news-tone-area" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#ff9300" stopOpacity={0.32} />
                    <stop offset="100%" stopColor="#ff9300" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                <XAxis
                  dataKey="month"
                  minTickGap={32}
                  tickFormatter={(v) => String(v).slice(2)}
                  className="text-xs"
                />
                <YAxis
                  tickFormatter={(v) => Number(v).toFixed(1)}
                  className="text-xs"
                  width={44}
                />
                <Tooltip
                  formatter={(v) => Number(v).toFixed(3)}
                  labelFormatter={(l) => String(l)}
                  contentStyle={{ fontSize: "12px" }}
                />
                <ReferenceLine y={0} stroke="currentColor" className="text-line2" strokeDasharray="4 4" />
                <Area
                  type="monotone"
                  dataKey="value"
                  stroke="#ff9300"
                  strokeWidth={1.5}
                  fill="url(#news-tone-area)"
                  dot={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
          <p className="px-3 pb-1 text-[11px] text-faint">{t("themes.sentiment.chart_note")}</p>
        </div>
      ) : null}

      <div className="border-t border-line2 px-5 py-3">
        <p className="font-mono text-[11px] leading-relaxed text-faint">
          {t("news.window")}
        </p>
      </div>
    </Card>
  );
}
