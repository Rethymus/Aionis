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
import { ProvenanceBadge } from "@/components/provenance-badge";
import {
  ActivityIcon,
  ClockIcon,
  CalendarClockIcon,
  LockIcon,
} from "lucide-react";

// Literal-keyed so the strict `t(key)` union accepts the dynamic panel keys
// (template literals won't typecheck — same pattern as model-health-view).
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

type Category = "daily" | "cadence" | "frozen";

const CATEGORY_ORDER: Category[] = ["daily", "cadence", "frozen"];

const CATEGORY_STYLE: Record<Category, string> = {
  daily: "border-emerald-500/40 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400",
  cadence: "border-amber-500/40 bg-amber-500/10 text-amber-700 dark:text-amber-400",
  frozen: "border-slate-500/40 bg-slate-500/10 text-slate-700 dark:text-slate-300",
};

const CATEGORY_ICON: Record<Category, React.ReactNode> = {
  daily: <ClockIcon className="size-3.5" />,
  cadence: <CalendarClockIcon className="size-3.5" />,
  frozen: <LockIcon className="size-3.5" />,
};

type CategoryNameKey =
  | "datahealth.cat.daily"
  | "datahealth.cat.cadence"
  | "datahealth.cat.frozen";
const CATEGORY_NAME: Record<Category, CategoryNameKey> = {
  daily: "datahealth.cat.daily",
  cadence: "datahealth.cat.cadence",
  frozen: "datahealth.cat.frozen",
};

type CategoryNoteKey =
  | "datahealth.note.daily"
  | "datahealth.note.cadence"
  | "datahealth.note.frozen";
const CATEGORY_NOTE: Record<Category, CategoryNoteKey> = {
  daily: "datahealth.note.daily",
  cadence: "datahealth.note.cadence",
  frozen: "datahealth.note.frozen",
};

function Kpi({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex flex-col gap-1 rounded-lg border bg-card p-4">
      <span className="text-2xl font-bold tabular-nums">{value}</span>
      <span className="text-xs text-muted-foreground">{label}</span>
    </div>
  );
}

