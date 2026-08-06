"use client";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useI18n } from "@/i18n/provider";
import { aionis } from "@/data/aionis";
import { cn } from "@/lib/utils";
import {
  Scatter,
  ScatterChart,
  ReferenceLine,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
  ResponsiveContainer,
} from "recharts";

const toneForLook = (i: number) =>
  i === 0 ? "text-destructive" : i === 1 ? "text-amber-600 dark:text-amber-400" : "text-emerald-600 dark:text-emerald-400";

export function PowerFloorView() {
  const { t } = useI18n();
  const looks = aionis.powerFloor.looks;
  const sigmaRows = aionis.sigmaSurvey.rows.map((r) => ({
    x: r.sigma_pure_noise,
    y: r.sigma_observed,
    series: `${r.source}/${r.arm}`,
    excess: r.excess_ratio,
  }));
  const maxY = Math.max(...sigmaRows.map((r) => r.y)) * 1.05;

  return (
    <div className="space-y-6 p-4 md:p-6">
      <header className="space-y-2">
        <h1 className="text-2xl font-bold tracking-tight">{t("module.powerfloor.title")}</h1>
        <p className="max-w-2xl text-sm text-muted-foreground">{t("powerfloor.intro")}</p>
      </header>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
        {looks.map((l, i) => (
          <Card key={l.look}>
            <CardContent className="p-4">
              <p className="text-xs text-muted-foreground">
                Look {l.look} · planned n={l.n}
              </p>
              <p className={cn("mt-1 text-2xl font-bold tabular-nums", toneForLook(i))}>
                {l.n_min_years.toFixed(1)}y
              </p>
              <p className="mt-0.5 text-xs text-muted-foreground tabular-nums">
                z={l.z} · RCI {l.rci_level_pct}%
              </p>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card className="overflow-hidden py-0">
        <CardHeader className="border-b">
          <CardTitle className="text-base">Minimum-n per look</CardTitle>
          <CardDescription>{t("module.powerfloor.window")}</CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          <div className="divide-y">
            {looks.map((l) => (
              <div key={l.look} className="flex items-center gap-4 px-4 py-2.5 text-sm">
                <span className="w-12 font-medium">Look {l.look}</span>
                <span className="w-24 text-muted-foreground tabular-nums">n={l.n}</span>
                <span className="w-24 text-muted-foreground tabular-nums">z={l.z}</span>
                <span className="ml-auto font-mono tabular-nums">
                  {l.n_min_months} mo
                </span>
                <span className="w-20 text-right font-mono text-muted-foreground tabular-nums">
                  {l.n_min_years}y
                </span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="border-b">
          <CardTitle className="text-base">
            σ(IC) observed vs pure-noise bound 1/√(N−1)
          </CardTitle>
          <CardDescription>
            {aionis.sigmaSurvey.summary.n_series} IC series · median excess{" "}
            {aionis.sigmaSurvey.summary.excess_median.toFixed(1)}× · all above the y=x line
          </CardDescription>
        </CardHeader>
        <CardContent className="p-2">
          <div className="h-[360px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart margin={{ top: 16, right: 24, bottom: 40, left: 16 }}>
                <ReferenceLine
                  segment={[
                    { x: 0, y: 0 },
                    { x: maxY, y: maxY },
                  ]}
                  stroke="oklch(0.704 0.191 22.216)"
                  strokeDasharray="4 4"
                />
                <XAxis
                  type="number"
                  dataKey="x"
                  name="σ_null"
                  domain={[0, "dataMax"]}
                  tickFormatter={(v) => Number(v).toFixed(3)}
                  label={{ value: "σ_null = 1/√(N−1)", position: "insideBottom", offset: -12, className: "fill-muted-foreground text-xs" }}
                />
                <YAxis
                  type="number"
                  dataKey="y"
                  name="σ_obs"
                  domain={[0, maxY]}
                  tickFormatter={(v) => Number(v).toFixed(2)}
                  label={{ value: "σ(IC) observed", angle: -90, position: "insideLeft", className: "fill-muted-foreground text-xs" }}
                />
                <ZAxis type="number" dataKey="excess" range={[60, 160]} name="excess" />
                <Tooltip
                  cursor={{ strokeDasharray: "3 3" }}
                  formatter={(value) => Number(value).toFixed(4)}
                  labelFormatter={() => ""}
                  contentStyle={{ fontSize: "12px" }}
                />
                <Scatter data={sigmaRows} fill="oklch(0.556 0 0)" />
              </ScatterChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
