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
import { ThemesFunnel } from "./themes-funnel";
import { ShieldCheckIcon } from "lucide-react";

// Literal-keyed maps so the strict `t(key)` union accepts them (template
// literals like `themes.${key}` are not assignable to the dict key union).
type ThemeLabelKey =
  | "themes.price"
  | "themes.macro"
  | "themes.fundamentals"
  | "themes.news_sentiment"
  | "themes.risk"
  | "themes.net_cost"
  | "themes.market_structure";
const THEME_LABEL: Record<string, ThemeLabelKey> = {
  price: "themes.price",
  macro: "themes.macro",
  fundamentals: "themes.fundamentals",
  news_sentiment: "themes.news_sentiment",
  risk: "themes.risk",
  net_cost: "themes.net_cost",
  market_structure: "themes.market_structure",
};
// Professional term + plain gloss for each signal name (owner directive:
// terminology allowed, but every term carries a simple explanation).
type SignalLabelKey =
  | "themes.signal.momentum_21d"
  | "themes.signal.volatility_63d"
  | "themes.signal.beta_252d"
  | "themes.signal.reversal_5d"
  | "themes.signal.macro_regime"
  | "themes.signal.roe"
  | "themes.signal.profit_margin"
  | "themes.signal.revenue_growth_12m"
  | "themes.signal.leverage"
  | "themes.signal.downside_beta"
  | "themes.signal.idiosyncratic_volatility"
  | "themes.signal.return_skewness"
  | "themes.signal.worst_day_drawdown"
  | "themes.signal.net_sharpe_bps5"
  | "themes.signal.gross_sharpe"
  | "themes.signal.avg_turnover"
  | "themes.signal.amihud_illiquidity_21d"
  | "themes.signal.tone_latest"
  | "themes.signal.tone_mean"
  | "themes.signal.tone_min"
  | "themes.signal.volume_latest"
  | "themes.signal.n_months"
  | "themes.signal.rsi_21d"
  | "themes.signal.timetohigh_63d";
const SIGNAL_LABEL: Record<string, SignalLabelKey> = {
  momentum_21d: "themes.signal.momentum_21d",
  volatility_63d: "themes.signal.volatility_63d",
  beta_252d: "themes.signal.beta_252d",
  reversal_5d: "themes.signal.reversal_5d",
  macro_regime: "themes.signal.macro_regime",
  roe: "themes.signal.roe",
  profit_margin: "themes.signal.profit_margin",
  revenue_growth_12m: "themes.signal.revenue_growth_12m",
  leverage: "themes.signal.leverage",
  downside_beta: "themes.signal.downside_beta",
  idiosyncratic_volatility: "themes.signal.idiosyncratic_volatility",
  return_skewness: "themes.signal.return_skewness",
  worst_day_drawdown: "themes.signal.worst_day_drawdown",
  net_sharpe_bps5: "themes.signal.net_sharpe_bps5",
  gross_sharpe: "themes.signal.gross_sharpe",
  avg_turnover: "themes.signal.avg_turnover",
  amihud_illiquidity_21d: "themes.signal.amihud_illiquidity_21d",
  tone_latest: "themes.signal.tone_latest",
  tone_mean: "themes.signal.tone_mean",
  tone_min: "themes.signal.tone_min",
  volume_latest: "themes.signal.volume_latest",
  n_months: "themes.signal.n_months",
  rsi_21d: "themes.signal.rsi_21d",
  timetohigh_63d: "themes.signal.timetohigh_63d",
};
const GROUP_LABEL: Record<string, ThemeLabelKey> = {
  price: "themes.price",
  fundamentals: "themes.fundamentals",
  market_structure: "themes.market_structure",
};

// Funnel-layer membership for the 7 themes (presentation grouping). The funnel
// overview component renders the full 5-layer architecture; this groups the
// cards under their in-panel layer so same-type data is shown together.
type FunnelLayer = "context" | "signals" | "cost";
const LAYER_KEYS: Record<FunnelLayer, string[]> = {
  context: ["macro"],
  signals: ["fundamentals", "price", "risk", "market_structure", "news_sentiment"],
  cost: ["net_cost"],
};
const LAYER_SECTION: Record<
  FunnelLayer,
  "themes.funnel.section.context" | "themes.funnel.section.signals" | "themes.funnel.section.cost"
> = {
  context: "themes.funnel.section.context",
  signals: "themes.funnel.section.signals",
  cost: "themes.funnel.section.cost",
};
const LAYER_ORDER: FunnelLayer[] = ["context", "signals", "cost"];

