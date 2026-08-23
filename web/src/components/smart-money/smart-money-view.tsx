"use client";

import { useMemo, useState } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { fmtDateShort } from "@/lib/format";
import { FilterPills, LoadMoreFooter, usePaged } from "@/components/stream/stream-kit";
import { useI18n } from "@/i18n/provider";
import { aionis, type StakesPct } from "@/data/aionis";
import Link from "next/link";
import {
  Bar,
  BarChart,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

const PAGE_SIZE = 30;

type KindFilter = "all" | "new" | "amendment";
type GFormFilter = "all" | "SC 13G" | "SC 13G/A";

// The /stakes-style active/passive axis — derived from the immutable form
// type only (SC 13D* = active, SC 13G* = passive): zero parsing dependency.
function StakesTypeBadge({ form }: { form: string }) {
  const { t } = useI18n();
  const active = form.startsWith("SC 13D");
  return (
    <Badge
      variant="outline"
      className={cn(
        "shrink-0 px-1.5 py-0 text-xs",
        active
          ? "border-violet-500/40 bg-violet-500/10 text-violet-600 dark:text-violet-400"
          : "border-slate-500/40 bg-slate-500/10 text-slate-600 dark:text-slate-400",
      )}
    >
      {t(active ? "stakes.type.active" : "stakes.type.passive")}
    </Badge>
  );
}

// Holding-percentage badge + previous value + derived status. Honest-null
// rendering throughout: no parsed pct_now → NO pct badge (no "—" placeholder);
// pct_prev renders only when parsed (amendments); the exited/below_5 badge
// exists only when pct_status carries a PARSED-derived value — null status
// renders nothing.
function StakesPctBadges({ row }: { row: StakesPct }) {
  const { t } = useI18n();
  const now = row.pct_now ?? null;
  const prev = row.pct_prev ?? null;
  const status = row.pct_status ?? null;
  return (
    <span className="flex shrink-0 items-center gap-1" title={t("stakes.pct.hint")}>
      {now !== null && (
        <Badge variant="secondary" className="px-1.5 py-0 text-xs tabular-nums">
          {now}%
          {prev !== null && (
            <span className="ml-1 font-normal text-muted-foreground">
              {t("stakes.pct.prevOpen")} {prev}%{t("stakes.pct.prevClose")}
            </span>
          )}
        </Badge>
      )}
      {status === "exited" && (
        <Badge
          variant="outline"
          className="shrink-0 border-rose-500/40 bg-rose-500/10 px-1.5 py-0 text-xs text-rose-600 dark:text-rose-400"
        >
          {t("stakes.status.exited")}
        </Badge>
      )}
      {status === "below_5" && (
        <Badge
          variant="outline"
          className="shrink-0 border-amber-500/40 bg-amber-500/10 px-1.5 py-0 text-xs text-amber-600 dark:text-amber-400"
        >
          {t("stakes.status.below_5")}
        </Badge>
      )}
    </span>
  );
}

export function SmartMoneyView() {
  const { t } = useI18n();
  const sm = aionis.smartMoney;
  const sg = aionis.stakes13g;
  const yearlyHeading = "年度 13D 申报趋势 / Yearly 13D filings";
  const [kind, setKind] = useState<KindFilter>("all");
  const { visibleCount, reset, loadMore } = usePaged(PAGE_SIZE);
  const [gform, setGform] = useState<GFormFilter>("all");
  const gPaged = usePaged(PAGE_SIZE);

  const recent = sm.recent_filings ?? [];
  const filtered = useMemo(
    () =>
      kind === "all"
        ? recent
        : recent.filter((r) => (kind === "amendment") === r.is_amendment),
    [recent, kind],
  );
  const visible = filtered.slice(0, visibleCount);

  const gRecent = sg.filings ?? [];
  const gFiltered = useMemo(
    () => (gform === "all" ? gRecent : gRecent.filter((r) => r.form === gform)),
    [gRecent, gform],
  );
  const gVisible = gFiltered.slice(0, gPaged.visibleCount);

  const applyKind = (k: KindFilter) => {
    setKind(k);
    reset();
  };
  const applyGForm = (k: GFormFilter) => {
    setGform(k);
    gPaged.reset();
  };

  return (
    <div className="space-y-6 p-4 md:p-6">
      <p className="text-xs font-medium text-primary">{t("smartmoney.role")}</p>
      <header className="space-y-1">
        <h1 className="text-2xl font-bold tracking-tight">{t("smartmoney.title")}</h1>
        <p className="text-sm text-muted-foreground">{t("smartmoney.window")}</p>
        <p className="font-mono text-xs tabular-nums text-muted-foreground/80">
          {sm.total_filings.toLocaleString("en-US")} · latest {sm.latest_date ?? "—"}
        </p>
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
          <div className="pt-1">
            <FilterPills<KindFilter>
              label={t("smartmoney.filter.label")}
              value={kind}
              onChange={applyKind}
              options={[
                { key: "all", label: t("smartmoney.filter.all"), count: recent.length },
                { key: "new", label: t("smartmoney.new"), count: recent.filter((r) => !r.is_amendment).length },
                { key: "amendment", label: t("smartmoney.amendment"), count: recent.filter((r) => r.is_amendment).length },
              ]}
            />
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <div className="divide-y">
            {visible.map((r, i) => (
              <div key={i} className="flex items-center gap-3 px-4 py-2.5 text-sm">
                <span
                  className="w-14 shrink-0 font-mono text-xs text-muted-foreground"
                  title={r.date}
                >
                  {fmtDateShort(r.date)}
                </span>
                <Badge
                  variant="outline"
                  className={cn(
                    "shrink-0 px-1.5 py-0 text-xs",
                    r.is_amendment
                      ? "text-muted-foreground"
                      : "border-emerald-500/40 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
                  )}
                >
                  {t(r.is_amendment ? "smartmoney.amendment" : "smartmoney.new")}
                </Badge>
                <StakesTypeBadge form={r.form} />
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
                <StakesPctBadges row={r} />
                {r.ticker ? (
                  <Link href={`/stock/${r.ticker}`} className="ml-auto shrink-0">
                    <Badge variant="secondary" className="font-mono text-xs">
                      {r.ticker}
                    </Badge>
                  </Link>
                ) : null}
              </div>
            ))}
          </div>
          <LoadMoreFooter
            shown={visible.length}
            total={filtered.length}
            onLoadMore={loadMore}
            pageSize={PAGE_SIZE}
          />
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

      <Card className="overflow-hidden py-0">
        <CardHeader className="border-b">
          <CardTitle className="text-base" title={t("stakes13g.term13GHint")}>
            {t("stakes13g.title")}
          </CardTitle>
          <CardDescription>{t("stakes13g.window")}</CardDescription>
          <p className="font-mono text-xs tabular-nums text-muted-foreground/80">
            {sg.total.toLocaleString("en-US")} · {sg.window.start} → {sg.window.end}
            {sg.by_form["SC 13G"] ? ` · 13G ${sg.by_form["SC 13G"].toLocaleString("en-US")}` : ""}
            {sg.by_form["SC 13G/A"] ? ` · 13G/A ${sg.by_form["SC 13G/A"].toLocaleString("en-US")}` : ""}
          </p>
          <div className="pt-1">
            <FilterPills<GFormFilter>
              label={t("stakes13g.filter.label")}
              value={gform}
              onChange={applyGForm}
              options={[
                { key: "all", label: t("stakes13g.filter.all"), count: gRecent.length },
                {
                  key: "SC 13G",
                  label: t("stakes13g.form13g"),
                  count: gRecent.filter((r) => r.form === "SC 13G").length,
                },
                {
                  key: "SC 13G/A",
                  label: t("stakes13g.form13ga"),
                  count: gRecent.filter((r) => r.form === "SC 13G/A").length,
                },
              ]}
            />
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {gVisible.length === 0 ? (
            <div className="p-4 text-sm text-muted-foreground">{t("stakes13g.empty")}</div>
          ) : (
            <>
              <div className="divide-y">
                {gVisible.map((r, i) => (
                  <div key={i} className="flex items-center gap-3 px-4 py-2.5 text-sm">
                    <span
                      className="w-14 shrink-0 font-mono text-xs text-muted-foreground"
                      title={r.date}
                    >
                      {fmtDateShort(r.date)}
                    </span>
                    <Badge
                      variant="outline"
                      className={cn(
                        "shrink-0 px-1.5 py-0 text-xs",
                        r.form === "SC 13G/A"
                          ? "text-muted-foreground"
                          : "border-sky-500/40 bg-sky-500/10 text-sky-600 dark:text-sky-400",
                      )}
                    >
                      {t(r.form === "SC 13G/A" ? "stakes13g.form13ga" : "stakes13g.form13g")}
                    </Badge>
                    <StakesTypeBadge form={r.form} />
                    <span className="w-32 shrink-0 truncate text-muted-foreground">{r.filer}</span>
                    {r.doc_url ? (
                      <a
                        href={r.doc_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="truncate font-medium underline-offset-2 hover:underline"
                        title={t("stakes13g.filing_link")}
                      >
                        → {r.target}
                      </a>
                    ) : (
                      <span className="truncate font-medium">→ {r.target}</span>
                    )}
                    <StakesPctBadges row={r} />
                    {r.ticker ? (
                      <Link href={`/stock/${r.ticker}`} className="ml-auto shrink-0">
                        <Badge variant="secondary" className="font-mono text-xs">
                          {r.ticker}
                        </Badge>
                      </Link>
                    ) : null}
                  </div>
                ))}
              </div>
              <LoadMoreFooter
                shown={gVisible.length}
                total={gFiltered.length}
                onLoadMore={gPaged.loadMore}
                pageSize={PAGE_SIZE}
              />
            </>
          )}
        </CardContent>
      </Card>

      <p className="text-xs text-muted-foreground">{t("smartmoney.explain")}</p>
      <p className="text-xs text-muted-foreground">{t("stakes13g.explain")}</p>
    </div>
  );
}
