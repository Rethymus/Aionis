"use client";

import Link from "next/link";
import {
  ArrowRightIcon,
  ArrowUpIcon,
  ArrowDownIcon,
  MinusIcon,
  GaugeIcon,
  BarChart3Icon,
  TargetIcon,
  CheckCircle2Icon,
} from "lucide-react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { useI18n } from "@/i18n/provider";
import { aionis } from "@/data/aionis";
import type { DictKey } from "@/i18n/dict";

function Hero() {
  const { t } = useI18n();
  return (
    <section className="space-y-4">
      <Badge variant="secondary" className="rounded-full px-3 py-1 text-xs">
        {t("hero.badge")}
      </Badge>
      <h1 className="text-4xl font-bold tracking-tight text-balance md:text-5xl">
        {t("hero.title")}
      </h1>
      <p className="max-w-2xl text-pretty text-muted-foreground md:text-lg">
        {t("hero.subtitle")}
      </p>
    </section>
  );
}

function KpiCards() {
  const { t } = useI18n();
  const items: { label: DictKey; value: string; tone: "muted" | "emerald" | "amber" }[] = [
    { label: "kpi.combined_ic", value: aionis.metrics.combined_ic.toFixed(4), tone: "muted" },
    { label: "kpi.n_months", value: String(aionis.metrics.n_months), tone: "muted" },
    { label: "kpi.p_value", value: aionis.metrics.p.toFixed(3), tone: "muted" },
    { label: "kpi.verdict", value: aionis.metrics.jt_look1, tone: "amber" },
    { label: "kpi.h6", value: aionis.metrics.h6, tone: "emerald" },
  ];
  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
      {items.map((it) => (
        <Card key={it.label} className="overflow-hidden">
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">{t(it.label)}</p>
            <p
              className={cn(
                "mt-1 text-lg font-semibold tracking-tight tabular-nums md:text-xl",
                it.tone === "emerald" && "text-emerald-600 dark:text-emerald-400",
                it.tone === "amber" && "text-amber-600 dark:text-amber-400",
              )}
            >
              {it.value}
            </p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

function ScoreTicker() {
  const { t } = useI18n();
  const items = aionis.picks;
  const row = (
    <div className="flex items-center">
      {items.map((p) => (
        <span key={p.ticker} className="inline-flex items-center gap-1.5 px-4 text-xs">
          <span className="font-medium">{p.ticker}</span>
          <Badge
            variant="outline"
            className="px-1 py-0 text-[10px] font-normal text-muted-foreground"
          >
            {p.region.toUpperCase()}
          </Badge>
          <span className="tabular-nums text-muted-foreground">
            {p.score > 0 ? "+" : ""}
            {p.score.toFixed(2)}
          </span>
        </span>
      ))}
    </div>
  );
  return (
    <Card className="overflow-hidden py-0">
      <div className="flex items-center gap-2 border-b px-4 py-2">
        <span className="size-1.5 animate-pulse rounded-full bg-emerald-500" />
        <span className="text-xs font-medium text-muted-foreground">
          {t("ticker.label")}
        </span>
      </div>
      <div className="group relative h-9 w-full overflow-hidden">
        <div className="animate-marquee group-hover:[animation-play-state:paused] absolute flex h-full items-center whitespace-nowrap">
          {row}
          <div aria-hidden>{row}</div>
        </div>
      </div>
    </Card>
  );
}

function RankChange({ change }: { change: number | null }) {
  if (change === null || change === 0) {
    return (
      <span className="inline-flex items-center gap-0.5 text-xs text-muted-foreground">
        <MinusIcon className="size-3" />
      </span>
    );
  }
  const up = change > 0;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-0.5 text-xs tabular-nums",
        up ? "text-emerald-600 dark:text-emerald-400" : "text-rose-600 dark:text-rose-400",
      )}
    >
      {up ? <ArrowUpIcon className="size-3" /> : <ArrowDownIcon className="size-3" />}
      {Math.abs(change)}
    </span>
  );
}

function PicksPreview() {
  const { t } = useI18n();
  const top5 = aionis.picks.slice(0, 5);
  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between gap-2 space-y-0">
        <div className="space-y-1">
          <CardTitle className="flex items-center gap-2">
            {t("module.picks.title")}
          </CardTitle>
          <CardDescription>{t("module.picks.window")}</CardDescription>
        </div>
        <Link
          href="/picks"
          className="inline-flex shrink-0 items-center gap-1 text-xs font-medium text-muted-foreground hover:text-foreground"
        >
          {t("module.picks.cta")}
        </Link>
      </CardHeader>
      <CardContent>
        <div className="divide-y">
          {top5.map((p) => (
            <div key={`${p.region}-${p.ticker}`} className="flex items-center gap-3 py-2.5">
              <span className="w-6 text-sm font-semibold tabular-nums text-muted-foreground">
                {p.rank}
              </span>
              <div className="flex min-w-0 flex-col">
                <span className="truncate text-sm font-medium">{p.name || p.ticker}</span>
                <span className="font-mono text-[10px] text-muted-foreground">{p.ticker}</span>
              </div>
              <Badge variant="secondary" className="px-1.5 py-0 text-[10px]">
                {t(p.region === "us" ? "picks.region.us" : "picks.region.cn")}
              </Badge>
              <span className="ml-auto font-mono text-sm tabular-nums">
                {p.score > 0 ? "+" : ""}
                {p.score.toFixed(2)}
              </span>
              <span className="w-10 text-right">
                <RankChange change={p.rank_change} />
              </span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function FunnelCards() {
  const { t } = useI18n();

  // One representative stat per hub — the four-question closed loop.
  const latestVix = aionis.marketContext.vix_series[aionis.marketContext.vix_series.length - 1]?.vix ?? 0;

  const topPick = aionis.picks[0];
  const topPickDisplay = topPick ? `${topPick.ticker} ${topPick.score > 0 ? "+" : ""}${topPick.score.toFixed(2)}` : "N/A";

  const totalFilings = aionis.smartMoney.total_filings ?? 0;

  const usEce = aionis.calibrationReliability.regions?.us?.pooled_ece ?? 0;
  const cnEce = aionis.calibrationReliability.regions?.cn?.pooled_ece ?? 0;

  const cards: {
    n: string;
    href: string;
    icon: React.ReactNode;
    titleKey: DictKey;
    introKey: DictKey;
    stat: string;
    tone: "muted" | "amber" | "emerald";
  }[] = [
    {
      n: "①",
      href: "/regime",
      icon: <GaugeIcon className="size-4" />,
      titleKey: "nav.group.regime",
      introKey: "regime_hub.intro",
      stat: `VIX ${latestVix.toFixed(1)}`,
      tone: "muted",
    },
    {
      n: "②",
      href: "/picks",
      icon: <TargetIcon className="size-4" />,
      titleKey: "nav.group.picks",
      introKey: "picks_hub.intro",
      stat: topPickDisplay,
      tone: "emerald",
    },
    {
      n: "③",
      href: "/confirmation",
      icon: <BarChart3Icon className="size-4" />,
      titleKey: "nav.group.confirm",
      introKey: "confirmation_hub.intro",
      stat: `${totalFilings} filings`,
      tone: "muted",
    },
    {
      n: "④",
      href: "/track",
      icon: <CheckCircle2Icon className="size-4" />,
      titleKey: "nav.group.track",
      introKey: "track_hub.intro",
      stat: `ECE ${((usEce + cnEce) / 2).toFixed(3)}`,
      tone: "amber",
    },
  ];

  return (
    <section className="space-y-3">
      <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
        <h2 className="text-base font-semibold tracking-tight">{t("overview.loop.title")}</h2>
        <p className="text-xs text-muted-foreground">{t("overview.loop.subtitle")}</p>
      </div>
      <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-4">
        {cards.map((c) => (
          <Link key={c.href} href={c.href} className="group">
            <Card className="h-full transition-colors group-hover:border-foreground/20">
              <CardHeader className="space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex size-8 items-center justify-center rounded-md bg-muted text-muted-foreground">
                    {c.icon}
                  </div>
                  <span className="text-base font-semibold tabular-nums text-muted-foreground/70">
                    {c.n}
                  </span>
                </div>
                <CardTitle className="text-base">{t(c.titleKey)}</CardTitle>
                <CardDescription className="line-clamp-3 text-xs">{t(c.introKey)}</CardDescription>
              </CardHeader>
              <CardContent>
                <p
                  className={cn(
                    "text-sm font-medium tabular-nums",
                    c.tone === "emerald" && "text-emerald-600 dark:text-emerald-400",
                    c.tone === "amber" && "text-amber-600 dark:text-amber-400",
                  )}
                >
                  {c.stat}
                </p>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
      <p className="text-center text-[11px] text-muted-foreground">{t("overview.loop.feedback")}</p>
    </section>
  );
}

export function Overview() {
  return (
    <div className="space-y-6 p-4 md:p-6">
      <Hero />
      <KpiCards />
      <ScoreTicker />
      <PicksPreview />
      <FunnelCards />
    </div>
  );
}
