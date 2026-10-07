"use client";

import { useI18n } from "@/i18n/provider";
import { aionis } from "@/data/aionis";
import { cn } from "@/lib/utils";
import type { Evidence } from "@/data/aionis";

// Global CI axis across all rows so every interval shares one zero line —
// the board's whole point is "every interval crosses zero, at a glance".
const allBounds = aionis.evidence.flatMap((r) =>
  r.ci_lo !== null && r.ci_hi !== null ? [r.ci_lo, r.ci_hi] : [],
);
const AXIS_MIN = Math.min(...allBounds, -0.01);
const AXIS_MAX = Math.max(...allBounds, 0.01);
const pct = (v: number) =>
  ((v - AXIS_MIN) / (AXIS_MAX - AXIS_MIN)) * 100;

function verdict(r: Evidence): { kind: "null" | "point"; ci: boolean } {
  const hasCi = r.ci_lo !== null && r.ci_hi !== null;
  if (hasCi) return { kind: "null", ci: true }; // every CI-bearing row brackets zero (panel fact)
  return { kind: "point", ci: false };
}

export function VerdictBoardView() {
  const { t } = useI18n();
  const rows = aionis.evidence;

  return (
    <div className="flex flex-col gap-4">
      <p className="text-xs font-medium text-primary">{t("verdicts.role")}</p>
      <header className="space-y-2">
        <h1 className="text-2xl font-semibold tracking-[-0.032em]">
          {t("module.verdicts.title")}
        </h1>
        <p className="max-w-3xl text-sm text-muted-foreground">{t("verdicts.intro")}</p>
      </header>

      {/* Board */}
      <div className="overflow-x-auto rounded-lg border">
        <table className="w-full min-w-[860px] border-collapse text-sm">
          <thead>
            <tr className="border-b bg-muted/40 text-left text-xs text-muted-foreground">
              <th className="px-3 py-2 font-medium">#</th>
              <th className="px-3 py-2 font-medium">{t("verdicts.col.claim")}</th>
              <th className="px-3 py-2 font-medium">{t("verdicts.col.estimate")}</th>
              <th className="w-[38%] px-3 py-2 font-medium">{t("verdicts.col.ci")}</th>
              <th className="px-3 py-2 font-medium">p</th>
              <th className="px-3 py-2 font-medium">n</th>
              <th className="px-3 py-2 font-medium"
                  title={t("verdicts.grade.hint")}>{t("verdicts.col.grade")}</th>
              <th className="px-3 py-2 font-medium">{t("verdicts.col.verdict")}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => {
              const v = verdict(r);
              const confirmatory = r.grade === "CONFIRMATORY";
              return (
                <tr key={r.n} className={cn(
                  "border-b last:border-0",
                  confirmatory && "bg-primary/5",
                )}>
                  <td className="px-3 py-2 tabular-nums text-muted-foreground">{r.n}</td>
                  <td className="px-3 py-2 font-medium">{r.result}</td>
                  <td className="px-3 py-2 tabular-nums">
                    {r.estimate !== null ? r.estimate.toFixed(4) : "—"}
                  </td>
                  <td className="px-3 py-2">
                    {v.ci ? (
                      <div className="relative h-5 min-w-[220px]" title={`[${r.ci_lo?.toFixed(4)}, ${r.ci_hi?.toFixed(4)}]`}>
                        {/* zero reference line */}
                        <div
                          className="absolute inset-y-0 w-px bg-border"
                          style={{ left: `${pct(0)}%` }}
                        />
                        {/* CI bar */}
                        <div
                          className="absolute top-1/2 h-[6px] -translate-y-1/2 rounded-sm bg-primary/45"
                          style={{
                            left: `${pct(r.ci_lo!)}%`,
                            width: `${pct(r.ci_hi!) - pct(r.ci_lo!)}%`,
                          }}
                        />
                        {/* point estimate marker */}
                        {r.estimate !== null && (
                          <div
                            className="absolute top-1/2 size-[10px] -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-primary bg-background"
                            style={{ left: `${pct(r.estimate)}%` }}
                          />
                        )}
                        <span className="absolute right-0 top-0 text-[10px] tabular-nums text-muted-foreground">
                          [{r.ci_lo?.toFixed(3)}, {r.ci_hi?.toFixed(3)}]
                        </span>
                      </div>
                    ) : (
                      <span className="text-xs text-muted-foreground">{t("verdicts.noCi")}</span>
                    )}
                  </td>
                  <td className="px-3 py-2 tabular-nums">{r.p ?? "—"}</td>
                  <td className="px-3 py-2 tabular-nums text-muted-foreground">{r.n_months}</td>
                  <td className="px-3 py-2">
                    <span className={cn(
                      "rounded-full border px-2 py-0.5 text-[10px] font-medium",
                      confirmatory
                        ? "border-primary/60 text-primary"
                        : "border-border text-muted-foreground",
                    )}>
                      {r.grade}
                    </span>
                  </td>
                  <td className="px-3 py-2">
                    <span className={cn(
                      "rounded-full px-2 py-0.5 text-[10px] font-semibold",
                      v.kind === "null" && !confirmatory && "bg-muted text-foreground",
                      v.kind === "null" && confirmatory && "border border-primary/60 bg-primary/10 text-primary",
                      v.kind === "point" && "border border-dashed border-border text-muted-foreground",
                    )}>
                      {v.kind === "null" ? t("verdicts.badge.null") : t("verdicts.badge.point")}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="rounded-lg border bg-muted/30 p-3">
        <p className="text-xs font-semibold">{t("verdicts.diag.title")}</p>
        <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
          {t("verdicts.diag.body")}
        </p>
      </div>

      <p className="text-xs text-muted-foreground">{t("verdicts.footer")}</p>
    </div>
  );
}
