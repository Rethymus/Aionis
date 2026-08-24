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
  SearchIcon,
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

/** Aligned-site home hero: centered 34→52px headline with a brand-colored
 *  accent span, radial glow + grid decorative layers, a 560px search box that
 *  opens the command palette, and mono pill chips. */
function Hero() {
  const { t } = useI18n();
  const openPalette = () =>
    window.dispatchEvent(new Event("aionis:open-palette"));
  return (
    <section className="relative -mt-8 pt-14 pb-4 text-center md:pt-20">
      <div className="hero-glow pointer-events-none absolute inset-0" aria-hidden="true" />
      <div className="hero-grid" aria-hidden="true" />
      <div className="relative">
        <h1 className="mx-auto mt-5 max-w-[16em] text-[34px] leading-[1.15] font-bold tracking-[-0.035em] text-balance md:text-[52px]">
          <span className="text-brand">{t("hero.title.accent")}</span>
          {t("hero.title.rest")}
        </h1>
        <p className="mx-auto mt-4 max-w-[36em] text-[14px] leading-relaxed text-sub md:text-[15px]">
          {t("hero.subtitle")}
        </p>
        <div className="mt-7">
          <button
            type="button"
            onClick={openPalette}
            className="relative mx-auto flex h-12 w-full max-w-[560px] cursor-pointer items-center rounded-xl border border-line bg-card pr-24 pl-11 text-left shadow-[0_1px_2px_rgba(0,0,0,0.04),0_8px_24px_-12px_rgba(0,0,0,0.12)] transition-colors hover:border-faint"
          >
            <SearchIcon className="pointer-events-none absolute left-4 size-[17px] text-faint" />
            <span className="truncate text-[14px] text-mute">
              {t("overview.search.placeholder")}
            </span>
            <span className="pointer-events-none absolute right-4 flex items-center gap-1 font-mono text-[11px] text-faint">
              ⌘K
            </span>
          </button>
        </div>
        <div className="mt-4 flex flex-wrap items-center justify-center gap-2">
          {(
            [
              ["/institutions", t("nav.institutions")],
              ["/congress", t("nav.congress")],
              ["/insiders", t("nav.insiders")],
              ["/ipo", t("nav.ipo")],
            ] as const
          ).map(([href, label]) => (
            <Link
              key={href}
              href={href}
              className="rounded-full border border-line bg-card px-3 py-1 font-mono text-[12px] font-semibold text-sub transition-colors hover:border-faint hover:text-ink"
            >
              {label}
            </Link>
          ))}
          <span className="rounded-full border border-line bg-card px-3 py-1 font-semibold text-[12px] text-sub">
            {t("hero.badge")}
          </span>
        </div>
        <StatBand />
      </div>
    </section>
  );
}

/** Centered mono stat band (720px, hairline dividers between cells). */
function StatBand() {
  const { t } = useI18n();
  const m = aionis.metrics;
  const vix = aionis.marketContext.vix_series;
  const latestVix = vix[vix.length - 1]?.vix ?? 0;
  const sm = aionis.smartMoney;
  const cells: { label: string; value: string }[] = [
    { label: t("overview.stat.picks"), value: String(m.n_picks_total) },
    { label: t("overview.stat.months"), value: String(m.n_months) },
    { label: t("overview.stat.vix"), value: latestVix.toFixed(1) },
    { label: t("overview.stat.filings"), value: String(sm.total_filings ?? 0) },
  ];
  return (
    <div className="mx-auto mt-10 flex max-w-[720px] flex-wrap items-stretch justify-center gap-y-4">
      {cells.map((c, i) => (
        <div
          key={c.label}
          className={`px-5 text-center md:px-7 ${i > 0 ? "border-l border-line" : ""}`}
        >
          <div className="text-[11px] text-mute">{c.label}</div>
          <div className="font-mono text-[20px] font-bold tracking-tight md:text-[24px]">
            {c.value}
          </div>
        </div>
      ))}
    </div>
  );
}

/** Market snapshot cards (3-col grid, mono 22px values, up/down deltas). */
function MarketCards() {
  const { t } = useI18n();
  const vix = aionis.marketContext.vix_series;
  const ms = aionis.marketContext.market_series;
  const lastVix = vix[vix.length - 1]?.vix ?? 0;
  const prevVix = vix[vix.length - 2]?.vix ?? 0;
  const vixDelta = lastVix - prevVix;
  const lastIdx = ms[ms.length - 1];
  const ctx = aionis.politicianTradesTx;
  const cards: {
    label: string;
    value: string;
    delta: string;
    tone: "up" | "down" | "flat";
    sub: string;
  }[] = [
    {
      label: "VIX",
      value: lastVix.toFixed(1),
      delta: `${vixDelta > 0 ? "+" : ""}${vixDelta.toFixed(1)}`,
      tone: vixDelta > 0.05 ? "up" : vixDelta < -0.05 ? "down" : "flat",
      sub: t("overview.market.vs_prev"),
    },
    {
      label: t("overview.market.index"),
      value: lastIdx ? lastIdx.index.toFixed(2) : "—",
      delta: lastIdx ? `${(lastIdx.ret * 100) > 0 ? "+" : ""}${(lastIdx.ret * 100).toFixed(2)}%` : "—",
      tone: lastIdx && lastIdx.ret > 0 ? "up" : "down",
      sub: lastIdx?.month ?? "—",
    },
    {
      label: t("overview.market.trades"),
      value: String(ctx.total ?? 0),
      delta: String(ctx.year ?? "—"),
      tone: "flat",
      sub: t("nav.congress"),
    },
  ];
  return (
    <section className="grid grid-cols-1 gap-3 md:grid-cols-3">
      {cards.map((c) => (
        <div
          key={c.label}
          className="flex items-center justify-between gap-3 rounded-xl border border-line bg-card px-5 py-4"
        >
          <div className="min-w-0">
            <div className="truncate text-[12px] text-mute">{c.label}</div>
            <div className="font-mono text-[22px] font-semibold tracking-tight">
              {c.value}
            </div>
          </div>
          <div className="shrink-0 text-right">
            <div
              className={`text-[12px] font-semibold ${
                c.tone === "up" ? "text-up" : c.tone === "down" ? "text-down" : "text-sub"
              }`}
            >
              {c.delta}
            </div>
            <div className="text-[11px] text-mute">{c.sub}</div>
          </div>
        </div>
      ))}
    </section>
  );
}