export function DataHealthView() {
  const { t } = useI18n();
  const dh = aionis.dataHealth;

  const byCategory = (cat: Category) =>
    dh.panels.filter((p) => p.category === cat);

  return (
    <div className="space-y-6 p-4 md:p-6">
      <p className="text-xs font-medium text-primary">{t("datahealth.role")}</p>
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1">
          <h1 className="text-2xl font-bold tracking-tight">
            {t("datahealth.title")}
          </h1>
          <p className="max-w-2xl text-sm text-muted-foreground">
            {t("datahealth.intro")}
          </p>
        </div>
        <ProvenanceBadge ts={dh.snapshot_ts} />
      </header>

      <div className="grid grid-cols-3 gap-3">
        <Kpi label={t("datahealth.cat.daily")} value={dh.summary.n_daily} />
        <Kpi label={t("datahealth.cat.cadence")} value={dh.summary.n_cadence} />
        <Kpi label={t("datahealth.cat.frozen")} value={dh.summary.n_frozen} />
      </div>

      {dh.source_health ? (
        <Card className="py-0">
          <CardHeader className="border-b">
            <CardTitle className="flex items-center gap-2 text-base">
              <ActivityIcon className="size-4 text-muted-foreground" />
              {t("datahealth.sourcehealth.title")}
            </CardTitle>
            <CardDescription>{t("datahealth.sourcehealth.note")}</CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            <div className="divide-y">
              <div className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3 px-4 py-2.5 text-sm">
                <span>{t("datahealth.panel.smart_money")}</span>
                <span className="font-mono text-xs tabular-nums text-muted-foreground">
                  {t("datahealth.sourcehealth.sm")
                    .replace("{null}", String(dh.source_health.smart_money.ticker_null))
                    .replace("{n}", String(dh.source_health.smart_money.n_recent))
                    .replace("{days}", String(dh.source_health.smart_money.days_since_latest))}
                </span>
              </div>
              <div className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3 px-4 py-2.5 text-sm">
                <span>{t("datahealth.panel.reddit")}</span>
                <span className="font-mono text-xs tabular-nums text-muted-foreground">
                  {t("datahealth.sourcehealth.reddit")
                    .replace("{null}", String(dh.source_health.reddit.bull_ratio_null))
                    .replace("{n}", String(dh.source_health.reddit.n_picks))}
                </span>
              </div>
              <div className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3 px-4 py-2.5 text-sm">
                <span>{t("datahealth.panel.cot")}</span>
                <span className="font-mono text-xs tabular-nums text-muted-foreground">
                  {t("datahealth.sourcehealth.cot").replace(
                    "{weeks}",
                    String(dh.source_health.cot.weeks_since_latest),
                  )}
                </span>
              </div>
            </div>
          </CardContent>
        </Card>
      ) : null}

      {dh.planned && dh.planned.length > 0 ? (
        <Card className="py-0 border-dashed">
          <CardHeader className="border-b">
            <CardTitle className="flex items-center gap-2 text-base">
              <CalendarClockIcon className="size-4 text-muted-foreground" />
              {t("datahealth.planned.title")}
              <Badge variant="outline" className="text-xs font-normal text-muted-foreground">
                {dh.planned.length}
              </Badge>
            </CardTitle>
            <CardDescription>{t("datahealth.planned.note")}</CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            <div className="divide-y">
              {dh.planned.map((p) => (
                <div key={p.key} className="grid grid-cols-[minmax(0,1fr)_minmax(0,2fr)] gap-3 px-4 py-2.5">
                  <span className="font-mono text-sm">{p.key}</span>
                  <span className="text-xs leading-relaxed text-muted-foreground">{p.note}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      ) : null}

      {CATEGORY_ORDER.map((cat) => {
        const rows = byCategory(cat);
        if (rows.length === 0) return null;
        return (
          <Card key={cat} className="py-0">
            <CardHeader className="border-b">
              <CardTitle className="flex items-center gap-2 text-base">
                <span className={cn("inline-flex rounded-md border p-1", CATEGORY_STYLE[cat])}>
                  {CATEGORY_ICON[cat]}
                </span>
                {t(CATEGORY_NAME[cat])}
                <span className="text-sm font-normal text-muted-foreground">
                  {rows.length}
                </span>
              </CardTitle>
              <CardDescription className="leading-relaxed">
                {t(CATEGORY_NOTE[cat])}
              </CardDescription>
            </CardHeader>
            <CardContent className="p-0">
              <div className="divide-y">
                {rows.map((p) => {
                  const labelKey = PANEL_LABELS[p.key];
                  return (
                    <div
                      key={p.key}
                      className="grid grid-cols-[minmax(0,1fr)_auto_auto] items-center gap-3 px-4 py-2.5"
                    >
                      <div className="min-w-0">
                        <p className="truncate text-sm font-medium">
                          {labelKey ? t(labelKey) : p.key}
                          {!p.present && (
                            <span className="ml-2 text-xs italic text-amber-600 dark:text-amber-400">
                              {t("datahealth.notpresent")}
                            </span>
                          )}
                        </p>
                        <p className="truncate font-mono text-xs text-muted-foreground">
                          {p.file}
                        </p>
                      </div>
                      <span
                        className="font-mono text-xs tabular-nums text-muted-foreground"
                        title={t("datahealth.col.asof")}
                      >
                        {p.as_of ?? "—"}
                      </span>
                      <span
                        className="w-24 text-right font-mono text-xs tabular-nums text-muted-foreground/70"
                        title={t("datahealth.col.exported")}
                      >
                        {p.exported_at ?? "—"}
                      </span>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        );
      })}

      <Card className="border-muted">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-sm">
            <ActivityIcon className="size-4 text-muted-foreground" />
            {t("datahealth.methodology.title")}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="font-mono text-xs leading-relaxed text-muted-foreground">
            {dh.methodology}
          </p>
          <div className="mt-3">
            <Badge variant="outline" className={cn("gap-1", CATEGORY_STYLE.frozen)}>
              {t("datahealth.cat.frozen")}
            </Badge>
            <span className="ml-2 text-xs text-muted-foreground">
              {t("datahealth.note.frozen.short")}
            </span>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
