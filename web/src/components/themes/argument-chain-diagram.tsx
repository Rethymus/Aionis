"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { useI18n } from "@/i18n/provider";
import Link from "next/link";
import {
  WavesIcon,
  GaugeIcon,
  BrainCircuitIcon,
  ShieldCheckIcon,
  ScissorsIcon,
  ArrowRightIcon,
} from "lucide-react";

// The validity-argument chain (paradigm α, ECD). NOT a data funnel — it is one
// falsifiable claim's argument: each segment is a logical step, and the step
// between two segments is the WARRANT (why this segment supports the next), not
// "data flowing down a pipe". Segments estimand/validity live in the picks/track
// routes; this diagram links them so the page is one coherent argument.
type TitleKey =
  | "argument.chain.context.title"
  | "argument.chain.evidence.title"
  | "argument.chain.estimand.title"
  | "argument.chain.validity.title"
  | "argument.chain.verdict.title";

type DescKey =
  | "argument.chain.context.desc"
  | "argument.chain.evidence.desc"
  | "argument.chain.estimand.desc"
  | "argument.chain.validity.desc"
  | "argument.chain.verdict.desc";

// The warrant explains why this segment entails the next (ECD claim→evidence→warrant).
type WarrantKey =
  | "argument.chain.context.warrant"
  | "argument.chain.evidence.warrant"
  | "argument.chain.estimand.warrant"
  | "argument.chain.validity.warrant";

const SEGMENTS = [
  {
    id: "context",
    titleKey: "argument.chain.context.title" as TitleKey,
    descKey: "argument.chain.context.desc" as DescKey,
    warrantKey: "argument.chain.context.warrant" as WarrantKey,
    icon: WavesIcon,
    accent: "border-blue-500/40 bg-blue-500/5 text-blue-700 dark:text-blue-300",
    external: null as string | null,
  },
  {
    id: "evidence",
    titleKey: "argument.chain.evidence.title" as TitleKey,
    descKey: "argument.chain.evidence.desc" as DescKey,
    warrantKey: "argument.chain.evidence.warrant" as WarrantKey,
    icon: GaugeIcon,
    accent: "border-emerald-500/40 bg-emerald-500/5 text-emerald-700 dark:text-emerald-300",
    external: null as string | null,
  },
  {
    id: "estimand",
    titleKey: "argument.chain.estimand.title" as TitleKey,
    descKey: "argument.chain.estimand.desc" as DescKey,
    warrantKey: "argument.chain.estimand.warrant" as WarrantKey,
    icon: BrainCircuitIcon,
    accent: "border-violet-500/40 bg-violet-500/5 text-violet-700 dark:text-violet-300",
    external: "/picks",
  },
  {
    id: "validity",
    titleKey: "argument.chain.validity.title" as TitleKey,
    descKey: "argument.chain.validity.desc" as DescKey,
    warrantKey: "argument.chain.validity.warrant" as WarrantKey,
    icon: ShieldCheckIcon,
    accent: "border-amber-500/40 bg-amber-500/5 text-amber-700 dark:text-amber-300",
    external: "/track",
  },
  {
    id: "verdict",
    titleKey: "argument.chain.verdict.title" as TitleKey,
    descKey: "argument.chain.verdict.desc" as DescKey,
    warrantKey: null,
    icon: ScissorsIcon,
    accent: "border-rose-500/40 bg-rose-500/5 text-rose-700 dark:text-rose-400",
    external: null as string | null,
  },
];

export function ArgumentChainDiagram() {
  const { t } = useI18n();
  return (
    <Card className="overflow-hidden py-0">
      <CardContent className="p-4">
        <div className="mb-3">
          <h2 className="text-base font-semibold tracking-tight">
            {t("argument.chain.title")}
          </h2>
          <p className="text-xs text-muted-foreground">{t("argument.chain.hint")}</p>
        </div>
        <ol className="space-y-0">
          {SEGMENTS.map((seg) => {
            const Icon = seg.icon;
            const body = (
              <div
                className={cn(
                  "flex items-center gap-3 rounded-md border px-3 py-2.5",
                  seg.accent,
                )}
              >
                <Icon className="size-4 shrink-0" />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium">{t(seg.titleKey)}</span>
                    {seg.external ? (
                      <Badge variant="secondary" className="px-1.5 py-0 text-[9px]">
                        {t("argument.chain.here")}
                      </Badge>
                    ) : null}
                  </div>
                  <p className="line-clamp-2 text-[11px] opacity-80">
                    {t(seg.descKey)}
                  </p>
                </div>
              </div>
            );
            return (
              <li key={seg.id}>
                {seg.external ? (
                  <Link href={seg.external} className="block">
                    {body}
                  </Link>
                ) : (
                  body
                )}
                {seg.warrantKey ? (
                  <div className="flex items-center gap-2 py-1 pl-6">
                    <ArrowRightIcon className="size-3 shrink-0 text-muted-foreground/70" />
                    <span className="text-[10px] italic text-muted-foreground">
                      {t(seg.warrantKey)}
                    </span>
                  </div>
                ) : null}
              </li>
            );
          })}
        </ol>
      </CardContent>
    </Card>
  );
}