/** 数据驾驶舱 — deployed-terminal alignment: the home page opens with a
 *  live-data cockpit (headlines / retail heat / congressional trades)
 *  aggregated CLIENT-SIDE from existing panels — zero new exports, zero
 *  new fetches. The validity-argument narrative continues below it. */
function DataCockpit() {
  const { t } = useI18n();
  const news = aionis.newsFeed.status === "ok" ? aionis.newsFeed.items.slice(0, 5) : [];
  const heat = aionis.redditTrending.status === "ok" ? aionis.redditTrending.tickers.slice(0, 10) : [];
  const ctx = aionis.politicianTradesTx;
  const trades = ctx.status === "ok" ? ctx.transactions.slice(0, 5) : [];
  if (news.length === 0 && heat.length === 0 && trades.length === 0) return null;
  return (
    <section className="grid items-start gap-3 lg:grid-cols-3">
      <Card className="min-w-0 py-0">
        <CardHeader className="border-b">
          <CardTitle className="text-sm">{t("overview.cockpit.news")}</CardTitle>
          <CardDescription className="font-mono text-[11px] tabular-nums">
            {aionis.newsFeed.as_of?.split("T")[0] ?? "—"} · {aionis.newsFeed.n_sources ?? 0} src
          </CardDescription>
        </CardHeader>
        <CardContent className="divide-y p-0">
          {news.map((n) => (
            <a
              key={n.url}
              href={n.url}
              target="_blank"
              rel="noopener noreferrer"
              className="block px-4 py-3 transition-colors hover:bg-soft"
            >
              <p className="truncate text-[13px] font-medium" title={n.title}>{n.title}</p>
              <p className="truncate font-mono text-[11px] text-mute">
                {n.domain} · {n.seendate.slice(5, 10).replace("-", "/")}
              </p>
            </a>
          ))}
        </CardContent>
      </Card>
      <Card className="min-w-0 py-0">
        <CardHeader className="border-b">
          <CardTitle className="text-sm">{t("overview.cockpit.heat")}</CardTitle>
          <CardDescription className="font-mono text-[11px] tabular-nums">
            {aionis.redditTrending.as_of?.split("T")[0] ?? "—"} · top {heat.length}
          </CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          {heat.map((h, i) => {
            const max = heat[0]?.mentions || 1;
            return (
              <div key={h.ticker} className="flex flex-col gap-1.5 border-t border-line2 px-4 py-3 first:border-t-0">
                <div className="flex items-baseline gap-2 text-[13px]">
                  <span className="w-6 flex-none text-right font-mono font-bold text-brand">{i + 1}</span>
                  <span className="min-w-0 flex-1 truncate font-semibold">{h.ticker}</span>
                  <span className="flex-none font-mono font-semibold tabular-nums">{h.mentions}</span>
                </div>
                <div className="flex items-center gap-2.5 pl-8">
                  <div className="h-[5px] flex-1 overflow-hidden rounded bg-line2">
                    <div
                      className="h-full rounded bg-green-fill"
                      style={{ width: `${Math.max(3, (h.mentions / max) * 100)}%` }}
                    />
                  </div>
                </div>
              </div>
            );
          })}
        </CardContent>
      </Card>
      <Card className="min-w-0 py-0">
        <CardHeader className="border-b">
          <CardTitle className="text-sm">{t("overview.cockpit.trades")}</CardTitle>
          <CardDescription className="font-mono text-[11px] tabular-nums">
            {ctx.total ?? 0} tx · {ctx.year ?? "—"}
          </CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          {trades.map((r) => (
            <div key={`${r.doc_url}-${r.transaction_date}-${r.ticker || "x"}`} className="flex items-center gap-2 border-t border-line2 px-4 py-3 first:border-t-0 transition-colors hover:bg-soft">
              <span className="w-16 shrink-0 truncate text-[11px] font-medium" title={r.member}>
                {r.member.split(",")[0]}
              </span>
              <span className="font-mono text-[13px] font-semibold">{r.ticker || "—"}</span>
              <span
                className={
                  "rounded-[3px] px-1 font-mono text-[10px] font-semibold " +
                  (r.direction === "buy" ? "badge-up border" : "badge-down border")
                }
              >
                {r.direction === "buy" ? "B" : "S"}
              </span>
              <span className="ml-auto shrink-0 font-mono text-[11px] text-mute tabular-nums">
                {r.transaction_date.slice(5).replace("-", "/")}
              </span>
            </div>
          ))}
        </CardContent>
      </Card>
    </section>
  );
}

export function Overview() {
  return (
    <div className="flex flex-col gap-10">
      <Hero />
      <MarketCards />
      <DataCockpit />
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
