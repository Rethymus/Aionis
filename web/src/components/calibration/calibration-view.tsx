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
import { ShieldAlertIcon, ShieldCheckIcon } from "lucide-react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

type RegionPayload = CalibrationReliability["regions"][string];
type ReliabilityPoint = { x: number; y: number; n: number };
type EcePoint = { month: string; ece: number };

function Stat({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 text-xl font-bold tabular-nums">{value}</p>
      {hint ? <p className="text-[10px] leading-tight text-muted-foreground/70">{hint}</p> : null}
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

        <div>
          <p className="mb-1 text-xs font-medium text-muted-foreground">{t("calibration.reliabilityTitle")}</p>
          <div className="h-[220px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart margin={{ top: 8, right: 16, bottom: 20, left: 8 }}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted/30" />
                <XAxis
                  type="number"
                  dataKey="x"
                  domain={[0, 1]}
                  tickCount={6}
                  tick={{ fontSize: 11 }}
                  label={{
                    value: t("calibration.predP"),
                    position: "insideBottom",
                    offset: -10,
                    fontSize: 11,
                  }}
                />
                <YAxis
                  type="number"
                  dataKey="y"
                  domain={[0, 1]}
                  tickCount={6}
                  tick={{ fontSize: 11 }}
                  label={{
                    value: t("calibration.empFreq"),
                    angle: -90,
                    position: "insideLeft",
                    fontSize: 11,
                  }}
                />
                <Tooltip
                  cursor={{ strokeDasharray: "3 3" }}
                  contentStyle={{ fontSize: 12, borderRadius: 8 }}
                  formatter={(value, name) =>
                    name === "n" ? Number(value).toLocaleString() : Number(value).toFixed(3)
                  }
                />
                <ReferenceLine
                  segment={[
                    { x: 0, y: 0 },
                    { x: 1, y: 1 },
                  ]}
                  stroke="hsl(var(--primary))"
                  strokeDasharray="4 4"
                  ifOverflow="extendDomain"
                />
                <Scatter data={relPoints} dataKey="y" fill="hsl(var(--primary))" />
              </ScatterChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div>
          <p className="mb-1 text-xs font-medium text-muted-foreground">{t("calibration.eceTitle")}</p>
          <div className="h-[160px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={eceSeries} margin={{ top: 8, right: 16, bottom: 4, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted/30" />
                <XAxis
                  dataKey="month"
                  interval={xInterval}
                  tick={{ fontSize: 10 }}
                  angle={-30}
                  textAnchor="end"
                  height={36}
                />
                <YAxis domain={[0, "auto"]} tick={{ fontSize: 11 }} width={32} />
                <Tooltip
                  contentStyle={{ fontSize: 12, borderRadius: 8 }}
                  formatter={(value) => [Number(value).toFixed(4), "ECE"]}
                />
                <ReferenceLine y={0.05} stroke="#10b981" strokeDasharray="3 3" />
                <Line type="monotone" dataKey="ece" stroke="hsl(var(--primary))" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
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
    <div className="space-y-6 p-4 md:p-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-bold tracking-tight">{t("calibration.title")}</h1>
        <p className="text-sm text-muted-foreground">{t("calibration.window")}</p>
      </header>

      {ok ? (
        regions.map(([region, payload]) => (
          <RegionCard key={region} region={region} payload={payload} />
        ))
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
    </div>
  );
}
