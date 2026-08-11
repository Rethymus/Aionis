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
  ArrowDownIcon,
} from "lucide-react";

// The validity-argument chain (paradigm α): one falsifiable claim's argument,
// read top → bottom. Layers 2/3 (estimand / validity) live in the picks/track
// segments; the funnel links them so this panel is not an isolated collage.
// Layer indices (0..4) are internal ids only — no layer numbers are shown.
type LayerKey =
  | "themes.funnel.l0.title"
  | "themes.funnel.l1.title"
  | "themes.funnel.l2.title"
  | "themes.funnel.l3.title"
  | "themes.funnel.l4.title";

type DescKey =
  | "themes.funnel.l0.desc"
  | "themes.funnel.l1.desc"
  | "themes.funnel.l2.desc"
  | "themes.funnel.l3.desc"
  | "themes.funnel.l4.desc";

type TransitionKey =
  | "themes.funnel.l0.flow"
  | "themes.funnel.l1.flow"
  | "themes.funnel.l2.flow"
  | "themes.funnel.l3.flow";

const LAYERS = [
  {
    n: 0,
    titleKey: "themes.funnel.l0.title" as LayerKey,
    descKey: "themes.funnel.l0.desc" as DescKey,
    flowKey: "themes.funnel.l0.flow" as TransitionKey,
    icon: WavesIcon,
    accent: "border-blue-500/40 bg-blue-500/5 text-blue-700 dark:text-blue-300",
    inPanel: true,
    hub: null as string | null,
  },
  {
    n: 1,
    titleKey: "themes.funnel.l1.title" as LayerKey,
    descKey: "themes.funnel.l1.desc" as DescKey,
    flowKey: "themes.funnel.l1.flow" as TransitionKey,
    icon: GaugeIcon,
    accent: "border-emerald-500/40 bg-emerald-500/5 text-emerald-700 dark:text-emerald-300",
    inPanel: true,
    hub: null as string | null,
  },
  {
    n: 2,
    titleKey: "themes.funnel.l2.title" as LayerKey,
    descKey: "themes.funnel.l2.desc" as DescKey,
    flowKey: "themes.funnel.l2.flow" as TransitionKey,
    icon: BrainCircuitIcon,
    accent: "border-violet-500/40 bg-violet-500/5 text-violet-700 dark:text-violet-300",
    inPanel: false,
    hub: "/picks",
  },
  {
    n: 3,
    titleKey: "themes.funnel.l3.title" as LayerKey,
    descKey: "themes.funnel.l3.desc" as DescKey,
    flowKey: "themes.funnel.l3.flow" as TransitionKey,
    icon: ShieldCheckIcon,
    accent: "border-amber-500/40 bg-amber-500/5 text-amber-700 dark:text-amber-300",
    inPanel: false,
    hub: "/track",
  },
  {
    n: 4,
    titleKey: "themes.funnel.l4.title" as LayerKey,
    descKey: "themes.funnel.l4.desc" as DescKey,
    flowKey: null,
    icon: ScissorsIcon,
    accent: "border-rose-500/40 bg-rose-500/5 text-rose-700 dark:text-rose-300",
    inPanel: true,
    hub: null as string | null,
  },
];

export function ThemesFunnel() {
  const { t } = useI18n();
  return (
    <Card className="overflow-hidden py-0">
      <CardContent className="p-4">
        <div className="mb-3">
          <h2 className="text-base font-semibold tracking-tight">
            {t("themes.funnel.title")}
          </h2>
          <p className="text-xs text-muted-foreground">{t("themes.funnel.hint")}</p>
        </div>
        <ol className="space-y-0">
          {LAYERS.map((layer, i) => {
            const Icon = layer.icon;
            const body = (
              <div
                className={cn(
                  "flex items-center gap-3 rounded-md border px-3 py-2.5",
                  layer.accent,
                )}
              >
                <div className="flex flex-col items-center gap-1">
                  <Icon className="size-4" />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium">{t(layer.titleKey)}</span>
                    {layer.inPanel ? (
                      <Badge variant="secondary" className="px-1.5 py-0 text-[9px]">
                        {t("themes.funnel.here")}
                      </Badge>
                    ) : null}
                  </div>
                  <p className="truncate text-[11px] opacity-80">
                    {t(layer.descKey)}
                  </p>
                </div>
              </div>
            );
            return (
              <li key={layer.n}>
                {layer.hub ? (
                  <Link href={layer.hub} className="block">
                    {body}
                  </Link>
                ) : (
                  body
                )}
                {layer.flowKey ? (
                  <div className="flex items-center gap-2 py-1 pl-6">
                    <ArrowDownIcon className="size-3 shrink-0 text-muted-foreground" />
                    <span className="text-[10px] text-muted-foreground">
                      {t(layer.flowKey)}
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
