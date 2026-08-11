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
import {
  Bar,
  BarChart,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

export function SmartMoneyView() {
  const { t } = useI18n();
  const sm = aionis.smartMoney;
  const yearlyHeading = "年度 13D 申报趋势 / Yearly 13D filings";

  return (
    <div className="space-y-6 p-4 md:p-6">
      <p className="text-xs font-medium text-primary">{t("smartmoney.role")}</p>
      <header className="space-y-1">
        <h1 className="text-2xl font-bold tracking-tight">{t("smartmoney.title")}</h1>
        <p className="text-sm text-muted-foreground">{t("smartmoney.window")}</p>
      </header>

      <div className="grid grid-cols-3 gap-3">
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">{t("smartmoney.total")}</p>
            <p className="mt-1 text-2xl font-bold tabular-nums">{sm.total_filings}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">{t("smartmoney.filers")}</p>
            <p className="mt-1 text-2xl font-bold tabular-nums">{sm.n_filers}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">{t("smartmoney.latest")}</p>
            <p className="mt-1 text-2xl font-bold tabular-nums">{sm.latest_date ?? "—"}</p>
          </CardContent>
        </Card>
      </div>

      <Card className="overflow-hidden py-0">
        <CardHeader className="border-b">
          <CardTitle className="text-base">{t("smartmoney.active")}</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="divide-y">
            {sm.active_filers.map((f, i) => (
              <div key={f.filer} className="flex items-center gap-3 px-4 py-2.5 text-sm">
                <span className="w-6 shrink-0 text-muted-foreground tabular-nums">{i + 1}</span>
                <span className="truncate">{f.filer}</span>
                <Badge variant="secondary" className="ml-auto shrink-0 tabular-nums">
                  {f.count}
                </Badge>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card className="overflow-hidden py-0">
        <CardHeader className="border-b">
          <CardTitle className="text-base">{t("smartmoney.recent")}</CardTitle>
          <CardDescription>{t("smartmoney.window")}</CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          <div className="divide-y">
            {sm.recent_filings.map((r, i) => (
              <div key={i} className="flex items-center gap-3 px-4 py-2.5 text-sm">
                <span className="w-24 shrink-0 font-mono text-xs text-muted-foreground">
                  {r.date}
                </span>
                <Badge
                  variant="outline"
                  className={cn(
                    "shrink-0 px-1.5 py-0 text-[10px]",
                    r.is_amendment
                      ? "text-muted-foreground"
                      : "border-emerald-500/40 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
                  )}
                >
                  {t(r.is_amendment ? "smartmoney.amendment" : "smartmoney.new")}
                </Badge>
                <span className="w-32 shrink-0 truncate text-muted-foreground">{r.filer}</span>
                {r.url ? (
                  <a
                    href={r.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="truncate font-medium underline-offset-2 hover:underline"
                    title={t("smartmoney.filing_link")}
                  >
                    → {r.target}
                  </a>
                ) : (
                  <span className="truncate font-medium">→ {r.target}</span>
                )}
                {r.ticker ? (
                  <Badge variant="secondary" className="ml-auto shrink-0 font-mono text-[10px]">
                    {r.ticker}
                  </Badge>
                ) : null}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {sm.yearly && sm.yearly.length > 0 && (
        <Card>
          <CardHeader className="border-b">
            <CardTitle className="text-base" title={t("smartmoney.term13DHint")}>
              {yearlyHeading}
            </CardTitle>
          </CardHeader>
          <CardContent className="p-2">
            <div className="h-[180px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={sm.yearly} margin={{ top: 12, right: 20, bottom: 24, left: 12 }}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                  <XAxis
                    dataKey="year"
                    tickFormatter={(v) => String(v)}
                    className="text-xs"
                  />
                  <YAxis className="text-xs" />
                  <Tooltip
                    formatter={(v) => [Number(v).toLocaleString(), t("smartmoney.term13DFilings")]}
                    labelFormatter={(l) => `Year: ${l}`}
                    contentStyle={{ fontSize: "12px" }}
                  />
                  <Bar dataKey="filings" fill="hsl(var(--primary))" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      )}

      <p className="text-xs text-muted-foreground">{t("smartmoney.explain")}</p>
    </div>
  );
}
