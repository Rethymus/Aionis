"use client";

import Link from "next/link";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { useI18n } from "@/i18n/provider";
import { aionis } from "@/data/aionis";
import {
  LockIcon,
  CheckCircle2Icon,
  ArrowRightIcon,
  ShieldCheckIcon,
} from "lucide-react";

// The birth certificate of the headline claim (paradigm-α validity spine).
// The hero shows `combined rank-IC = -0.0088`; this anchor ties that exact
// number to its ledger row, the config_committed row that froze its config
// BEFORE the result was observed, the shared sha256, H6 determinism, and the
// J-T gate verdict. It is the anti-leakage contract surfaced at the point of
// the claim — not buried in a separate timeline. Reads only the curated
// headline_provenance.json (READ-ONLY projection of the append-only ledger).
// Deterministic, no external call, no OOS signal, never mutates the ledger.

function tsTime(ts?: string): string {
  if (!ts) return "—";
  // 2026-08-05T10:27:13... -> 2026-08-05 10:27 UTC
  return ts.slice(0, 16).replace("T", " ") + " UTC";
}

export function ProvenanceAnchor({ embedded = false }: { embedded?: boolean }) {
  const { t } = useI18n();
  const p = aionis.headlineProvenance;
  if (!p || p.status !== "ok" || !p.freeze || !p.headline) {
    // Honest degradation: if no confirmatory result has frozen provenance, show
    // a muted note rather than fabricating a certificate (embedded mode: the
    // verdict card already carries the claim; nothing to certify, omit).
    if (embedded) return null;
    return (
      <Card className="border-dashed">
        <CardContent className="flex items-center gap-2 p-3 text-xs text-muted-foreground">
          <LockIcon className="size-3.5" />
          {t("overview.provenance.awaiting")}
        </CardContent>
      </Card>
    );
  }
  const proven = p.contract?.freeze_before_result === true;
  const body = (
    <>
      <div className="flex flex-wrap items-center gap-2">
          <Badge
            variant="outline"
            className={cn(
              "gap-1 px-1.5 py-0 text-xs font-normal",
              proven
                ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                : "border-amber-500/30 bg-amber-500/10 text-amber-600 dark:text-amber-400",
            )}
          >
            {proven ? <CheckCircle2Icon className="size-2.5" /> : <LockIcon className="size-2.5" />}
            {t("overview.provenance.freeze_before")}
          </Badge>
          <span className="text-xs text-muted-foreground">{t("overview.provenance.label")}</span>
        </div>
        <div className="grid gap-x-6 gap-y-1.5 font-mono text-xs sm:grid-cols-2">
          <div className="flex items-center justify-between gap-2">
            <span className="text-muted-foreground">
              {t("overview.provenance.freeze_row")} · {t("overview.provenance.row")} #{p.freeze.ledger_row}
            </span>
            <span className="tabular-nums text-muted-foreground">{tsTime(p.freeze.ts)}</span>
          </div>
          <div className="flex items-center justify-between gap-2">
            <span className="text-muted-foreground">
              {t("overview.provenance.result_row")} · {t("overview.provenance.row")} #{p.ledger_row}
            </span>
            <span className="tabular-nums text-muted-foreground">{tsTime(p.result_ts)}</span>
          </div>
          <div className="flex items-center justify-between gap-2">
            <span className="text-muted-foreground">{t("overview.provenance.sha")}</span>
            <span className="tabular-nums">{p.config_sig_short || "—"}</span>
          </div>
          <div className="flex items-center justify-between gap-2">
            <span className="text-muted-foreground">{t("overview.provenance.h6")}</span>
            <span
              className={cn(
                "tabular-nums",
                p.headline.h6_deterministic
                  ? "text-emerald-600 dark:text-emerald-400"
                  : "text-amber-600 dark:text-amber-400",
              )}
            >
              {p.headline.h6_deterministic ? "PASS" : "FAIL"}
            </span>
          </div>
          <div className="flex items-center justify-between gap-2">
            <span className="text-muted-foreground">{t("overview.provenance.jt")}</span>
            <span className="tabular-nums">{p.headline.jt_look1 || "—"}</span>
          </div>
        </div>
        <Link
          href="/discipline"
          className="group inline-flex items-center gap-1 text-xs font-medium text-muted-foreground transition-colors hover:text-foreground"
        >
          <ShieldCheckIcon className="size-3" />
          {t("overview.provenance.view_timeline")}
          <ArrowRightIcon className="size-3 transition-transform group-hover:translate-x-0.5" />
        </Link>
    </>
  );
  // Embedded = the birth certificate lives INSIDE the verdict card it belongs
  // to (a claim and how it was frozen are one object). The overview previously
  // stacked three badge-heavy cards — trust ribbon → verdict → provenance —
  // which read as clutter before the argument chain even began.
  if (embedded) {
    return <div className="mt-3 space-y-2.5 border-t pt-3">{body}</div>;
  }
  return (
    <Card className="overflow-hidden">
      <CardContent className="space-y-2.5 p-4">{body}</CardContent>
    </Card>
  );
}
