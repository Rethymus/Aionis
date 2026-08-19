"use client";

import Link from "next/link";
import {
  ArrowRightIcon,
  ArrowUpIcon,
  ArrowDownIcon,
  MinusIcon,
  GlobeIcon,
  FlaskConicalIcon,
  GaugeCircleIcon,
  GavelIcon,
  ShieldCheckIcon,
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
import { ResearchGlance } from "./research-glance";
import { ProvenanceAnchor } from "./provenance-anchor";
import { TrustRibbon } from "./trust-ribbon";

// Paradigm α — the Overview IS the validity-argument chain, not a collage with
// a chain buried at the bottom. The composition leads with the verdict (the
// whole point of a falsifiable claim), then unfolds the chain that produced it.
// Layout: Verdict anchor → 4-segment chain (context→evidence→validity→verdict)
// → corroboration + evidence detail folded under the spine → guard band.

function VerdictAnchor() {
  const { t } = useI18n();
  const m = aionis.metrics;
  const ci = m.ci_lo !== null && m.ci_hi !== null ? `[${m.ci_lo.toFixed(4)}, ${m.ci_hi.toFixed(4)}]` : "—";
  // Null is the intended outcome — the anchor states it plainly
  // rather than apologizing for it. IC≈0 + CI bracketing zero = honest null.
  return (
    <Card className="overflow-hidden border-foreground/15">
      <CardContent className="grid gap-4 p-5 md:grid-cols-[auto_1fr_auto] md:items-center">
        <div className="flex items-center gap-3">
          <div className="flex size-11 items-center justify-center rounded-lg bg-muted">
            <ScaleIcon className="size-5 text-muted-foreground" />
          </div>
          <div>
            <p className="text-xs text-muted-foreground">{t("overview.verdict.claim")}</p>
            <p className="text-sm font-medium leading-tight">{t("overview.verdict.question")}</p>
          </div>
        </div>
        <div className="flex flex-wrap items-baseline gap-x-6 gap-y-1">
          <div>
            <p className="text-xs text-muted-foreground">{t("kpi.combined_ic")}</p>
            <p className="font-mono text-2xl font-semibold tabular-nums">
              {m.combined_ic > 0 ? "+" : ""}{m.combined_ic.toFixed(4)}
            </p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">95% CI</p>
            <p className="font-mono text-sm font-medium tabular-nums text-muted-foreground">{ci}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">{t("kpi.p_value")}</p>
            <p className="font-mono text-sm font-medium tabular-nums text-muted-foreground">{m.p.toFixed(3)}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">{t("kpi.n_months")}</p>
            <p className="font-mono text-sm font-medium tabular-nums text-muted-foreground">{m.n_months}</p>
          </div>
        </div>
        <div className="flex flex-col items-start gap-1 md:items-end">
          {/* NULL = the intended outcome (NOT a failure). The prior
              amber tint signaled "warning/error" — a framing that fights the
              null.note directly below ("not a failure"). A glance reads color
              faster than text, so the amber short-circuited the honest framing.
              Slate/blue reads as "settled/concluded" (the verdict landed), while
              amber is reserved for genuine statistical cautions (J-T gate,
              power-floor) elsewhere — a semantic split, not a blanket recolor. */}
          <Badge variant="secondary" className="bg-slate-500/15 text-slate-600 dark:text-slate-300">
            {t("overview.verdict.null")}
          </Badge>
          <span className="text-xs text-muted-foreground">{t("overview.verdict.null.note")}</span>
        </div>
      </CardContent>
      {/* The verdict's birth certificate — embedded in the same card (a claim
          and how it was frozen are one object; three stacked badge cards read
          as clutter before the argument chain even began). */}
      <CardContent className="pt-0">
        <ProvenanceAnchor embedded />
      </CardContent>
    </Card>
  );
}

function ChainSegment({
  href,
  icon,
  titleKey,
  stat,
  statTone,
  detail,
}: {
  href: string;
  icon: React.ReactNode;
  titleKey: DictKey;
  stat: string;
  statTone: "muted" | "amber" | "emerald";
  detail: React.ReactNode;
}) {
  const { t } = useI18n();
  return (
    <Link href={href} className="group block">
      <Card className="h-full transition-colors group-hover:border-foreground/25">
        <CardHeader className="space-y-2">
          <div className="flex items-center gap-2">
            <div className="flex size-7 items-center justify-center rounded-md bg-muted text-muted-foreground">
              {icon}
            </div>
            <CardTitle className="text-sm">{t(titleKey)}</CardTitle>
          </div>
          <p
            className={cn(
              "font-mono text-lg font-semibold tabular-nums",
              statTone === "emerald" && "text-emerald-600 dark:text-emerald-400",
              statTone === "amber" && "text-amber-600 dark:text-amber-400",
            )}
          >
            {stat}
          </p>
        </CardHeader>
        <CardContent className="pt-0">{detail}</CardContent>
      </Card>
    </Link>
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
        up ? "text-up" : "text-down",
      )}
    >
      {up ? <ArrowUpIcon className="size-3" /> : <ArrowDownIcon className="size-3" />}
      {Math.abs(change)}
    </span>
  );
}

