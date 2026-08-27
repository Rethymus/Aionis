"use client";

import Link from "next/link";
import {
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
  NewspaperIcon,
  FlameIcon,
  Building2Icon,
  NetworkIcon,
  UserIcon,
  LandmarkIcon,
  UserCogIcon,
  RocketIcon,
  FlagIcon,
  LayoutGridIcon,
  ZapIcon,
  BriefcaseIcon,
  FileTextIcon,
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
// Home star-investors digest (~2KB — top-8 managers derived at export time
// from the committed form13f panel). The full 13F book (~650KB) stays in its
// dedicated module for /institutions + /manager; the landing page never pays
// for it. See data/aionis/form13f-stars.ts.
import { form13fStars } from "@/data/aionis/form13f-stars";
import { fmtDateShort, fmtInt, fmtUsd } from "@/lib/format";
import { AvatarInitials } from "@/components/stream/avatar-initials";
import { CATEGORY_LABEL } from "@/components/events/events-view";
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

/** Centered mono stat band (720px, hairline dividers between cells) —
 *  directory-SCALE counts (deployed-terminal parity): every number is a real
 *  row count of a committed panel. companies_dir / filers13f are dedicated
 *  heavy modules deliberately NOT imported into the home barrel chain — their
 *  counts come from data_health.rows (len() of the exported list at export
 *  time, contract-pinned by test_data_health_rows_reconcile_with_source_lists). */
function StatBand() {
  const { t } = useI18n();
  const dh = (key: string) =>
    aionis.dataHealth.panels.find((p) => p.key === key)?.rows ?? null;
  const ctx = aionis.politicianTradesTx;
  const cells: { label: string; value: number | null }[] = [
    { label: t("overview.stat.companies"), value: dh("companies_dir") },
    { label: t("overview.stat.filers"), value: dh("filers13f") },
    {
      label: t("overview.stat.stars"),
      value: form13fStars.status === "ok" ? form13fStars.n_managers : null,
    },
    { label: t("overview.stat.trades"), value: ctx.status === "ok" ? ctx.total : null },
    {
      label: t("overview.stat.reddit"),
      value: aionis.redditTrending.status === "ok" ? aionis.redditTrending.count_declared : null,
    },
  ];
  return (
    <div className="mx-auto mt-10 flex max-w-[840px] flex-wrap items-stretch justify-center gap-y-4">
      {cells.map((c, i) => (
        <div
          key={c.label}
          className={`px-4 text-center md:px-6 ${i > 0 ? "border-l border-line" : ""}`}
        >
          <div className="text-[11px] text-mute">{c.label}</div>
          <div className="font-mono text-[20px] font-bold tracking-tight tabular-nums md:text-[24px]">
            {c.value != null ? fmtInt(c.value) : "—"}
          </div>
        </div>
      ))}
    </div>
  );
}

/** 机构最新申报 (deployed-terminal anatomy): the latest EDGAR filings from the
 *  existing filing_stream panel — form chip + filer (truncated) + MM/DD mono
 *  right-aligned. The panel carries filed_date only (no intraday time field),
 *  so rows show MM/DD honestly. Zero new data paths; renders as one card in
 *  the home module grid (its own <section> wrapper lives in Overview()). */
function FilingStrip() {
  const { t } = useI18n();
  const f = aionis.filingStream;
  const rows = f.status === "ok" ? f.filings.slice(0, 10) : [];
  if (rows.length === 0) return null;
  return (
    <div className="overflow-hidden rounded-xl border border-line bg-card">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 border-b border-line2 px-5 py-4">
        <h2 className="text-[17px] font-semibold tracking-[-0.02em]">
          {t("overview.filings.title")}
        </h2>
        <span className="font-mono text-[11px] text-mute tabular-nums">
          {fmtInt(f.n_visible ?? rows.length)} · {f.as_of?.split("T")[0] ?? "—"}
        </span>
        <Link
          href="/events"
          className="ml-auto text-[13px] font-semibold text-brand hover:text-brand-hover"
        >
          {t("overview.filings.link")} →
        </Link>
      </div>
      {rows.map((r, i) => (
        <a
          key={`${r.doc_url}-${i}`}
          href={r.doc_url}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-baseline gap-3 border-t border-line2 px-5 py-[10px] transition-colors hover:bg-soft first:border-t-0"
        >
          <span className="flex-none rounded border border-line bg-soft px-1.5 py-px font-mono text-[10px] font-semibold text-sub">
            {r.form}
          </span>
          <span className="min-w-0 flex-1 truncate text-[13px] text-ink" title={r.who}>
            {r.who}
          </span>
          {r.ticker ? (
            <span className="flex-none font-mono text-[11px] font-semibold text-brand">
              {r.ticker}
            </span>
          ) : null}
          <span className="w-10 flex-none text-right font-mono text-[11px] text-mute tabular-nums">
            {fmtDateShort(r.filed_date)}
          </span>
        </a>
      ))}
    </div>
  );
}

/** 最新举牌 — SC 13G passive-stake stream (deployed-terminal row anatomy):
 *  bordered mono form chip + ticker (bold mono) + pct-of-class + MM/DD, row
 *  links to the SEC primary doc. The panel is the 13G family only (13D lives
 *  in smart_money), so chips read 13G / 13G/A; pct_now is the parsed
 *  percent-of-class (null = honest miss → "—"). */
function StakesCard() {
  const { t } = useI18n();
  const s = aionis.stakes13g;
  const rows = s.status === "ok" ? s.filings.slice(0, 5) : [];
  if (rows.length === 0) return null;
  return (
    <div className="overflow-hidden rounded-xl border border-line bg-card">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 border-b border-line2 px-5 py-4">
        <h2 className="text-[17px] font-semibold tracking-[-0.02em]">
          {t("overview.stakes.title")}
        </h2>
        <span className="font-mono text-[11px] text-mute tabular-nums">
          {s.as_of ?? "—"}
        </span>
        <Link
          href="/stakes"
          className="ml-auto text-[13px] font-semibold text-brand hover:text-brand-hover"
        >
          {t("overview.stakes.more")} →
        </Link>
      </div>
      {rows.map((r, i) => (
        <a
          key={`${r.doc_url}-${i}`}
          href={r.doc_url}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-2.5 border-t border-line2 px-5 py-3 transition-colors hover:bg-soft first:border-t-0"
        >
          <span className="flex-none rounded border border-line bg-soft px-1.5 py-px font-mono text-[10px] font-semibold text-sub">
            {r.form.replace("SC ", "")}
          </span>
          <span
            className="min-w-0 flex-1 truncate font-mono text-[13px] font-bold text-ink"
            title={r.ticker ?? r.target}
          >
            {r.ticker ?? r.target}
          </span>
          <span className="flex-none font-mono text-[12px] tabular-nums">
            {r.pct_now != null ? `${r.pct_now.toFixed(1)}%` : "—"}
          </span>
          <span className="w-10 flex-none text-right font-mono text-[11px] text-mute tabular-nums">
            {fmtDateShort(r.date)}
          </span>
        </a>
      ))}
    </div>
  );
}

/** 近期 IPO — S-1 / S-1/A / 424B4 registration stream (the panel whose status
 *  enum IS the reference pill pair: filed → 即将上市, priced → 已定价; Form D
 *  is Reg-D private placements with status new/amendment, a different thing).
 *  Honest degradation vs the reference row: the panel carries no exchange or
 *  price (424B4 price parsing is not built) — the sub-line shows ticker · form
 *  instead, never a fabricated $ or venue. */
const MONTHS_EN = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"];

function IpoCard() {
  const { t } = useI18n();
  const f = aionis.ipo;
  const rows = f.status === "ok" ? f.filings.slice(0, 5) : [];
  if (rows.length === 0) return null;
  return (
    <div className="overflow-hidden rounded-xl border border-line bg-card">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 border-b border-line2 px-5 py-4">
        <h2 className="text-[17px] font-semibold tracking-[-0.02em]">
          {t("overview.ipo.title")}
        </h2>
        <span className="font-mono text-[11px] text-mute tabular-nums">
          {fmtInt(f.total)} · {f.as_of ?? "—"}
        </span>
        <Link
          href="/ipo"
          className="ml-auto text-[13px] font-semibold text-brand hover:text-brand-hover"
        >
          {t("overview.ipo.cal")} →
        </Link>
      </div>
      {rows.map((r, i) => {
        const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(r.filed_date);
        const day = m ? m[3] : "—";
        const mon = m ? MONTHS_EN[Number(m[2]) - 1] ?? "—" : "—";
        const priced = r.status === "priced";
        return (
          <a
            key={`${r.doc_url}-${i}`}
            href={r.doc_url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-3 border-t border-line2 px-5 py-3 transition-colors hover:bg-soft first:border-t-0"
          >
            <span className="flex h-9 w-9 flex-none flex-col items-center justify-center rounded-lg bg-soft leading-none">
              <span className="font-mono text-[13px] font-bold text-ink tabular-nums">{day}</span>
              <span className="mt-0.5 font-mono text-[9px] text-mute">{mon}</span>
            </span>
            <span className="min-w-0 flex-1">
              <span className="block truncate text-[13px] font-medium text-ink" title={r.company}>
                {r.company}
              </span>
              <span className="block truncate font-mono text-[11px] text-mute">
                {r.ticker || "—"} · {r.form}
              </span>
            </span>
            <span
              className={cn(
                "flex-none rounded-[4px] px-1.5 py-px text-[10px] font-semibold leading-4",
                priced ? "bg-green-tint text-brand" : "bg-soft text-sub",
              )}
            >
              {priced ? t("overview.ipo.status.priced") : t("overview.ipo.status.filed")}
            </span>
          </a>
        );
      })}
    </div>
  );
}

/** 明星投资人 — curated 13F managers (the curated roster is a subset of the
 *  committed panel and can grow independently — see form13f-stars.json
 *  n_managers for the live count; the header number is that digest value =
 *  full roster, honest, never the reference's count). Avatar initials +
 *  locale-aware name (zh_name in zh) + $B book + top holding. Data = the
 *  ~2KB export-time digest, not the full book. */
function StarInvestorsCard() {
  const { t, lang } = useI18n();
  const stars = form13fStars.status === "ok" ? form13fStars.stars.slice(0, 6) : [];
  if (stars.length === 0) return null;
  return (
    <div className="overflow-hidden rounded-xl border border-line bg-card md:col-span-2">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 border-b border-line2 px-5 py-4">
        <h2 className="text-[17px] font-semibold tracking-[-0.02em]">
          {t("overview.stars.title")}
        </h2>
        <span className="font-mono text-[11px] text-mute tabular-nums">
          {fmtInt(form13fStars.n_managers)} {t("overview.stars.count.unit")}
        </span>
        <Link
          href="/institutions"
          className="ml-auto text-[13px] font-semibold text-brand hover:text-brand-hover"
        >
          {t("overview.stars.viewall")} →
        </Link>
      </div>
      {stars.map((m) => {
        const main = lang === "zh" ? (m.zh_name ?? m.name) : m.name;
        const sub =
          lang === "zh"
            ? m.name
            : (m.zh_name ?? `13F · ${m.quarter}`);
        return (
          <div
            key={m.cik}
            className="flex items-center gap-3 border-t border-line2 px-5 py-3 first:border-t-0 transition-colors hover:bg-soft"
          >
            <AvatarInitials
              name={m.name}
              className="size-11 bg-soft text-[13px] leading-11 text-sub"
            />
            <div className="min-w-0 flex-1">
              <p className="truncate text-[13px] font-semibold text-ink" title={main}>
                {main}
              </p>
              <p className="truncate text-[13px] text-mute" title={sub}>
                {sub}
              </p>
            </div>
            <div className="flex shrink-0 flex-col items-end">
              <span className="font-mono text-[13px] font-semibold tabular-nums">
                {fmtUsd(m.total_value)}
              </span>
              <span className="text-[11px] text-mute">{t("overview.stars.top_holding")}</span>
              <span
                className="max-w-[160px] truncate font-mono text-[11px] text-mute"
                title={m.top_issuer ?? undefined}
              >
                {m.top_ticker ?? m.top_issuer ?? "—"}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

/** ARK 持仓共振 — the ark panel carries a holdings SNAPSHOT (official daily
 *  CSVs), NOT position-change deltas: no ±pp exists and none is invented. The
 *  honest analog of the reference's moves module is the family-resonance cut
 *  (tickers held by the most ARK funds); the bar is fund-count proportional,
 *  and there is no "近 30 天" window label because the data does not support
 *  one. Value tone stays neutral (no direction = no direction colors). */
function ArkCard() {
  const { t } = useI18n();
  const ark = aionis.ark;
  const rows = ark.status === "ok" ? ark.family_overlap.slice(0, 6) : [];
  if (rows.length === 0) return null;
  const maxFunds = Math.max(...rows.map((o) => o.funds.length), 1);
  return (
    <div className="overflow-hidden rounded-xl border border-line bg-card">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 border-b border-line2 px-5 py-4">
        <h2 className="text-[17px] font-semibold tracking-[-0.02em]">
          {t("overview.ark.title")}
        </h2>
        <span className="font-mono text-[11px] text-mute tabular-nums">
          {ark.as_of} · {ark.n_funds}
        </span>
        <Link
          href="/institutions"
          className="ml-auto text-[13px] font-semibold text-brand hover:text-brand-hover"
        >
          {t("overview.ark.all")} →
        </Link>
      </div>
      {rows.map((o) => (
        <div
          key={o.ticker}
          className="flex items-center gap-2.5 border-t border-line2 px-5 py-[11px] first:border-t-0 transition-colors hover:bg-soft"
        >
          <span className="w-14 flex-none font-mono text-[13px] font-bold text-ink">
            {o.ticker}
          </span>
          <span className="min-w-0 flex-1 truncate text-[11px] text-mute" title={o.company}>
            {o.company || "—"}
          </span>
          <span className="h-[5px] w-[64px] flex-none overflow-hidden rounded bg-line2">
            <span
              className="block h-full rounded bg-green-fill"
              style={{ width: `${Math.max(6, Math.round((o.funds.length / maxFunds) * 100))}%` }}
            />
          </span>
          <span className="w-16 flex-none text-right font-mono text-[11px] font-semibold tabular-nums">
            {o.funds.length} {t("overview.ark.funds_held")}
          </span>
          <span
            className="w-12 flex-none text-right font-mono text-[11px] text-mute tabular-nums"
            title={t("overview.ark.max_weight")}
          >
            {o.max_weight_pct.toFixed(2)}%
          </span>
        </div>
      ))}
    </div>
  );
}

/** 重大事件 — Form 8-K material-event stream, top 5: company + localized
 *  category chip (same CATEGORY_LABEL map the /events page renders from —
 *  one category, one label across pages) + MM/DD; row links the primary doc. */
function Events8kCard() {
  const { t } = useI18n();
  const f = aionis.form8k;
  const rows = f.status === "ok" ? f.events.slice(0, 5) : [];
  if (rows.length === 0) return null;
  return (
    <div className="overflow-hidden rounded-xl border border-line bg-card md:col-span-2">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 border-b border-line2 px-5 py-4">
        <h2 className="text-[17px] font-semibold tracking-[-0.02em]">
          {t("overview.events8k.title")}
        </h2>
        <span className="font-mono text-[11px] text-mute tabular-nums">
          {fmtInt(f.total)} · {f.as_of ?? "—"}
        </span>
        <Link
          href="/events"
          className="ml-auto text-[13px] font-semibold text-brand hover:text-brand-hover"
        >
          {t("overview.events8k.all")} →
        </Link>
      </div>
      {rows.map((r, i) => {
        const labelKey = CATEGORY_LABEL[r.category];
        return (
          <a
            key={`${r.doc_url}-${i}`}
            href={r.doc_url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2.5 border-t border-line2 px-5 py-3 transition-colors hover:bg-soft first:border-t-0"
          >
            <span className="min-w-0 flex-1 truncate text-[13px] font-medium text-ink" title={r.company}>
              {r.company}
            </span>
            <span className="flex-none rounded-[4px] bg-soft px-1.5 py-px text-[10px] font-semibold leading-4 text-sub">
              {labelKey ? t(labelKey as DictKey) : r.category}
            </span>
            <span className="w-10 flex-none text-right font-mono text-[11px] text-mute tabular-nums">
              {fmtDateShort(r.filing_date)}
            </span>
          </a>
        );
      })}
    </div>
  );
}

/** 高管变动 — 8-K Item 5.02 officer-change filings. HONEST DEGRADATION: the
 *  panel (and form8k's officer_changes category) carries company-level events
 *  only — no person names and no 离任/上任 direction are parsed, so there is
 *  no initials avatar and no direction pill; rows are company + Item-5.02
 *  chip + MM/DD, with the granularity disclosed in the header note. */
function ExecsCard() {
  const { t } = useI18n();
  const f = aionis.executives;
  const rows = f.status === "ok" ? f.events.slice(0, 5) : [];
  if (rows.length === 0) return null;
  return (
    <div className="overflow-hidden rounded-xl border border-line bg-card">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 border-b border-line2 px-5 py-4">
        <h2 className="text-[17px] font-semibold tracking-[-0.02em]">
          {t("overview.execs.title")}
        </h2>
        <Link
          href="/executives"
          className="ml-auto text-[13px] font-semibold text-brand hover:text-brand-hover"
        >
          {t("overview.execs.all")} →
        </Link>
        <span className="w-full text-[11px] text-mute">{t("overview.execs.note")}</span>
      </div>
      {rows.map((r, i) => (
        <a
          key={`${r.doc_url}-${i}`}
          href={r.doc_url}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-2.5 border-t border-line2 px-5 py-3 transition-colors hover:bg-soft first:border-t-0"
        >
          <span className="min-w-0 flex-1 truncate text-[13px] font-medium text-ink" title={r.company}>
            {r.company}
          </span>
          <span className="flex-none rounded border border-line bg-soft px-1.5 py-px font-mono text-[10px] font-semibold text-sub">
            5.02
          </span>
          <span className="w-10 flex-none text-right font-mono text-[11px] text-mute tabular-nums">
            {fmtDateShort(r.filing_date)}
          </span>
        </a>
      ))}
    </div>
  );
}

/** 探索全部数据模块 — the directory footer grid: 12 route cards over OUR real
 *  routes, each desc naming the actual upstream source. The footer line lists
 *  the true sourcing (the panels' own primary sources — no marketing padding). */
function ExploreGrid() {
  const { t } = useI18n();
  const items: {
    href: string;
    icon: React.ReactNode;
    title: string;
    desc: string;
    key: string;
  }[] = [
    { key: "news", href: "/news", icon: <NewspaperIcon className="size-4" />, title: t("overview.explore.t_news"), desc: t("overview.explore.news") },
    { key: "reddit", href: "/reddit", icon: <FlameIcon className="size-4" />, title: t("overview.explore.t_reddit"), desc: t("overview.explore.reddit") },
    { key: "institutions", href: "/institutions", icon: <Building2Icon className="size-4" />, title: t("overview.explore.t_institutions"), desc: t("overview.explore.institutions") },
    { key: "forcecamp", href: "/force-camp", icon: <NetworkIcon className="size-4" />, title: t("overview.explore.t_forcecamp"), desc: t("overview.explore.forcecamp") },
    { key: "stars", href: "/institutions", icon: <UserIcon className="size-4" />, title: t("overview.stars.title"), desc: t("overview.explore.stars") },
    { key: "congress", href: "/congress", icon: <LandmarkIcon className="size-4" />, title: t("overview.stat.trades"), desc: t("overview.explore.congress") },
    { key: "insiders", href: "/insiders", icon: <UserCogIcon className="size-4" />, title: t("overview.explore.t_insiders"), desc: t("overview.explore.insiders") },
    { key: "ipo", href: "/ipo", icon: <RocketIcon className="size-4" />, title: t("overview.explore.t_ipo"), desc: t("overview.explore.ipo") },
    { key: "stakes", href: "/stakes", icon: <FlagIcon className="size-4" />, title: t("nav.stakes"), desc: t("overview.explore.stakes") },
    { key: "companies", href: "/companies", icon: <LayoutGridIcon className="size-4" />, title: t("nav.companies"), desc: t("overview.explore.companies") },
    { key: "events", href: "/events", icon: <ZapIcon className="size-4" />, title: t("overview.events8k.title"), desc: t("overview.explore.events") },
    { key: "executives", href: "/executives", icon: <BriefcaseIcon className="size-4" />, title: t("overview.explore.t_executives"), desc: t("overview.explore.executives") },
    { key: "quarterly", href: "/quarterly", icon: <FileTextIcon className="size-4" />, title: t("overview.explore.t_quarterly"), desc: t("overview.explore.quarterly") },
  ];
  return (
    <section className="space-y-3">
      <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
        <h2 className="text-[17px] font-semibold tracking-[-0.02em]">
          {t("overview.explore.title")}
        </h2>
        <p className="text-xs text-mute">{t("overview.explore.subtitle")}</p>
      </div>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
        {items.map((it) => (
          <Link key={it.key} href={it.href} className="group">
            <div className="flex h-full items-start gap-3 rounded-xl border border-line bg-card p-4 transition-colors group-hover:border-faint">
              <span className="flex size-9 flex-none items-center justify-center rounded-lg bg-soft text-sub">
                {it.icon}
              </span>
              <span className="min-w-0">
                <span className="block truncate text-[13px] font-semibold text-ink">
                  {it.title}
                </span>
                <span className="mt-0.5 block text-[11px] leading-snug text-mute">
                  {it.desc}
                </span>
              </span>
            </div>
          </Link>
        ))}
      </div>
      <p className="border-t border-line2 pt-3 text-[11px] text-mute">
        {t("overview.explore.source")}
      </p>
    </section>
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
 *  new fetches. The validity-argument narrative continues below it.
 *
 *  The Reddit card renders the deployed board's FULL row anatomy, but only
 *  fields the ApeWisdom panel actually carries: rank / ticker / name /
 *  rank_24h_ago (arrow) / mentions / upvotes. There is NO price-Δ field (and
 *  live prices are display-Worker-only by project law) — the Δ slot shows the
 *  honest 24h MENTIONS change instead, tooltip-labeled. N in the header is
 *  count_declared (the board's own declared total), not our visible slice. */
function DataCockpit() {
  const { t } = useI18n();
  const news = aionis.newsFeed.status === "ok" ? aionis.newsFeed.items.slice(0, 5) : [];
  const rt = aionis.redditTrending;
  const heat = rt.status === "ok" ? rt.tickers.slice(0, 10) : [];
  const ctx = aionis.politicianTradesTx;
  const tx = ctx.status === "ok" ? ctx.transactions : [];
  const trades = tx.slice(0, 5);
  const nBuy = tx.filter((r) => r.direction === "buy").length;
  const nSell = tx.length - nBuy;
  const nLate = tx.filter((r) => r.days_late !== null && r.days_late > 45).length;
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
          <div className="flex items-baseline justify-between gap-2">
            <CardTitle className="text-sm">{t("overview.cockpit.heat")}</CardTitle>
            <Link
              href="/reddit"
              className="text-[13px] font-semibold text-brand hover:text-brand-hover"
            >
              {t("overview.cockpit.heat.full")} →
            </Link>
          </div>
          <CardDescription className="font-mono text-[11px] tabular-nums">
            {t("overview.cockpit.heat.count_pre")
              ? `${t("overview.cockpit.heat.count_pre")} ${fmtInt(rt.count_declared)} ${t("overview.cockpit.heat.count_suf")}`
              : `${fmtInt(rt.count_declared)} ${t("overview.cockpit.heat.count_suf")}`}
          </CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          {heat.map((h) => {
            const prev = h.rank_24h_ago;
            const up = prev !== null && prev > h.rank;
            const down = prev !== null && prev < h.rank;
            const dMentions =
              h.mentions_24h_ago != null ? h.mentions - h.mentions_24h_ago : null;
            return (
              <div
                key={h.ticker}
                className="flex items-center gap-2 border-t border-line2 px-4 py-2.5 first:border-t-0 transition-colors hover:bg-soft"
              >
                <span className="w-5 flex-none text-right font-mono text-[13px] font-bold text-brand tabular-nums">
                  {h.rank}
                </span>
                <span className="flex-none font-mono text-[13px] font-semibold">{h.ticker}</span>
                <span className="min-w-0 flex-1 truncate text-[11px] text-mute" title={h.name}>
                  {h.name || "—"}
                </span>
                {prev == null ? (
                  <span className="flex-none rounded-[3px] bg-soft px-1 font-mono text-[10px] font-semibold text-mute">
                    {t("overview.cockpit.heat.new")}
                  </span>
                ) : up || down ? (
                  <span
                    className={cn(
                      "inline-flex flex-none items-center gap-0.5 font-mono text-[10px] font-semibold tabular-nums",
                      up ? "text-up" : "text-down",
                    )}
                  >
                    {up ? <ArrowUpIcon className="size-3" /> : <ArrowDownIcon className="size-3" />}
                    {Math.abs(prev - h.rank)}
                  </span>
                ) : (
                  <span className="flex-none text-mute">
                    <MinusIcon className="size-3" />
                  </span>
                )}
                <span className="w-8 flex-none text-right font-mono text-[12px] font-semibold tabular-nums">
                  {h.mentions}
                </span>
                {dMentions != null && dMentions !== 0 ? (
                  <span
                    className={cn(
                      "w-8 flex-none text-right font-mono text-[10px] tabular-nums",
                      dMentions > 0 ? "text-up" : "text-down",
                    )}
                    title={t("overview.cockpit.heat.mentions24h")}
                  >
                    {dMentions > 0 ? "+" : ""}{dMentions}
                  </span>
                ) : (
                  <span className="w-8 flex-none" />
                )}
                <span
                  className="w-10 flex-none text-right font-mono text-[11px] text-mute tabular-nums"
                  title={t("overview.cockpit.heat.upvotes")}
                >
                  {h.upvotes}
                </span>
              </div>
            );
          })}
        </CardContent>
      </Card>
      <Card className="min-w-0 py-0">
        <CardHeader className="border-b">
          <div className="flex items-baseline justify-between gap-2">
            <CardTitle className="text-sm">{t("overview.cockpit.trades")}</CardTitle>
            <Link
              href="/congress"
              className="text-[13px] font-semibold text-brand hover:text-brand-hover"
            >
              {t("overview.cockpit.trades.viewall")} →
            </Link>
          </div>
          {/* KPI line computed client-side from the transactions themselves:
              buy/sell from the parsed direction, late = STOCK Act >45-day
              clock (days_late field — 379 rows in the committed panel). */}
          <CardDescription className="font-mono text-[11px] tabular-nums">
            {fmtInt(ctx.total ?? tx.length)} {t("overview.cockpit.trades.kpi_tx")} ·{" "}
            {t("overview.cockpit.trades.buy")} {fmtInt(nBuy)} /{" "}
            {t("overview.cockpit.trades.sell")} {fmtInt(nSell)} /{" "}
            {t("overview.cockpit.trades.late")} {fmtInt(nLate)}
          </CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          {trades.map((r) => (
            <div
              key={`${r.doc_url}-${r.transaction_date}-${r.ticker || "x"}`}
              className="flex items-center gap-2 border-t border-line2 px-4 py-3 first:border-t-0 transition-colors hover:bg-soft"
            >
              <span className="w-16 shrink-0 truncate text-[11px] font-medium" title={r.member}>
                {r.member.split(",")[0]}
              </span>
              {r.party ? (
                <span
                  className={cn(
                    "shrink-0 rounded-[3px] px-1 font-mono text-[10px] font-semibold leading-4",
                    r.party === "D"
                      ? "bg-blue-tint text-blue"
                      : r.party === "R"
                        ? "bg-red-tint text-red"
                        : "bg-soft text-mute",
                  )}
                >
                  {r.party}
                </span>
              ) : null}
              <span className="font-mono text-[13px] font-semibold">{r.ticker || "—"}</span>
              <span
                className={
                  "ml-auto shrink-0 rounded-[3px] px-1 font-mono text-[10px] font-semibold " +
                  (r.direction === "buy" ? "badge-up border" : "badge-down border")
                }
              >
                {r.direction === "buy" ? "B" : "S"}
              </span>
              <span className="shrink-0 font-mono text-[11px] text-mute tabular-nums">
                {fmtDateShort(r.transaction_date)}
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
      {/* Directory-lane module rows (deployed-terminal parity): the three
          stream cards, then institutions (star managers + ARK resonance),
          then the two event cards. All client-side from committed panels. */}
      <section className="grid grid-cols-1 items-start gap-4 md:grid-cols-3">
        <StakesCard />
        <IpoCard />
        <FilingStrip />
      </section>
      <section className="grid grid-cols-1 items-start gap-4 md:grid-cols-3">
        <StarInvestorsCard />
        <ArkCard />
      </section>
      <section className="grid grid-cols-1 items-start gap-4 md:grid-cols-3">
        <Events8kCard />
        <ExecsCard />
      </section>
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
      <ExploreGrid />
      <GuardBand />
    </div>
  );
}