type StatusKey =
  | "themes.status.live"
  | "themes.status.partial"
  | "themes.status.forward_only"
  | "themes.status.needs_work";
const STATUS_KEY: Record<string, StatusKey> = {
  live: "themes.status.live",
  partial: "themes.status.partial",
  forward_only: "themes.status.forward_only",
  needs_work: "themes.status.needs_work",
};
const STATUS_STYLE: Record<string, string> = {
  live: "border-emerald-500/40 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400",
  partial: "border-amber-500/40 bg-amber-500/10 text-amber-700 dark:text-amber-400",
  forward_only: "border-muted-foreground/30 bg-muted/40 text-muted-foreground",
  needs_work: "border-rose-500/40 bg-rose-500/10 text-rose-700 dark:text-rose-400",
};

type DirKey = "themes.direction.bullish" | "themes.direction.bearish" | "themes.direction.neutral";
const DIR_KEY: Record<string, DirKey> = {
  bullish: "themes.direction.bullish",
  bearish: "themes.direction.bearish",
  neutral: "themes.direction.neutral",
};
const DIR_STYLE: Record<string, string> = {
  bullish: "border-emerald-500/40 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400",
  bearish: "border-rose-500/40 bg-rose-500/10 text-rose-700 dark:text-rose-400",
  neutral: "border-muted-foreground/30 bg-muted/40 text-muted-foreground",
};
const DIR_BAR: Record<string, string> = {
  bullish: "bg-emerald-500",
  bearish: "bg-rose-500",
  neutral: "bg-muted-foreground/40",
};

function Sparkline({ data, className }: { data: number[]; className?: string }) {
  if (data.length < 2) return null;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const w = 100;
  const h = 24;
  const pts = data
    .map((v, i) => `${(i / (data.length - 1)) * w},${h - ((v - min) / range) * h}`)
    .join(" ");
  return (
    <svg
      viewBox={`0 0 ${w} ${h}`}
      className={cn("h-6 w-full", className)}
      preserveAspectRatio="none"
      aria-hidden
    >
      <polyline
        points={pts}
        fill="none"
        stroke="currentColor"
        strokeWidth={1.5}
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  );
}

function ThemeCard({ theme }: { theme: { key: string; status: string; headline?: string; signals?: { name: string; value: number | null }[]; series?: { value: number }[] } }) {
  const { t } = useI18n();
  const seriesVals = (theme.series ?? [])
    .map((s) => s.value)
    .filter((v): v is number => typeof v === "number");
  return (
    <Card className="overflow-hidden py-0">
      <CardHeader className="border-b">
        <CardTitle className="flex items-center justify-between gap-2 text-base">
          <span>{t(THEME_LABEL[theme.key] ?? "themes.risk")}</span>
          <Badge
            variant="outline"
            className={cn(STATUS_STYLE[theme.status] ?? "", "shrink-0")}
          >
            {t(STATUS_KEY[theme.status] ?? "themes.status.needs_work")}
          </Badge>
        </CardTitle>
        {theme.headline ? <CardDescription>{theme.headline}</CardDescription> : null}
      </CardHeader>
      <CardContent className="p-4">
        {(theme.signals ?? []).length > 0 ? (
          <div className="space-y-2">
            {(theme.signals ?? []).map((s) => (
              <div key={s.name} className="flex items-center justify-between text-sm">
                <span className="truncate text-xs text-muted-foreground">
                  {SIGNAL_LABEL[s.name] ? t(SIGNAL_LABEL[s.name]) : s.name}
                </span>
                <span className="ml-2 shrink-0 tabular-nums font-medium">
                  {s.value === null || s.value === undefined ? "—" : s.value}
                </span>
              </div>
            ))}
            {seriesVals.length >= 2 ? (
              <Sparkline className="text-emerald-600 dark:text-emerald-400" data={seriesVals} />
            ) : null}
          </div>
        ) : (
          <p className="text-xs italic text-muted-foreground">{t("themes.awaiting")}</p>
        )}
      </CardContent>
    </Card>
  );
}