function MiniPicks() {
  const { t } = useI18n();
  const top4 = aionis.picks.slice(0, 4);
  return (
    <div className="space-y-1">
      {top4.map((p) => (
        <Link
          key={`${p.region}-${p.ticker}`}
          href={`/stock/${p.ticker}`}
          className="flex items-center gap-2 rounded-sm text-xs hover:underline"
        >
          {/* Name grows to fill, truncates only if truly starved (was w-14/56px
              which chopped "CENTERPOINT ENERGY INC" to "CENTERPOIN…"). The
              ticker sibling stays fixed-width so the row stays scannable. */}
          <span className="min-w-0 flex-1 truncate font-medium" title={p.name || p.ticker}>
            {p.name || p.ticker}
          </span>
          <span className="shrink-0 font-mono text-xs text-muted-foreground">{p.ticker}</span>
          <span className="ml-auto shrink-0 font-mono tabular-nums">
            {p.score > 0 ? "+" : ""}{p.score.toFixed(2)}
          </span>
          <span className="w-6 shrink-0 text-right">
            <RankChange change={p.rank_change} />
          </span>
        </Link>
      ))}
      <p className="pt-1 text-xs text-muted-foreground">{t("overview.chain.evidence.detail")}</p>
    </div>
  );
}

function MiniCorroboration() {
  const { t } = useI18n();
  const filings = aionis.smartMoney.total_filings ?? 0;
  const latest = aionis.smartMoney.latest_date ?? "—";
  const cotLatest = aionis.cot.latest_date ?? "—";
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-xs">
        <span className="text-muted-foreground">{t("nav.smartmoney")}</span>
        <span className="font-mono tabular-nums">{filings} · {latest}</span>
      </div>
      <div className="flex items-center justify-between text-xs">
        <span className="text-muted-foreground">{t("nav.positioning")}</span>
        <span className="font-mono tabular-nums">{cotLatest}</span>
      </div>
      <p className="pt-0.5 text-xs text-muted-foreground">{t("overview.chain.corroboration.note")}</p>
    </div>
  );
}

