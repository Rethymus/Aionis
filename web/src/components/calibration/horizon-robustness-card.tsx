"use client";

// TASK-H1 — horizon-robustness card on /track (calibration tab, validity
// family). Renders the committed horizon_robustness.json panel: the latest
// exploratory `sensitivity_horizon` ledger row projected to a per-phase
// table (differential + 95% CI + DM p at each swept horizon, verdict badges).
// Red lines honored: emerald = trust semantics ONLY (verdict badges — the
// differentials themselves stay neutral tabular ink, no up/down color), no
// Date.now / Math.random, every number straight from the panel (ledger-real).
// Display-only derivation of an EXPLORATORY row (h≠21 = changed config) — it
// asserts no confirmatory claim; the note line carries that disclosure.

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
import {
  aionis,
  type HorizonHorizonCell,
  type HorizonPhase,
} from "@/data/aionis";
import { CheckIcon, MinusIcon, ShieldAlertIcon, ShieldCheckIcon, XIcon } from "lucide-react";

// Emerald = "null holds" (trust); amber = a null broke at a non-frozen
// horizon. Both are verdict semantics — never market up/down direction.
const HOLD_BADGE =
  "border-emerald-500/40 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400";
const BROKE_BADGE =
  "border-amber-500/40 bg-amber-500/10 text-amber-700 dark:text-amber-400";

function fmtSigned(v: number | null | undefined): string {
  return typeof v === "number" && Number.isFinite(v)
    ? `${v > 0 ? "+" : ""}${v.toFixed(4)}`
    : "—";
}

function fmtNum(v: number | null | undefined, dp = 4): string {
  return typeof v === "number" && Number.isFinite(v) ? v.toFixed(dp) : "—";
}

// One verdict badge per swept horizon: check (holds) / x (broke) / minus
// (coverage incomplete — honest null), titled with the verdict label.
function HorizonVerdictBadge({ cell, horizon }: { cell: HorizonHorizonCell | null; horizon: string }) {
  const { t } = useI18n();
  const holds = cell?.null_holds;
  const label =
    holds === true
      ? t("track.horizon.verdict.holds")
      : holds === false
        ? t("track.horizon.verdict.broke")
        : "—";
  return (
    <Badge
      variant="outline"
      className={cn(
        "gap-0.5 px-1.5 py-0 text-[10px]",
        holds === true ? HOLD_BADGE : holds === false ? BROKE_BADGE : "text-muted-foreground",
      )}
      aria-label={`${horizon} ${label}`}
      title={`${horizon}: ${label}`}
    >
      {horizon}
      {holds === true ? (
        <CheckIcon className="size-3" aria-hidden />
      ) : holds === false ? (
        <XIcon className="size-3" aria-hidden />
      ) : (
        <MinusIcon className="size-3" aria-hidden />
      )}
    </Badge>
  );
}

function PhaseCells({ phase, horizon }: { phase: HorizonPhase; horizon: "h10" | "h42" }) {
  const cell = phase[horizon];
  return (
    <>
      <td className="px-2 py-1.5 text-right font-mono text-[11px] tabular-nums">
        {fmtSigned(cell?.mean_diff)}
      </td>
      <td className="px-2 py-1.5 text-right font-mono text-[11px] tabular-nums text-muted-foreground">
        {cell ? `[${fmtNum(cell.ci_lo)}, ${fmtNum(cell.ci_hi)}]` : "—"}
      </td>
      <td className="px-2 py-1.5 text-right font-mono text-[11px] tabular-nums text-muted-foreground">
        {fmtNum(cell?.dm_p_mbb, 3)}
      </td>
    </>
  );
}