export function ThemesView() {
  const { t } = useI18n();
  const th = aionis.themes;
  const themes = th.themes ?? [];
  const ts = aionis.themeSignals;
  const sigs = ts.signals ?? {};
  const sigEntries = Object.values(sigs);
  const sigsByGroup = (g: string) => sigEntries.filter((s) => s.group === g);

  return (
    <div className="space-y-6 p-4 md:p-6">
      <p className="text-xs font-medium text-primary">{t("themes.role")}</p>
      <header className="space-y-1">
        <h1 className="text-2xl font-bold tracking-tight">{t("themes.title")}</h1>
        <p className="text-sm text-muted-foreground">
          {t("themes.window")}
          {th.as_of_date ? ` · ${t("themes.asof")} ${th.as_of_date}` : ""}
        </p>
      </header>

      <ThemesFunnel />

      {/* Operationalized signals: direction × strength × favored (the actionable read) */}
      {ts.status === "ok" && sigEntries.length > 0 ? (
        <section className="space-y-3">
          <div>
            <h2 className="text-lg font-semibold tracking-tight">{t("themes.signals.title")}</h2>
            <p className="text-xs text-muted-foreground">
              {t("themes.signals.hint")}
              {ts.as_of_date ? ` · ${ts.as_of_date}` : ""}
            </p>
          </div>
          <div className="grid gap-4 md:grid-cols-3">
            {ts.groups.map((g) => {
              const groupSigs = sigsByGroup(g);
              if (groupSigs.length === 0) return null;
              return (
                <Card key={g} className="overflow-hidden py-0">
                  <CardHeader className="border-b">
                    <CardTitle className="text-sm">{t(GROUP_LABEL[g] ?? "themes.price")}</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3 p-3">
                    {groupSigs.map((s) => (
                      <div key={s.signal} className="space-y-1.5">
                        <div className="flex items-center justify-between gap-2">
                          <span className="truncate font-mono text-xs">{s.signal}</span>
                          <Badge
                            variant="outline"
                            className={cn("shrink-0 px-1.5 py-0 text-[10px]", DIR_STYLE[s.direction] ?? "")}
                          >
                            {t(DIR_KEY[s.direction] ?? "themes.direction.neutral")}
                          </Badge>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="w-8 shrink-0 text-[10px] text-muted-foreground">
                            {t("themes.strength")}
                          </span>
                          <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-muted">
                            <div
                              className={cn("h-full rounded-full", DIR_BAR[s.direction] ?? DIR_BAR.neutral)}
                              style={{ width: `${Math.min((s.strength / 3) * 100, 100)}%` }}
                            />
                          </div>
                          <span className="w-8 shrink-0 text-right text-[10px] tabular-nums text-muted-foreground">
                            {s.strength.toFixed(2)}
                          </span>
                        </div>
                        {s.favored.length > 0 ? (
                          <div className="flex flex-wrap gap-1">
                            <span className="text-[10px] text-muted-foreground">{t("themes.favored")}:</span>
                            {s.favored.slice(0, 4).map((f) => (
                              <span
                                key={f.ticker}
                                className="rounded bg-muted/60 px-1.5 py-0.5 font-mono text-[10px]"
                                title={
                                  f.name
                                    ? `${f.name}${f.sector ? ` · ${f.sector}` : ""}`
                                    : f.ticker
                                }
                              >
                                {f.ticker}
                              </span>
                            ))}
                          </div>
                        ) : null}
                      </div>
                    ))}
                  </CardContent>
                </Card>
              );
            })}
          </div>
          <p className="text-[10px] text-muted-foreground">{t("themes.favored.note")}</p>
        </section>
      ) : null}

      {th.status !== "ok" || themes.length === 0 ? (
        <Card className="border-amber-500/30 bg-amber-500/5">
          <CardContent className="p-4 text-sm text-muted-foreground">
            {t("themes.awaiting")}
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-6">
          {LAYER_ORDER.map((layer) => {
            const layerThemes = themes.filter((theme) =>
              LAYER_KEYS[layer].includes(theme.key),
            );
            if (layerThemes.length === 0) return null;
            return (
              <section key={layer} className="space-y-3">
                <h3 className="text-sm font-semibold tracking-tight text-muted-foreground">
                  {t(LAYER_SECTION[layer])}
                </h3>
                <div className="grid gap-4 md:grid-cols-2">
                  {layerThemes.map((theme) => (
                    <ThemeCard key={theme.key} theme={theme} />
                  ))}
                </div>
              </section>
            );
          })}
        </div>
      )}

      <Card className="border-dashed">
        <CardHeader className="border-b">
          <CardTitle className="flex items-center gap-2 text-base">
            <ShieldCheckIcon className="size-4" /> {t("themes.methodology_title")}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 p-4">
          <p className="text-xs text-muted-foreground">{ts.methodology ?? th.methodology}</p>
        </CardContent>
      </Card>
    </div>
  );
}
