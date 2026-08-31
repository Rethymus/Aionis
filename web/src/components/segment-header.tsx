"use client";

import type { ReactNode } from "react";
import { useI18n } from "@/i18n/provider";
import { ProvenanceBadge } from "@/components/provenance-badge";
import type { DictKey } from "@/i18n/dict";

// The argument-spine segment a page belongs to (paradigm α). The spine
// breadcrumb row ("语境 → 证据 → 效度 → 可证伪主张") was retired 2026-08-31
// (owner call): the top nav + the Overview argument chain already carry that
// navigation, and the per-page row duplicated them. The segment prop is kept
// (optional, unused) so 21 page call sites stay untouched; the page-level
// provenance (as_of badge, intro, count hint) is the part that must survive.
export type Segment =
  | "context"
  | "evidence"
  | "validity"
  | "verdict"
  | "guard";

export function SegmentHeader({
  introKey,
  asOf,
  frozen = false,
  countHint,
  extra,
}: {
  /** Retained for call-site compatibility; no longer rendered (see above). */
  segment?: Segment;
  introKey: DictKey;
  asOf?: string | null;
  frozen?: boolean;
  /** Data scale + window, reference P1 style: "874 份 · 2025–2026". Rendered
   *  under the intro so the first screen anchors count AND freshness. The
   *  caller composes it from real panel data (never a hardcoded literal). */
  countHint?: string;
  /** Optional extra provenance chips for pages whose panels carry MORE than
   *  one waterline (e.g. institutions: quarterly holdings vs the filer
   *  directory's filed envelope). Rendered right after the page's own as_of
   *  badge so every freshness claim stays in one place. */
  extra?: ReactNode;
}) {
  const { t } = useI18n();
  return (
    <header className="space-y-2">
      <p className="max-w-3xl text-sm text-muted-foreground">{t(introKey)}</p>
      <div className="flex flex-wrap items-center gap-2">
        {asOf ? <ProvenanceBadge ts={asOf} frozen={frozen} /> : null}
        {extra}
        {countHint ? (
          <p className="font-mono text-xs tabular-nums text-muted-foreground/80">
            {countHint}
          </p>
        ) : null}
      </div>
    </header>
  );
}
