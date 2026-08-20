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
import { aionis, type ApiCatalogEndpoint } from "@/data/aionis";
import { ProvenanceBadge } from "@/components/provenance-badge";
import { TerminalIcon, ExternalLinkIcon, ShieldAlertIcon } from "lucide-react";

// Literal-keyed panel names (shared with the data-health view).
type PanelLabelKey =
  | "datahealth.panel.metrics"
  | "datahealth.panel.picks"
  | "datahealth.panel.shorts"
  | "datahealth.panel.picks_meta"
  | "datahealth.panel.sector_breakdown"
  | "datahealth.panel.picks_backtest"
  | "datahealth.panel.ic_monthly"
  | "datahealth.panel.pick_conviction"
  | "datahealth.panel.model_health"
  | "datahealth.panel.calibration_reliability"
  | "datahealth.panel.power_floor"
  | "datahealth.panel.sigma_survey"
  | "datahealth.panel.bps_sweep"
  | "datahealth.panel.evidence"
  | "datahealth.panel.stock_universe"
  | "datahealth.panel.themes"
  | "datahealth.panel.theme_signals"
  | "datahealth.panel.market_context"
  | "datahealth.panel.macro_drivers"
  | "datahealth.panel.taco"
  | "datahealth.panel.form4"
  | "datahealth.panel.reddit"
  | "datahealth.panel.headline_provenance"
  | "datahealth.panel.ledger_audit"
  | "datahealth.panel.cot"
  | "datahealth.panel.smart_money";

const PANEL_LABELS: Record<string, PanelLabelKey> = {
  metrics: "datahealth.panel.metrics",
  picks: "datahealth.panel.picks",
  shorts: "datahealth.panel.shorts",
  picks_meta: "datahealth.panel.picks_meta",
  sector_breakdown: "datahealth.panel.sector_breakdown",
  picks_backtest: "datahealth.panel.picks_backtest",
  ic_monthly: "datahealth.panel.ic_monthly",
  pick_conviction: "datahealth.panel.pick_conviction",
  model_health: "datahealth.panel.model_health",
  calibration_reliability: "datahealth.panel.calibration_reliability",
  power_floor: "datahealth.panel.power_floor",
  sigma_survey: "datahealth.panel.sigma_survey",
  bps_sweep: "datahealth.panel.bps_sweep",
  evidence: "datahealth.panel.evidence",
  stock_universe: "datahealth.panel.stock_universe",
  themes: "datahealth.panel.themes",
  theme_signals: "datahealth.panel.theme_signals",
  market_context: "datahealth.panel.market_context",
  macro_drivers: "datahealth.panel.macro_drivers",
  taco: "datahealth.panel.taco",
  form4: "datahealth.panel.form4",
  reddit: "datahealth.panel.reddit",
  headline_provenance: "datahealth.panel.headline_provenance",
  ledger_audit: "datahealth.panel.ledger_audit",
  cot: "datahealth.panel.cot",
  smart_money: "datahealth.panel.smart_money",
};

type Freshness = "daily" | "cadence" | "frozen" | "planned";

const FRESHNESS_STYLE: Record<Freshness, string> = {
  daily: "border-emerald-500/40 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400",
  cadence: "border-amber-500/40 bg-amber-500/10 text-amber-700 dark:text-amber-400",
  frozen: "border-slate-500/40 bg-slate-500/10 text-slate-700 dark:text-slate-300",
  planned: "border-dashed border-muted-foreground/40 text-muted-foreground",
};

type FreshnessKey =
  | "datahealth.cat.daily"
  | "datahealth.cat.cadence"
  | "datahealth.cat.frozen"
  | "apidocs.cat.planned";
const FRESHNESS_LABEL: Record<Freshness, FreshnessKey> = {
  daily: "datahealth.cat.daily",
  cadence: "datahealth.cat.cadence",
  frozen: "datahealth.cat.frozen",
  planned: "apidocs.cat.planned",
};

function Code({ children }: { children: React.ReactNode }) {
  return (
    <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs">{children}</code>
  );
}

const ROOT_ENDPOINTS = [
  { path: "/api/v1/catalog.json", descKey: "apidocs.ep.catalog" },
  { path: "/api/v1/health.json", descKey: "apidocs.ep.health" },
  { path: "/api/v1/openapi.json", descKey: "apidocs.ep.openapi" },
  { path: "/api/v1/panels/{key}.json", descKey: "apidocs.ep.panels" },
] as const;

