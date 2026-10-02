"use client";

// Calibration recharts figures (round 122, market round-114 recipe): the
// scatter/ECE charts hydrate from an async chunk; the stat grids, headers
// and pooled-ECE badges stay SSR in calibration-view.tsx (content-first).
// Both blocks are SLICED VERBATIM from the pre-split file.

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
import { useI18n } from "@/i18n/provider";

type ReliabilityPoint = { x: number; y: number; n: number };
type EcePoint = { month: string; ece: number };

export function RegionCharts({
  relPoints,
  eceSeries,
  xInterval,
}: {
  relPoints: ReliabilityPoint[];
  eceSeries: EcePoint[];
  xInterval: number;
}) {
  const { t } = useI18n();
  return (
    <>
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
                  tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
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
                  tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
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
                  stroke="var(--primary)"
                  strokeDasharray="4 4"
                  ifOverflow="extendDomain"
                />
                <Scatter data={relPoints} dataKey="y" fill="var(--primary)" />
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
                  tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
                  angle={-30}
                  textAnchor="end"
                  height={36}
                />
                <YAxis domain={[0, "auto"]} tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} width={32} />
                <Tooltip
                  contentStyle={{ fontSize: 12, borderRadius: 8 }}
                  formatter={(value) => [Number(value).toFixed(4), t("calibration.eceTerm")]}
                />
                <ReferenceLine y={0.05} stroke="#10b981" strokeDasharray="3 3" />
                <Line type="monotone" dataKey="ece" stroke="var(--primary)" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
    </>
  );
}
