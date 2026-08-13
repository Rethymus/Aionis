"use client";

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
import { LockIcon, CheckCircle2Icon, FlaskConicalIcon } from "lucide-react";

// The frozen-config audit timeline (paradigm-α guard-band display layer). This
// surfaces Aionis's defining identity — config_committed BEFORE result — as a
// chronological table so a visitor can SEE the anti-leakage contract, not just
// read the badge. Reads only the curated ledger_audit.json (read-only export of
// the append-only runs/ledger.jsonl). Deterministic, no external call, no OOS
// signal, never mutates the ledger.

// Event → i18n key + visual treatment. config_committed rows are the anchor
// (the contract in action); result rows are paired consumers of a frozen config.
type EventMeta = {
  labelKey:
    | "audit.event.config_committed"
    | "audit.event.confirmatory:first"
    | "audit.event.oos_result"
    | "audit.event.exploratory"
    | "audit.event.phase_b_freeze";
  isFreeze: boolean; // config_committed = the "before result" anchor
  isResult: boolean; // confirmatory:first / oos_result = a verdict landed
};

const EVENT_META: Record<string, EventMeta> = {
  config_committed: { labelKey: "audit.event.config_committed", isFreeze: true, isResult: false },
  "confirmatory:first": { labelKey: "audit.event.confirmatory:first", isFreeze: false, isResult: true },
  oos_result: { labelKey: "audit.event.oos_result", isFreeze: false, isResult: true },
  exploratory: { labelKey: "audit.event.exploratory", isFreeze: false, isResult: false },
  phase_b_freeze: { labelKey: "audit.event.phase_b_freeze", isFreeze: true, isResult: false },
};

export function AuditTimeline() {
  const { t } = useI18n();
  const audit = aionis.ledgerAudit;
  if (!audit || !audit.entries || audit.entries.length === 0) {
    return null;
  }

  return (
    <Card className="overflow-hidden">
      <CardHeader className="gap-2">
        <CardTitle className="flex items-center gap-2 text-base">
          <LockIcon className="size-4 text-primary" />
          {t("audit.title")}
        </CardTitle>
        <CardDescription>{t("audit.intro")}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="border-b text-[10px] uppercase text-muted-foreground/70">
              <tr>
                <th className="py-1.5 pr-2 font-medium">{t("audit.col.row")}</th>
                <th className="py-1.5 pr-2 font-medium">{t("audit.col.date")}</th>
                <th className="py-1.5 pr-2 font-medium">{t("audit.col.event")}</th>
                <th className="hidden py-1.5 pr-2 font-medium md:table-cell">{t("audit.col.phase")}</th>
                <th className="hidden py-1.5 pr-2 font-mono font-medium md:table-cell">{t("audit.col.sig")}</th>
                <th className="py-1.5 pr-2 font-medium">{t("audit.col.metric")}</th>
                <th className="py-1.5 font-medium">{t("audit.col.verdict")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/50">
              {audit.entries.map((e) => {
                const meta = EVENT_META[e.event] ?? EVENT_META.exploratory;
                return (
                  <tr key={e.row} className="align-top">
                    <td className="py-1.5 pr-2 font-mono text-muted-foreground/60">{e.row}</td>
                    <td className="py-1.5 pr-2 font-mono whitespace-nowrap text-muted-foreground">{e.ts}</td>
                    <td className="py-1.5 pr-2">
                      <Badge
                        variant="outline"
                        title={e.config_sig_short ? `${e.phase} · ${e.config_sig_short}` : e.phase}
                        className={cn(
                          "gap-1 px-1.5 py-0 text-[10px] font-normal",
                          meta.isFreeze
                            ? "border-primary/30 bg-primary/10 text-primary"
                            : meta.isResult
                              ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                              : "border-muted-foreground/30 text-muted-foreground",
                        )}
                      >
                        {meta.isFreeze ? <LockIcon className="size-2.5" /> : meta.isResult ? <CheckCircle2Icon className="size-2.5" /> : <FlaskConicalIcon className="size-2.5" />}
                        {t(meta.labelKey)}
                      </Badge>
                    </td>
                    <td className="hidden py-1.5 pr-2 font-mono text-muted-foreground md:table-cell">{e.phase || "—"}</td>
                    <td className="hidden py-1.5 pr-2 font-mono text-[10px] text-muted-foreground/70 md:table-cell">{e.config_sig_short || "—"}</td>
                    <td className="py-1.5 pr-2 font-mono text-[10px] text-foreground/70">{e.metric || "—"}</td>
                    <td className="py-1.5 pr-2 text-muted-foreground">
                      {e.verdict ? (
                        <span className="line-clamp-2">{e.verdict}</span>
                      ) : e.h6 === true ? (
                        <span className="font-mono text-[10px] text-emerald-600 dark:text-emerald-400">H6 PASS</span>
                      ) : (
                        "—"
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <p className="border-t pt-2 text-[10px] text-muted-foreground/70">
          {t("audit.footer")
            .replace("{n}", String(audit.n_total_rows))
            .replace("{claims}", String(audit.n_claim_rows))}
        </p>
      </CardContent>
    </Card>
  );
}
