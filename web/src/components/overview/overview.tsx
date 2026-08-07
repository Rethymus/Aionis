"use client";

import Link from "next/link";
import {
  ArrowRightIcon,
  ArrowUpIcon,
  ArrowDownIcon,
  MinusIcon,
  ShieldCheckIcon,
  GaugeIcon,
  ScaleIcon,
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

function ModuleCards() {
  const { t } = useI18n();
  const cards: {
    href: string;
    icon: React.ReactNode;
    titleKey: DictKey;
    windowKey: DictKey;
    ctaKey: DictKey;
    stat: string;
    tone: "muted" | "amber" | "emerald";
  }[] = [
    {
      href: "/evidence",
      icon: <ScaleIcon className="size-4" />,
      titleKey: "module.evidence.title",
      windowKey: "module.evidence.window",
      ctaKey: "module.evidence.cta",
      stat: "14 / 14 null",
      tone: "muted",
    },
    {
      href: "/power-floor",
      icon: <GaugeIcon className="size-4" />,
      titleKey: "module.powerfloor.title",
      windowKey: "module.powerfloor.window",
      ctaKey: "module.evidence.cta",
      stat: "look-3 · 36.2y",
      tone: "amber",
    },
    {
      href: "/discipline",
      icon: <ShieldCheckIcon className="size-4" />,
      titleKey: "module.discipline.title",
      windowKey: "module.discipline.window",
      ctaKey: "module.evidence.cta",
      stat: "H6 PASS · PIT",
      tone: "emerald",
    },
  ];
  return (
    <div className="grid gap-3 md:grid-cols-3">
      {cards.map((c) => (
        <Link key={c.href} href={c.href} className="group">
          <Card className="h-full transition-colors group-hover:border-foreground/20">
            <CardHeader className="space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex size-8 items-center justify-center rounded-md bg-muted text-muted-foreground">
                  {c.icon}
                </div>
                <span
                  className={cn(
                    "text-xs font-medium tabular-nums",
                    c.tone === "emerald" && "text-emerald-600 dark:text-emerald-400",
                    c.tone === "amber" && "text-amber-600 dark:text-amber-400",
                  )}
                >
                  {c.stat}
                </span>
              </div>
              <CardTitle className="text-base">{t(c.titleKey)}</CardTitle>
              <CardDescription>{t(c.windowKey)}</CardDescription>
            </CardHeader>
            <CardContent>
              <span className="inline-flex items-center gap-1 text-xs font-medium text-muted-foreground group-hover:text-foreground">
                {t(c.ctaKey)}
                <ArrowRightIcon className="size-3 transition-transform group-hover:translate-x-0.5" />
              </span>
            </CardContent>
          </Card>
        </Link>
      ))}
    </div>
  );
}

export function Overview() {
  return (
    <div className="space-y-6 p-4 md:p-6">
      <Hero />
      <KpiCards />
      <ScoreTicker />
      <PicksPreview />
      <ModuleCards />
    </div>
  );
}
