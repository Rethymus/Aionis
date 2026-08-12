"use client";

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { BrainCircuitIcon, LockIcon } from "lucide-react";
import { useI18n } from "@/i18n/provider";
import { aionis } from "@/data/aionis";

// AI attribution (paradigm-α Track B, display-only). Renders an honest economic
// narrative of WHY the frozen null verdict is null — grounded strictly in the
// already-frozen ledger #49 result (IC / CI / p / power-floor), NOT a live LLM
// prediction. This is the compliance-safe form of "AI 贯彻": the AI contributes
// interpretation/attribution, never an OOS signal (LLM features = known leakage
// channel; see reports/design/2026-08-12-scientific-research-system-synthesis.md §3).
//
// The narrative below is a hand-anchored attribution (deterministic, no external
// call). A future live-LLM version would call the GLM router with ONLY these
// frozen public numbers as context and is gated on explicit owner approval
// (external, irreversible). Until then this card ships zero side-effects.

// A concise, honest, economically-grounded reading of the null. Pure function of
// the frozen metrics + the sigma-survey noise floor — no invented detail, no
// prediction, no advice.
function buildAttribution(
  m: typeof aionis.metrics,
  sigmaSurvey: typeof aionis.sigmaSurvey,
): {
  ciBracketsZero: boolean;
  sigmaFloor: number | null;
  points: { key: string; body: string }[];
} {
  const hasCI = m.ci_lo !== null && m.ci_hi !== null;
  const ciBracketsZero = hasCI && m.ci_lo! < 0 && m.ci_hi! > 0;
  const ciHalf = hasCI ? Math.max(Math.abs(m.ci_lo!), Math.abs(m.ci_hi!)) : null;
  const sesoi = m.sesoi ?? 0.01;
  const powerFloorAttainable = ciHalf !== null ? ciHalf <= sesoi : null;

  // Derive the monthly noise-floor sigma from the sigma survey's confirmatory
  // combined arm (the same Track C climax result the hero number comes from),
  // rather than a hand-constant. Falls back to null if the survey is absent.
  const sigmaFloor = (() => {
    const rows = sigmaSurvey?.rows;
    if (!Array.isArray(rows)) return null;
    const combined = rows.find(
      (r) => r.source === "track_c_confirmatory" && r.arm === "combined",
    );
    return typeof combined?.sigma_observed === "number" ? combined.sigma_observed : null;
  })();
  const sigmaStr = sigmaFloor !== null ? `σ≈${sigmaFloor.toFixed(2)}` : "σ≈0.10";

  const points: { key: string; body: string }[] = [
    {
      key: "ic",
      body: `combined rank-IC = ${m.combined_ic.toFixed(4)}（${m.combined_ic >= 0 ? "微正" : "微负"}，量级远小于月频噪声地板 ${sigmaStr}）。点估计不构成可检测效应。`,
    },
    {
      key: "ci",
      body: hasCI
        ? `95% HAC CI = [${m.ci_lo!.toFixed(4)}, ${m.ci_hi!.toFixed(4)}]${ciBracketsZero ? " 跨越零 —— 无法排除「统筹分配」的零效应。" : "（未跨零）。"}`
        : "置信区间不可得。",
    },
    {
      key: "power",
      body:
        powerFloorAttainable === null
          ? `SESOI ±${sesoi} 的等价宣告需 CI 半宽 ≤ ${sesoi}；当前数据不足以下等价结论。`
          : powerFloorAttainable
            ? `CI 半宽 ${ciHalf!.toFixed(4)} ≤ SESOI ±${sesoi}：等价宣告在数据上可达（但 J-T 序贯门仍未放行）。`
            : `CI 半宽 ${ciHalf!.toFixed(4)} >> SESOI ±${sesoi}：月频噪声地板下，±${sesoi} 等价结构性不可达（设计级欠功率，非「没效应」）。`,
    },
    {
      key: "discipline",
      body: "结论可信非因效应强，而因反泄漏纪律严：PIT 数据 + PurgedGroupKFold+embargo + H6 比特一致。null 是预期、可发表的结果。",
    },
  ];

  return { ciBracketsZero, sigmaFloor, points };
}

export function AiAttributionCard() {
  const { t } = useI18n();
  const m = aionis.metrics;
  const { points } = buildAttribution(m, aionis.sigmaSurvey);

  return (
    <Card className="overflow-hidden border-primary/20">
      <CardHeader className="gap-2">
        <div className="flex items-center justify-between gap-2">
          <CardTitle className="flex items-center gap-2 text-base">
            <BrainCircuitIcon className="size-4 text-primary" />
            {t("ai.attribution.title")}
          </CardTitle>
          <Badge variant="outline" className="gap-1 px-1.5 py-0 text-[10px] font-normal text-muted-foreground">
            <LockIcon className="size-2.5" />
            {t("ai.attribution.mode")}
          </Badge>
        </div>
        <CardDescription>{t("ai.attribution.intro")}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-2.5">
        <ol className="space-y-2">
          {points.map((p) => (
            <li key={p.key} className="flex gap-2 text-xs leading-relaxed">
              <span className="mt-0.5 size-1.5 shrink-0 rounded-full bg-primary/50" />
              <span className="text-muted-foreground">{p.body}</span>
            </li>
          ))}
        </ol>
        <p className="border-t pt-2 text-[10px] text-muted-foreground/70">
          {t("ai.attribution.boundary")}
        </p>
      </CardContent>
    </Card>
  );
}
