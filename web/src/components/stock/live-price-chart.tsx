"use client";

/**
 * Live price tape chart for /stock/[ticker] — DISPLAY ONLY.
 *
 * ANTI-LEAKAGE BOUNDARY (CLAUDE.md "prices = DISPLAY ONLY"): everything this
 * component renders comes from the display-only Cloudflare Worker
 * (workers/prices/) via lib/live-prices.ts. It must NEVER be imported by any
 * research module (src/aionis/), never persisted, and never merged into any
 * panel JSON or gitignored data file. It is a terminal visual, not a signal.
 *
 * Honest data contract — the Worker exposes ONLY latest-quote endpoints
 * (/api/prices/us, /api/prices/cn; no intraday/history series exists on the
 * free tier), so this chart plots the CUMULATIVE SAMPLES taken since this page
 * was opened: one sample per successful hook fetch (~60s polling cadence,
 * subject to the Worker's edge-cache TTL). Reload resets the series — that is
 * the honest behavior, labeled as such in the UI. No history is fabricated.
 *
 * Degradation contract: if the Worker is unreachable / errors / returns no
 * quote, this component renders NOTHING (the header pill keeps its existing
 * degraded behavior). Never a full-page error state.
 *
 * Color: strictly the project --up/--down convention system (direction taken
 * from first-vs-last sample of THIS session's series); semantic palette
 * (emerald/rose) is never borrowed here. Numbers follow the page's existing
 * per-share convention (toFixed(2)); times are local 24h HH:MM.
 */

import { useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
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
import { type LivePrice, type PriceStatus } from "@/lib/live-prices";

/** Ring-buffer cap: ~4h of ~60s samples per visit. The samples counter labels
 *  what was collected since page open; with this cap they coincide for any
 *  realistic single visit, so the label stays honest. */
const MAX_SAMPLES = 240;

type Sample = { t: number; p: number };

function fmtClock(t: number): string {
  const d = new Date(t);
  return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

function ChartTooltip({ active, payload }: {
  active?: boolean;
  payload?: { payload?: Sample }[];
}) {
  if (!active || !payload?.length) return null;
  const s = payload[0]?.payload;
  if (!s) return null;
  return (
    <div className="rounded-md border bg-background p-2 text-xs shadow-sm">
      <div className="font-mono tabular-nums">{fmtClock(s.t)}</div>
      <div className="font-mono font-medium tabular-nums">${s.p.toFixed(2)}</div>
    </div>
  );
}

export function LivePriceChart({ region, quote, status, updatedAt }: {
  region: "us" | "cn";
  quote: LivePrice | undefined;
  status: PriceStatus;
  updatedAt: number | null;
}) {
  const { t } = useI18n();
  // Cumulative session series: one point per successful poll of the shared
  // live-prices hook (no second network loop is created here). Appending is a
  // render-phase state adjustment derived from the hook's fetch batches
  // (guarded by batch timestamp) — no effect, no cascading render.
  const [tape, setTape] = useState<{
    lastT: number | null;
    samples: Sample[];
  }>({ lastT: null, samples: [] });
  const px = quote?.price ?? null;
  if (px != null && updatedAt != null && tape.lastT !== updatedAt) {
    const next = [...tape.samples, { t: updatedAt, p: px }];
    setTape({
      lastT: updatedAt,
      samples: next.length > MAX_SAMPLES ? next.slice(-MAX_SAMPLES) : next,
    });
  }
  const samples = tape.samples;

  // Silent degrade: anything other than a healthy quote renders nothing and
  // leaves the header pill as the sole live-price surface.
  if (status !== "ok" || quote?.price == null) return null;

  const first = samples[0]?.p ?? null;
  const last = samples.at(-1)?.p ?? null;
  const rising = first !== null && last !== null && last > first;
  const falling = first !== null && last !== null && last < first;
  // Direction color from THIS session's series only; flat/too-few points stay
  // neutral. Strictly --up/--down — no semantic palette here.
  const lineVar = rising ? "var(--up)" : falling ? "var(--down)" : "var(--muted-foreground)";

  return (
    <Card className="py-0">
      <CardHeader className="border-b">
        <CardTitle className="flex flex-wrap items-center gap-2 text-base">
          {t("stock.live.chart.title")}
          <Badge variant="outline" className="px-1.5 py-0 font-mono text-[10px] font-normal">
            {t("stock.live.chart.badge")}
          </Badge>
        </CardTitle>
        <CardDescription className="font-mono text-xs">
          {t("stock.live.chart.note")}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3 p-4">
        <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
          <span className="font-mono text-2xl font-semibold tabular-nums">
            ${quote.price.toFixed(2)}
          </span>
          {quote.change_pct != null ? (
            <span
              className={cn(
                "font-mono text-sm font-medium tabular-nums",
                quote.change_pct >= 0 ? "text-up" : "text-down",
              )}
            >
              {quote.change_pct >= 0 ? "+" : ""}
              {quote.change_pct.toFixed(2)}%
            </span>
          ) : null}
          <span className="ml-auto font-mono text-xs tabular-nums text-muted-foreground">
            {t("stock.live.chart.samples.prefix")}
            {samples.length}
            {t("stock.live.chart.samples.suffix")}
          </span>
        </div>

        <div className="h-[160px] w-full">
          {samples.length < 2 ? (
            // Single-sample limbo: honest collecting state, stable card height.
            <div className="flex h-full items-center justify-center">
              <p className="text-xs italic text-muted-foreground">
                {t("stock.live.chart.collecting")}
              </p>
            </div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={samples} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
                <defs>
                  <linearGradient id="live-tape-area" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={lineVar} stopOpacity={0.25} />
                    <stop offset="100%" stopColor={lineVar} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis
                  dataKey="t"
                  type="number"
                  domain={["dataMin", "dataMax"]}
                  tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
                  tickFormatter={(tv: number) => fmtClock(tv)}
                  minTickGap={48}
                />
                <YAxis
                  domain={["auto", "auto"]}
                  width={64}
                  tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
                  tickFormatter={(v: number) => v.toFixed(2)}
                />
                <Tooltip content={<ChartTooltip />} />
                <Area
                  type="stepAfter"
                  dataKey="p"
                  stroke={lineVar}
                  strokeWidth={1.6}
                  fill="url(#live-tape-area)"
                  dot={false}
                  isAnimationActive={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </div>

        <p className="font-mono text-[11px] leading-relaxed text-muted-foreground/80">
          {region === "us"
            ? t("stock.live.chart.source.us")
            : t("stock.live.chart.source.cn")}
        </p>
      </CardContent>
    </Card>
  );
}