function ArgumentChain() {
  const { t } = useI18n();
  const latestVix = aionis.marketContext.vix_series[aionis.marketContext.vix_series.length - 1]?.vix ?? 0;
  const usEce = aionis.calibrationReliability.regions?.us?.pooled_ece ?? 0;
  const cnEce = aionis.calibrationReliability.regions?.cn?.pooled_ece ?? 0;
  const m = aionis.metrics;

  return (
    <section className="space-y-3">
      <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
        <h2 className="text-base font-semibold tracking-tight">{t("overview.loop.title")}</h2>
        <p className="text-xs text-muted-foreground">{t("overview.loop.subtitle")}</p>
      </div>
      <div className="grid items-stretch gap-2 md:grid-cols-4">
        <ChainSegment
          href="/regime"
          icon={<GlobeIcon className="size-3.5" />}
          titleKey="nav.group.context"
          stat={`VIX ${latestVix.toFixed(1)}`}
          statTone="muted"
          detail={<p className="text-xs leading-snug text-muted-foreground">{t("overview.chain.context.detail")}</p>}
        />
        <ChainSegment
          href="/picks"
          icon={<FlaskConicalIcon className="size-3.5" />}
          titleKey="nav.group.evidence"
          stat={`${m.n_picks_total} picks`}
          statTone="emerald"
          detail={<MiniPicks />}
        />
        <ChainSegment
          href="/track"
          icon={<GaugeCircleIcon className="size-3.5" />}
          titleKey="nav.group.validity"
          stat={`ECE ${((usEce + cnEce) / 2).toFixed(3)}`}
          statTone="amber"
          detail={<p className="text-xs leading-snug text-muted-foreground">{t("overview.chain.validity.detail")}</p>}
        />
        <ChainSegment
          href="/track#evidence"
          icon={<GavelIcon className="size-3.5" />}
          titleKey="overview.chain.verdict.label"
          stat={m.verdict}
          statTone="muted"
          detail={<p className="text-xs leading-snug text-muted-foreground">{t("overview.chain.verdict.detail")}</p>}
        />
      </div>
      {/* Corroboration ribbon — the second independent evidence source, folded
          under the spine rather than a 5th peer column. */}
      <Link href="/confirmation" className="group block">
        <Card className="border-dashed transition-colors group-hover:border-foreground/20">
          <CardContent className="flex flex-wrap items-center gap-x-6 gap-y-2 p-3">
            <div className="flex min-w-[180px] flex-1 flex-col">
              <MiniCorroboration />
            </div>
          </CardContent>
        </Card>
      </Link>
    </section>
  );
}

function GuardBand() {
  const { t } = useI18n();
  return (
    <Link href="/discipline" className="group block">
      <Card className="border-dashed transition-colors group-hover:border-foreground/20">
        <CardContent className="flex flex-wrap items-center gap-x-4 gap-y-2 p-3">
          <div className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
            <ShieldCheckIcon className="size-3.5" />
            {t("nav.group.guard")}
          </div>
          <div className="flex flex-wrap items-center gap-1.5">
            {["PIT", "embargo", "H6", "provenance"].map((g) => (
              <Badge key={g} variant="outline" className="px-1.5 py-0 text-xs font-normal text-muted-foreground">
                {g}
              </Badge>
            ))}
          </div>
          <span className="ml-auto hidden text-xs text-muted-foreground md:block">
            {t("overview.guard.spans")}
          </span>
        </CardContent>
      </Card>
    </Link>
  );
}

function Hero() {
  const { t } = useI18n();
  return (
    <section className="space-y-3">
      <Badge variant="secondary" className="rounded-full px-3 py-1 text-xs">
        {t("hero.badge")}
      </Badge>
      <h1 className="text-3xl font-bold tracking-tight text-balance md:text-4xl">
        {t("hero.title")}
      </h1>
      <p className="max-w-2xl text-pretty text-sm text-muted-foreground md:text-base">
        {t("hero.subtitle")}
      </p>
    </section>
  );
}

export function Overview() {
  return (
    <div className="space-y-5 p-4 md:p-6">
      <Hero />
      {/* Affirmative trust basis next to the verdict it underwrites — the
          complement to the hero's "non-investment advice" disclaimer. */}
      <TrustRibbon />
      {/* The verdict is the anchor — everything else is the argument for it.
          Its birth certificate (frozen-before-result provenance) is embedded
          inside the verdict card, not stacked as a third badge card. */}
      <VerdictAnchor />
      <ArgumentChain />
      {/* Why-null + what-was-tested, at a glance (deep-dives on /track, /themes). */}
      <ResearchGlance />
      <GuardBand />
    </div>
  );
}
