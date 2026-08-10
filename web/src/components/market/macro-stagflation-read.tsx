"use client"

import { aionis } from "@/data/aionis"
import { cn } from "@/lib/utils"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { useI18n } from "@/i18n/provider"

// Inline bilingual labels for new UI elements
const stagflationTitle = "滞涨风险 · Stagflation watch"
const heuristicDisclaimer = "Heuristic, not a forecast · 启发式参考，非预测"
const awaitingText = "Awaiting data · 等待数据"
const targetText = "target · 目标"

type StagflationGrade = "moderate" | "watch" | "elevated"

function getStagflationGrade(cpi: number, pay: number): StagflationGrade {
  if (cpi > 3 && pay < 1) return "elevated"
  if (cpi > 2.5 || pay < 1) return "watch"
  return "moderate"
}

function getGradeBadgeVariant(grade: StagflationGrade): "default" | "secondary" | "destructive" | "outline" {
  switch (grade) {
    case "elevated":
      return "destructive" // rose
    case "watch":
      return "outline" // amber outline
    case "moderate":
      return "default" // emerald
  }
}

function getGradeLabel(grade: StagflationGrade): string {
  switch (grade) {
    case "elevated":
      return "Elevated · 升高"
    case "watch":
      return "Watch · 关注"
    case "moderate":
      return "Moderate · 适中"
  }
}

function getGradeColorClass(grade: StagflationGrade): string {
  switch (grade) {
    case "elevated":
      return "text-rose-600 dark:text-rose-400"
    case "watch":
      return "text-amber-600 dark:text-amber-400"
    case "moderate":
      return "text-emerald-600 dark:text-emerald-400"
  }
}

export function MacroStagflationRead() {
  const { t } = useI18n()

  const { status, series } = aionis.macroDrivers

  // Guard for missing data
  if (status !== "ok" || !series) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">{stagflationTitle}</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-xs text-muted-foreground">{awaitingText}</p>
        </CardContent>
      </Card>
    )
  }

  const cpiLatest = series.cpi_yoy?.at(-1)
  const payLatest = series.payems_yoy?.at(-1)
  const ffLatest = series.fedfunds?.at(-1)

  // Guard for empty series
  if (!cpiLatest || !payLatest || !ffLatest) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">{stagflationTitle}</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-xs text-muted-foreground">{awaitingText}</p>
        </CardContent>
      </Card>
    )
  }

  const cpi = cpiLatest.value
  const pay = payLatest.value
  const ff = ffLatest.value

  const grade = getStagflationGrade(cpi, pay)
  const badgeVariant = getGradeBadgeVariant(grade)
  const gradeLabel = getGradeLabel(grade)
  const gradeColorClass = getGradeColorClass(grade)

  const summaryRead = `CPI ${cpi}% (vs 2% ${targetText}) · payrolls ${pay}% YoY · Fed funds ${ff}%`

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium">{stagflationTitle}</CardTitle>
          <Badge variant={badgeVariant} className={cn("text-xs", gradeColorClass)}>
            {gradeLabel}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Three stat tiles */}
        <div className="grid grid-cols-3 gap-3">
          {/* CPI */}
          <div className="space-y-1">
            <p className="text-xs text-muted-foreground">{t("macro.cpi")}</p>
            <p className={cn("text-lg font-semibold", gradeColorClass)}>{cpi}%</p>
          </div>

          {/* Payrolls */}
          <div className="space-y-1">
            <p className="text-xs text-muted-foreground">{t("macro.payrolls")}</p>
            <p className={cn("text-lg font-semibold", gradeColorClass)}>{pay}%</p>
          </div>

          {/* Fed Funds */}
          <div className="space-y-1">
            <p className="text-xs text-muted-foreground">{t("macro.fedfunds")}</p>
            <p className={cn("text-lg font-semibold", gradeColorClass)}>{ff}%</p>
          </div>
        </div>

        {/* One-line read */}
        <p className="text-xs text-muted-foreground border-t pt-3">
          {summaryRead}
        </p>

        {/* Disclaimer */}
        <p className="text-[10px] text-muted-foreground/70 italic">
          {heuristicDisclaimer}
        </p>
      </CardContent>
    </Card>
  )
}
