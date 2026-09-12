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
import { ArgumentChainDiagram } from "./argument-chain-diagram";
import { NewsSentimentCard } from "./news-sentiment-card";
import { CoverageMap } from "@/components/ai/coverage-map";
import { SegmentHeader } from "@/components/segment-header";
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
// α redesign: each theme (former "seven-theme") declares its argument role, so
// the card reads as a segment of the validity-argument chain rather than a
// legacy status card. Mirrors the segment vocabulary in argument-chain-diagram.
type ThemeRoleKey =
  | "theme.role.context"
  | "theme.role.evidence"
  | "theme.role.corroboration"
  | "theme.role.verdict";
const THEME_ROLE: Record<string, ThemeRoleKey> = {
  price: "theme.role.evidence",
  macro: "theme.role.context",
  fundamentals: "theme.role.evidence",
  news_sentiment: "theme.role.corroboration",
  risk: "theme.role.evidence",
  net_cost: "theme.role.verdict",
  market_structure: "theme.role.evidence",
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

type DirKey = "themes.direction.bullish" | "themes.direction.bearish" | "themes.direction.neutral";
const DIR_KEY: Record<string, DirKey> = {
  bullish: "themes.direction.bullish",
  bearish: "themes.direction.bearish",
  neutral: "themes.direction.neutral",
};
const DIR_STYLE: Record<string, string> = {
  bullish: "badge-up",
  bearish: "badge-down",
  neutral: "border-muted-foreground/30 bg-muted/40 text-muted-foreground",
};
const DIR_BAR: Record<string, string> = {
  bullish: "bg-up",
  bearish: "bg-down",
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
      // Owner directive: the theme cards were given a large page but the
      // sparkline was h-6 (tiny). Enlarge to h-12 so the trend reads at a
      // glance, matching the new card footprint. w-full keeps it responsive.
      className={cn("h-12 w-full", className)}
      preserveAspectRatio="none"
      aria-hidden
    >
      <polyline
        points={pts}
        fill="none"
        stroke="currentColor"
        strokeWidth={2}
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  );
}

export function ThemeCard({ theme }: { theme: Theme }) {
  const { t } = useI18n();
  // news_sentiment has its own family-anatomy card (directional KPI band +
  // amber tone area chart) — the generic KV-list + sparkline body below renders
  // a tone series as an unlabelled squiggle, which is what read as "not adapted
  // to the project" on /confirmation#news and /themes.
  if (theme.key === "news_sentiment") {
    return <NewsSentimentCard theme={theme} />;
  }
  const seriesVals = (theme.series ?? [])
    .map((s) => s.value)
    .filter((v): v is number => typeof v === "number");
  // α redesign: a theme card is an evidence/context SEGMENT card, not a legacy
  // "seven-theme" status card. The badge declares the argument role (evidence/
  // context/corroboration/verdict) so the card reads as part of the chain, and
  // provenance (as_of) replaces the generic live/partial status.
  const roleKey = THEME_ROLE[theme.key] ?? "theme.role.evidence";
  return (
    <Card className="overflow-hidden py-0">
      <CardHeader className="gap-2 border-b p-5">
        <div className="flex items-center justify-between gap-2">
          <CardTitle className="text-base">{t(THEME_LABEL[theme.key] ?? "themes.risk")}</CardTitle>
          <Badge variant="outline" className="shrink-0 px-2 py-0.5 text-xs font-normal text-muted-foreground">
            {t(roleKey)}
          </Badge>
        </div>
        {theme.headline ? <CardDescription className="text-xs">{theme.headline}</CardDescription> : null}
        {theme.as_of ? (
          <p className="font-mono text-xs text-muted-foreground">
            {t("themes.as_of")} {theme.as_of}
          </p>
        ) : null}
      </CardHeader>
      <CardContent className="p-5">
        {(theme.signals ?? []).length > 0 ? (
          <div className="space-y-2.5">
            {(theme.signals ?? []).map((s) => (
              <div key={s.name} className="flex items-center justify-between gap-2">
                <span className="min-w-0 flex-1 truncate text-sm text-muted-foreground">
                  {SIGNAL_LABEL[s.name] ? t(SIGNAL_LABEL[s.name]) : s.name}
                </span>
                <span className="shrink-0 font-mono text-sm font-medium tabular-nums">
                  {s.value === null || s.value === undefined ? "—" : s.value}
                </span>
              </div>
            ))}
            {seriesVals.length >= 2 ? (
              <div className="pt-1">
                <Sparkline className="text-muted-foreground/60" data={seriesVals} />
              </div>
            ) : null}
          </div>
        ) : (
          <p className="text-sm italic text-muted-foreground">{t("themes.awaiting")}</p>
        )}
      </CardContent>
    </Card>
  );
}

export function ThemesView() {
  const { t } = useI18n();
  const th = aionis.themes;
  const ts = aionis.themeSignals;
  const sigs = ts.signals ?? {};
  const sigEntries = Object.values(sigs);
  const sigsByGroup = (g: string) => sigEntries.filter((s) => s.group === g);

  return (
    <div className="flex flex-col gap-4">
      <SegmentHeader segment="verdict" introKey="themes.role" />
      <header>
        <h1 className="text-2xl font-semibold tracking-[-0.032em]">{t("themes.title")}</h1>
        <p className="mt-2 text-[13px] text-mute">
          {th.freshness?.mixed
            ? `${t("themes.asof")} ${th.freshness.earliest} → ${th.freshness.latest} · ${t("themes.freshness.mixed")}`
            : th.as_of_date
              ? `${t("themes.asof")} ${th.as_of_date}`
              : t("themes.window")}
        </p>
      </header>

      <ArgumentChainDiagram />

      <CoverageMap />

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
                            className={cn("shrink-0 px-1.5 py-0 text-xs", DIR_STYLE[s.direction] ?? "")}
                          >
                            {t(DIR_KEY[s.direction] ?? "themes.direction.neutral")}
                          </Badge>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="w-8 shrink-0 text-xs text-muted-foreground">
                            {t("themes.strength")}
                          </span>
                          <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-muted">
                            {s.strength !== null && (
                              <div
                                className={cn("h-full rounded-full", DIR_BAR[s.direction] ?? DIR_BAR.neutral)}
                                style={{ width: `${Math.min((s.strength / 3) * 100, 100)}%` }}
                              />
                            )}
                          </div>
                          <span className="w-8 shrink-0 text-right text-xs tabular-nums text-muted-foreground">
                            {s.strength === null ? "—" : s.strength.toFixed(2)}
                          </span>
                        </div>
                        {s.favored.length > 0 ? (
                          <div className="flex flex-wrap gap-1">
                            <span className="text-xs text-muted-foreground">{t("themes.favored")}:</span>
                            {s.favored.slice(0, 4).map((f) => (
                              <span
                                key={f.ticker}
                                className="rounded bg-muted/60 px-1.5 py-0.5 font-mono text-xs"
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
          <p className="text-xs text-muted-foreground">{t("themes.favored.note")}</p>
        </section>
      ) : null}

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