export function ApiDocsView() {
  const { t } = useI18n();
  const cat = aionis.apiCatalog;

  return (
    <div className="space-y-6 p-4 md:p-6">
      <p className="text-xs font-medium text-primary">{t("apidocs.role")}</p>
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1">
          <h1 className="text-2xl font-bold tracking-tight">{t("apidocs.title")}</h1>
          <p className="max-w-2xl text-sm text-muted-foreground">{t("apidocs.intro")}</p>
        </div>
        <ProvenanceBadge ts={cat.snapshot_ts} />
      </header>

      <Card className="py-0">
        <CardHeader className="border-b">
          <CardTitle className="flex items-center gap-2 text-base">
            <TerminalIcon className="size-4 text-muted-foreground" />
            {t("apidocs.endpoints.title")}
          </CardTitle>
          <CardDescription>{cat.base_note}</CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          <div className="divide-y">
            {ROOT_ENDPOINTS.map((e) => (
              <div key={e.path} className="flex flex-wrap items-center gap-x-3 gap-y-1 px-4 py-2.5">
                <Badge variant="outline" className="font-mono text-xs">GET</Badge>
                <a
                  href={`/Aionis${e.path === "/api/v1/panels/{key}.json" ? "/api/v1/catalog.json" : e.path}`}
                  target="_blank"
                  rel="noreferrer"
                  className="font-mono text-xs text-primary hover:underline"
                >
                  {e.path}
                </a>
                <span className="min-w-0 flex-1 text-xs text-muted-foreground">{t(e.descKey)}</span>
                <ExternalLinkIcon className="size-3 text-muted-foreground/50" />
              </div>
            ))}
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1 px-4 py-2.5">
              <Badge variant="outline" className="font-mono text-xs">GET</Badge>
              <span className="font-mono text-xs">{cat.live_prices.server}/api/prices/{"{us|cn}"}?tickers=…</span>
              <span className="min-w-0 flex-1 text-xs text-muted-foreground">
                {t("apidocs.ep.prices")}
              </span>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card className="py-0">
        <CardHeader className="border-b">
          <CardTitle className="text-base">{t("apidocs.panels.title")}</CardTitle>
          <CardDescription>{t("apidocs.panels.note")}</CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          <div className="hidden md:grid grid-cols-[minmax(0,1.2fr)_auto_minmax(0,1.6fr)_minmax(0,1.4fr)] gap-3 border-b bg-muted/40 px-4 py-2 text-xs font-medium text-muted-foreground">
            <span>{t("apidocs.col.panel")}</span>
            <span>{t("apidocs.col.freshness")}</span>
            <span>{t("apidocs.col.license")}</span>
            <span>{t("apidocs.col.source")}</span>
          </div>
          <div className="divide-y">
            {cat.endpoints.map((e: ApiCatalogEndpoint) => {
              const labelKey = PANEL_LABELS[e.key];
              const planned = e.status !== "available" || e.freshness === "planned";
              return (
                <div
                  key={e.key}
                  className="grid gap-x-3 gap-y-1 px-4 py-2.5 md:grid-cols-[minmax(0,1.2fr)_auto_minmax(0,1.6fr)_minmax(0,1.4fr)] md:items-center"
                >
                  <div className="min-w-0">
                    {planned ? (
                      <span className="truncate text-sm font-medium text-muted-foreground italic">
                        {labelKey ? t(labelKey) : e.key}
                      </span>
                    ) : (
                      <a
                        href={`/Aionis${e.path}`}
                        target="_blank"
                        rel="noreferrer"
                        className="truncate text-sm font-medium text-primary hover:underline"
                      >
                        {labelKey ? t(labelKey) : e.key}
                      </a>
                    )}
                    <p className="truncate font-mono text-xs text-muted-foreground">{e.path}</p>
                  </div>
                  <span className="flex items-center gap-1.5">
                    <Badge variant="outline" className={cn("gap-1 text-xs font-normal", FRESHNESS_STYLE[e.freshness])}>
                      {t(FRESHNESS_LABEL[e.freshness])}
                    </Badge>
                    {e.as_of ? (
                      <span className="font-mono text-xs text-muted-foreground">{e.as_of}</span>
                    ) : null}
                  </span>
                  <span className="text-xs text-muted-foreground">{e.license}</span>
                  <span className="text-xs text-muted-foreground/80">{e.source}</span>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-4 md:grid-cols-2">
        <Card className="py-0">
          <CardHeader className="border-b">
            <CardTitle className="text-base">{t("apidocs.usage.title")}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 p-4">
            <p className="text-xs text-muted-foreground">{t("apidocs.usage.note")}</p>
            <pre className="overflow-x-auto rounded-md bg-muted p-3 font-mono text-xs leading-relaxed">
{`curl https://rethymus.github.io/Aionis/api/v1/catalog.json

curl https://rethymus.github.io/Aionis/api/v1/panels/cot.json

fetch("/Aionis/api/v1/panels/themes.json")
  .then(r => r.json())`}
            </pre>
          </CardContent>
        </Card>

        <Card className="border-amber-500/30 bg-amber-500/5">
          <CardHeader className="border-b">
            <CardTitle className="flex items-center gap-2 text-base">
              <ShieldAlertIcon className="size-4 text-amber-600 dark:text-amber-400" />
              {t("apidocs.boundary.title")}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 p-4">
            <p className="text-xs leading-relaxed text-muted-foreground">{cat.methodology}</p>
            <p className="text-xs leading-relaxed text-muted-foreground">{cat.live_prices.note}</p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
