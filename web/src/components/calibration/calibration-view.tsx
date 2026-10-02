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
import { aionis, type CalibrationReliability } from "@/data/aionis";
import { HorizonRobustnessCard } from "@/components/calibration/horizon-robustness-card";
import dynamic from "next/dynamic";
import { LazyMount } from "@/components/ui/lazy-mount";
// Round 122: charts async-chunk (skeleton ≈ the two fixed chart heights);
// below-fold CN card + horizon card mount on approach.
const RegionCharts = dynamic(
  () => import("./calibration-charts").then(m => m.RegionCharts),
  {
    ssr: false,
    loading: () => (
      <div aria-hidden="true" style={{ minHeight: 420 }} className="w-full animate-pulse rounded-xl border border-line bg-soft/50" />
    ),
  },
);
import { ShieldAlertIcon, ShieldCheckIcon } from "lucide-react";

type RegionPayload = CalibrationReliability["regions"][string];
type ReliabilityPoint = { x: number; y: number; n: number };
type EcePoint = { month: string; ece: number };

function Stat({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 text-xl font-bold tabular-nums">{value}</p>
      {hint ? <p className="text-xs leading-tight text-muted-foreground">{hint}</p> : null}
    </div>
  );
}

// Lower ECE = better calibrated; color the pooled-ECE badge by quality band.
function eceBadgeClass(ece: number): string {
  if (ece <= 0.05) {
    return "border-emerald-500/40 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400";
  }
  if (ece <= 0.10) {
    return "border-amber-500/40 bg-amber-500/10 text-amber-700 dark:text-amber-400";
  }
  return "border-rose-500/40 bg-rose-500/10 text-rose-700 dark:text-rose-400";
}

function RegionCard({ region, payload }: { region: string; payload: RegionPayload }) {
  const { t } = useI18n();
  const last = payload.series.at(-1);
  if (!last) {
    return null;
  }
  const relPoints: ReliabilityPoint[] = payload.pooled_reliability
    .filter((b) => b.n > 0 && b.pred_mean != null && b.emp_freq != null)
    .map((b) => ({ x: b.pred_mean as number, y: b.emp_freq as number, n: b.n }));
  const eceSeries: EcePoint[] = payload.series.map((s) => ({ month: s.month, ece: s.ece_oos }));
  const xInterval = Math.max(0, Math.floor(eceSeries.length / 6));

  return (
    <Card className="overflow-hidden py-0">
      <CardHeader className="border-b">
        <CardTitle className="flex items-center justify-between text-base">
          <span className="font-mono uppercase">{region}</span>
          <Badge variant="outline" className={cn(eceBadgeClass(payload.pooled_ece))}>
            {t("calibration.pooledEce")} {payload.pooled_ece.toFixed(4)}
          </Badge>
        </CardTitle>
        <CardDescription>
          {t("calibration.reliabilityHint")} · {payload.n_months} {t("calibration.nMonthsUnit")}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-5 p-4">
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <Stat
            label={t("calibration.pooledEce")}
            value={payload.pooled_ece.toFixed(4)}
            hint={t("calibration.pooledEceHint")}
          />
          <Stat
            label={t("calibration.latestEce")}
            value={last.ece_oos.toFixed(4)}
            hint={t("calibration.latestEceHint")}
          />
          <Stat
            label={t("calibration.probRange")}
            value={`[${last.prob_min.toFixed(2)}, ${last.prob_max.toFixed(2)}]`}
            hint={t("calibration.probRangeHint")}
          />
          <Stat
            label={t("calibration.trainPairs")}
            value={last.n_train_pairs.toLocaleString()}
            hint={t("calibration.trainPairsHint")}
          />
        </div>

        <RegionCharts
          relPoints={relPoints}
          eceSeries={eceSeries}
          xInterval={xInterval}
        />
      </CardContent>
    </Card>
  );
}

export function CalibrationView() {
  const { t } = useI18n();
  const cr = aionis.calibrationReliability;
  const regions = Object.entries(cr.regions ?? {});
  const ok = cr.status === "ok" && regions.length > 0;

  return (
    <div className="flex flex-col gap-4">
      <p className="text-xs font-medium text-primary">{t("calibration.role")}</p>
      <header>
        <h1 className="text-2xl font-semibold tracking-[-0.032em]">{t("calibration.title")}</h1>
        <p className="mt-2 text-[13px] text-mute">{t("calibration.window")}</p>
      </header>

      {ok ? (
        regions.map(([region, payload]) =>
          region === "cn" ? (
            <LazyMount minHeight={640} key={region}>
              <RegionCard region={region} payload={payload} />
            </LazyMount>
          ) : (
            <RegionCard key={region} region={region} payload={payload} />
          ),
        )
      ) : (
        <Card className="border-amber-500/30 bg-amber-500/5">
          <CardContent className="p-4 text-sm text-muted-foreground">{t("calibration.awaiting")}</CardContent>
        </Card>
      )}

      <Card className="border-dashed">
        <CardHeader className="border-b">
          <CardTitle className="flex items-center gap-2 text-base">
            <ShieldCheckIcon className="size-4" /> {t("calibration.howto")}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 p-4">
          <p className="text-xs text-muted-foreground">{cr.methodology ?? t("calibration.window")}</p>
          <p className="flex items-center gap-1.5 text-xs text-amber-700 dark:text-amber-400">
            <ShieldAlertIcon className="size-3.5 shrink-0" />
            {t("calibration.disclaimer")}
          </p>
        </CardContent>
      </Card>

      {/* TASK-H1 — horizon robustness of the frozen nulls (validity family):
          the calibration tab is the /track validity entry, and this panel is
          the same kind of measurement self-check (does the frozen verdict
          survive a non-frozen horizon?). No new tab/route — hash behavior
          unchanged. */}
      <LazyMount minHeight={360}>
        <HorizonRobustnessCard />
      </LazyMount>
    </div>
  );
}
