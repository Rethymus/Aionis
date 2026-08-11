"use client";

import Link from "next/link";
import { ArrowRightIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import { useI18n } from "@/i18n/provider";
import type { DictKey } from "@/i18n/dict";

// The argument-spine segment a page belongs to (paradigm α). Every page declares
// its place on the context → evidence → validity → verdict chain (guard spans
// all), so the whole terminal radiates the spine — not just the Overview.
export type Segment =
  | "context"
  | "evidence"
  | "validity"
  | "verdict"
  | "guard";

const SEGMENT_META: Record<
  Segment,
  { labelKey: DictKey; href: string }
> = {
  context: { labelKey: "nav.group.context", href: "/regime" },
  evidence: { labelKey: "nav.group.evidence", href: "/picks" },
  validity: { labelKey: "nav.group.validity", href: "/track" },
  verdict: { labelKey: "overview.verdict.claim", href: "/track#evidence" },
  guard: { labelKey: "nav.group.guard", href: "/discipline" },
};

// The linear chain order. Guard is rendered as a spanning suffix, not a step.
const CHAIN_ORDER: Segment[] = ["context", "evidence", "validity", "verdict"];

export function SegmentHeader({
  segment,
  introKey,
}: {
  segment: Segment;
  introKey: DictKey;
}) {
  const { t } = useI18n();
  return (
    <header className="space-y-2">
      {/* Spine breadcrumb: every page shows where it sits on the argument. */}
      <nav aria-label="argument chain" className="flex flex-wrap items-center gap-1 text-[11px] text-muted-foreground">
        {CHAIN_ORDER.map((s, i) => {
          const meta = SEGMENT_META[s];
          const active = s === segment;
          const node = (
            <span
              className={cn(
                "rounded px-1.5 py-0.5",
                active
                  ? "bg-primary/10 font-medium text-primary"
                  : "text-muted-foreground/70 hover:text-foreground",
              )}
            >
              {t(meta.labelKey)}
            </span>
          );
          return (
            <span key={s} className="inline-flex items-center gap-1">
              {active ? node : <Link href={meta.href}>{node}</Link>}
              {i < CHAIN_ORDER.length - 1 ? (
                <ArrowRightIcon className="size-2.5 text-muted-foreground/40" />
              ) : null}
            </span>
          );
        })}
        {/* Guard spans the whole chain — shown as a trailing chip on every page. */}
        {segment !== "guard" ? (
          <Link
            href="/discipline"
            className="ml-1 inline-flex items-center gap-1 rounded border border-dashed border-muted-foreground/30 px-1.5 py-0.5 text-muted-foreground/60 hover:text-foreground"
          >
            {t("nav.group.guard")}
          </Link>
        ) : null}
      </nav>
      <p className="max-w-3xl text-sm text-muted-foreground">{t(introKey)}</p>
    </header>
  );
}
