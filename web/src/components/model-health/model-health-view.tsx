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
import { ShieldAlertIcon, ShieldCheckIcon } from "lucide-react";

const REGIME_STYLE: Record<string, string> = {
  stable: "border-emerald-500/40 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400",
  moderate: "border-amber-500/40 bg-amber-500/10 text-amber-700 dark:text-amber-400",
  significant: "border-rose-500/40 bg-rose-500/10 text-rose-700 dark:text-rose-400",
};

// Literal-keyed so the strict `t(key)` union accepts it (template literals won't).
type RegimeLabelKey =
  | "modelhealth.regime.stable"
  | "modelhealth.regime.moderate"
  | "modelhealth.regime.significant";
const REGIME_LABEL: Record<string, RegimeLabelKey> = {
  stable: "modelhealth.regime.stable",
  moderate: "modelhealth.regime.moderate",
  significant: "modelhealth.regime.significant",
};

function Stat({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div title={hint}>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 text-xl font-bold tabular-nums">{value}</p>
    </div>
  );
}

export function ModelHealthView() {
  const { t } = useI18n();
  const mh = aionis.modelHealth;
  const regions = Object.values(mh.regions ?? {});

  return (
    <div className="space-y-6 p-4 md:p-6">
      <p className="text-xs font-medium text-primary">{t("modelhealth.role")}</p>
      <header className="space-y-1">
        <h1 className="text-2xl font-bold tracking-tight" title={t("modelhealth.termHint")}>{t("modelhealth.title")}</h1>
        <p className="text-sm text-muted-foreground">{t("modelhealth.window")}</p>
      </header>

      {mh.status !== "ok" || regions.length === 0 ? (
        <Card className="border-amber-500/30 bg-amber-500/5">
          <CardContent className="p-4 text-sm text-muted-foreground">
            {t("modelhealth.awaiting")}
          </CardContent>
        </Card>
      ) : (
        regions.map((r) => (
          <Card key={r.region} className="overflow-hidden py-0">
            <CardHeader className="border-b">
              <CardTitle className="flex items-center justify-between text-base">
                <span className="font-mono uppercase">{r.region}</span>
                <Badge variant="outline" className={cn(REGIME_STYLE[r.regime] ?? "")}>
                  {t(REGIME_LABEL[r.regime] ?? "modelhealth.regime.moderate")}
                </Badge>
              </CardTitle>
              <CardDescription>
                {t("modelhealth.regimehint")} · <span title={t("modelhealth.psiTermHint")}>PSI = {r.psi.toFixed(3)}</span> · <span title={t("modelhealth.nRecentHint")}>n<sub>recent</sub> {r.n_recent}</span> / <span title={t("modelhealth.nHistoryHint")}>n<sub>hist</sub> {r.n_history}</span>
              </CardDescription>
            </CardHeader>
            <CardContent className="grid grid-cols-2 gap-3 p-4 md:grid-cols-4">
              <Stat label={t("modelhealth.psi")} value={r.psi.toFixed(3)} hint={t("modelhealth.psiTermHint")} />
              <Stat label={t("modelhealth.icrecent")} value={r.ic_recent.toFixed(3)} hint={t("modelhealth.icTermHint")} />
              <Stat label={t("modelhealth.icfull")} value={r.ic_full.toFixed(3)} hint={t("modelhealth.icTermHint")} />
              <Stat
                label={t("modelhealth.baserate")}
                value={`${r.base_rate_full.toFixed(2)}→${r.base_rate_recent.toFixed(2)}`}
                hint={t("modelhealth.baseRateTermHint")}
              />
            </CardContent>
          </Card>
        ))
      )}

      <Card className="border-dashed">
        <CardHeader className="border-b">
          <CardTitle className="flex items-center gap-2 text-base">
            <ShieldCheckIcon className="size-4" /> {t("modelhealth.howto")}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 p-4">
          <p className="text-xs text-muted-foreground">{mh.methodology}</p>
          <p className="flex items-center gap-1.5 text-xs text-amber-700 dark:text-amber-400">
            <ShieldAlertIcon className="size-3.5 shrink-0" />
            {t("modelhealth.disclaimer")}
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