export function HorizonRobustnessCard() {
  const { t } = useI18n();
  const hr = aionis.horizonRobustness;
  const phases = Object.entries(hr.phases ?? {});
  if (hr.status !== "ok" || phases.length === 0) {
    return null; // honest degradation — never render an empty/fabricated card
  }
  const all = hr.horizon_robust_all;
  const asOf = typeof hr.source_ts === "string" ? hr.source_ts.slice(0, 10) : "—";

  return (
    <Card>
      <CardHeader className="border-b">
        <CardTitle className="flex items-center justify-between text-base">
          <span>{t("track.horizon.title")}</span>
          {all === true ? (
            <Badge variant="outline" className={cn("gap-1", HOLD_BADGE)}>
              <ShieldCheckIcon className="size-3.5" aria-hidden />
              {t("track.horizon.verdict.holds")}
            </Badge>
          ) : all === false ? (
            <Badge variant="outline" className={cn("gap-1", BROKE_BADGE)}>
              <ShieldAlertIcon className="size-3.5" aria-hidden />
              {t("track.horizon.verdict.broke")}
            </Badge>
          ) : null}
        </CardTitle>
        <CardDescription>{t("track.horizon.desc")}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3 p-4">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-[11px]">
            <thead>
              <tr className="text-muted-foreground">
                <th rowSpan={2} className="border-b border-border px-2 py-1.5 font-medium">
                  {t("track.horizon.col.phase")}
                </th>
                <th colSpan={3} className="border-b border-border px-2 py-1.5 text-center font-medium">
                  h10
                </th>
                <th colSpan={3} className="border-b border-border px-2 py-1.5 text-center font-medium">
                  h42
                </th>
                <th rowSpan={2} className="border-b border-border px-2 py-1.5 text-right font-medium">
                  {t("track.horizon.col.verdict")}
                </th>
              </tr>
              <tr className="text-muted-foreground">
                <th className="border-b border-border px-2 py-1 text-right font-medium">
                  {t("track.horizon.col.diff")}
                </th>
                <th className="border-b border-border px-2 py-1 text-right font-medium">
                  {t("track.horizon.col.ci")}
                </th>
                <th className="border-b border-border px-2 py-1 text-right font-medium">
                  {t("track.horizon.col.dmp")}
                </th>
                <th className="border-b border-border px-2 py-1 text-right font-medium">
                  {t("track.horizon.col.diff")}
                </th>
                <th className="border-b border-border px-2 py-1 text-right font-medium">
                  {t("track.horizon.col.ci")}
                </th>
                <th className="border-b border-border px-2 py-1 text-right font-medium">
                  {t("track.horizon.col.dmp")}
                </th>
              </tr>
            </thead>
            <tbody>
              {phases.map(([phase, p]) => (
                <tr key={phase} className="border-t border-border">
                  <td className="px-2 py-1.5">
                    <span className="font-mono text-[12px] font-semibold">{phase}</span>
                    <span className="ml-2 font-mono text-[10px] text-muted-foreground">
                      {p.arm_enhanced ?? "—"}
                      {p.arm_base ? ` − ${p.arm_base}` : ""}
                    </span>
                  </td>
                  <PhaseCells phase={p} horizon="h10" />
                  <PhaseCells phase={p} horizon="h42" />
                  <td className="px-2 py-1.5">
                    <div className="flex justify-end gap-1">
                      <HorizonVerdictBadge cell={p.h10} horizon="h10" />
                      <HorizonVerdictBadge cell={p.h42} horizon="h42" />
                    </div>
                  </td>
                </tr>
              ))}
              <tr className="border-t border-border">
                <td colSpan={8} className="px-2 py-1.5">
                  {all === true ? (
                    <span className="flex items-center gap-1.5 text-emerald-700 dark:text-emerald-400">
                      <ShieldCheckIcon className="size-3.5 shrink-0" aria-hidden />
                      {t("track.horizon.allholds")}
                    </span>
                  ) : all === false ? (
                    <span className="flex items-center gap-1.5 text-amber-700 dark:text-amber-400">
                      <ShieldAlertIcon className="size-3.5 shrink-0" aria-hidden />
                      {t("track.horizon.verdict.broke")}
                    </span>
                  ) : (
                    <span className="text-muted-foreground">—</span>
                  )}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <p className="text-xs leading-relaxed text-muted-foreground">{t("track.horizon.note")}</p>
        <p className="text-xs text-muted-foreground">
          {t("track.horizon.asof")}: <span className="font-mono tabular-nums">{asOf}</span>
        </p>
      </CardContent>
    </Card>
  );
}
