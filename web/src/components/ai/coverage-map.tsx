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
import { CheckCircle2Icon, CircleDashedIcon, MinusCircleIcon } from "lucide-react";

// Coverage map (paradigm-α Track C, display-only). Maps Aionis's tested
// factor families against the academic "factor zoo" (Cochrane 2011) to surface
// what HAS a frozen confirmatory result vs what remains exploratory/untested.
//
// Grounded in the coverage inventory (runs/ledger.jsonl + config/ + src/features)
// — every "tested" claim cites a frozen ledger row; gaps cite the canonical
// anomaly. This is the "金融学知识 × 市场研究理论" bridge: each cell ties a
// research-software artifact to an asset-pricing anomaly. Deterministic, no
// external call, no OOS signal.

type Depth = "tested" | "exploratory" | "gap";

type FamilyRow = {
  familyKey:
    | "coverage.family.value"
    | "coverage.family.momentum"
    | "coverage.family.risk"
    | "coverage.family.liquidity"
    | "coverage.family.sentiment";
  depth: Depth;
  tested: string[]; // factors with a frozen ledger result
  exploratory: string[]; // features exist, no confirmatory row
  gaps: string[]; // canonical anomalies absent (factor zoo)
  cite?: string; // ledger/config citation
};

const FAMILIES: FamilyRow[] = [
  {
    familyKey: "coverage.family.value",
    depth: "tested",
    tested: ["mktcap", "pb_ratio", "roa/roe", "profit_margin", "leverage", "book_value/share", "accruals (col)"],
    exploratory: ["asset_growth (Track B)", "investment_12m (Track B)"],
    gaps: ["gross profitability (Novy-Marx GP)", "net stock issues (Pontiff-Singh)", "accruals anomaly (Sloan, standalone)"],
    cite: "ledger #28 / Track B #41",
  },
  {
    familyKey: "coverage.family.momentum",
    depth: "tested",
    tested: ["momentum 5/10/21/42d", "reversal_5d", "peer_mom (SIC ex-self)"],
    exploratory: [],
    gaps: ["J-T 12-1 momentum", "industry momentum (Moskowitz-Grinblatt)", "52-week high (George-Hwang)", "customer momentum (Cohen-Frazzini)"],
    cite: "Track B #41 / Phase D #34",
  },
  {
    familyKey: "coverage.family.risk",
    depth: "exploratory",
    tested: ["volatility_21/63d", "beta_252d", "vix_ar_surprise"],
    exploratory: ["downside_beta", "idiosyncratic_vol", "return_skew", "worst_day_dd", "FF5 betas (mkt/smb/hml/rmw/cma)"],
    gaps: ["MAX (Bali-Cakici-Whitelaw)", "coskewness / cokurtosis", "BAB (Frazzini-Pedersen)", "Pastor-Stambaugh liquidity", "IV spread"],
    cite: "risk_factors.py (defined, unconfirmed)",
  },
  {
    familyKey: "coverage.family.liquidity",
    depth: "tested",
    tested: ["turnover_21d", "amihud_illiquidity_21d", "stakes_13d_event"],
    exploratory: [],
    gaps: ["PIN / VPIN", "order imbalance", "short interest (Rapach-Ringgenberg)", "Sadka transient/permanent"],
    cite: "Track B #41 / Phase D #34",
  },
  {
    familyKey: "coverage.family.sentiment",
    depth: "exploratory",
    tested: ["macro CPI/NFP surprise", "earnings_surprise"],
    exploratory: ["news_sentiment (GDELT, ingest)", "reddit (RSS, ingest)", "Form 4 (ingest)", "LLM-tone (prereg, not run)"],
    gaps: ["analyst dispersion/revs", "short-interest sentiment", "news scored into model"],
    cite: "Phase C #30 / Track LLM prereg",
  },
];

const DEPTH_META: Record<
  Depth,
  { icon: typeof CheckCircle2Icon; key: "coverage.depth.tested" | "coverage.depth.exploratory" | "coverage.depth.gap"; cls: string }
> = {
  tested: { icon: CheckCircle2Icon, key: "coverage.depth.tested", cls: "text-emerald-600 dark:text-emerald-400" },
  exploratory: { icon: CircleDashedIcon, key: "coverage.depth.exploratory", cls: "text-amber-600 dark:text-amber-400" },
  gap: { icon: MinusCircleIcon, key: "coverage.depth.gap", cls: "text-muted-foreground" },
};

export function CoverageMap() {
  const { t } = useI18n();
  return (
    <Card className="overflow-hidden">
      <CardHeader className="gap-2">
        <CardTitle className="text-base">{t("coverage.title")}</CardTitle>
        <CardDescription>{t("coverage.intro")}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {FAMILIES.map((f) => {
          const meta = DEPTH_META[f.depth];
          const Icon = meta.icon;
          return (
            <div key={f.familyKey} className="space-y-1.5 rounded-md border p-3">
              <div className="flex items-center justify-between gap-2">
                <span className="text-sm font-medium">{t(f.familyKey)}</span>
                <Badge variant="outline" className={cn("gap-1 px-1.5 py-0 text-[10px]", meta.cls)}>
                  <Icon className="size-2.5" />
                  {t(meta.key)}
                </Badge>
              </div>
              <div className="space-y-1 text-xs">
                {f.tested.length > 0 ? (
                  <div className="flex flex-wrap items-baseline gap-x-1.5">
                    <span className="text-[10px] uppercase text-emerald-600/80 dark:text-emerald-400/80">{t("coverage.label.tested")}:</span>
                    {f.tested.map((x) => (
                      <span key={x} className="font-mono text-[11px] text-foreground/80">{x}</span>
                    ))}
                  </div>
                ) : null}
                {f.exploratory.length > 0 ? (
                  <div className="flex flex-wrap items-baseline gap-x-1.5">
                    <span className="text-[10px] uppercase text-amber-600/80 dark:text-amber-400/80">{t("coverage.label.exploratory")}:</span>
                    {f.exploratory.map((x) => (
                      <span key={x} className="font-mono text-[11px] text-muted-foreground">{x}</span>
                    ))}
                  </div>
                ) : null}
                {f.gaps.length > 0 ? (
                  <div className="flex flex-wrap items-baseline gap-x-1.5">
                    <span className="text-[10px] uppercase text-muted-foreground/70">{t("coverage.label.gaps")}:</span>
                    {f.gaps.map((x) => (
                      <span key={x} className="font-mono text-[11px] text-muted-foreground/60">{x}</span>
                    ))}
                  </div>
                ) : null}
              </div>
              {f.cite ? (
                <p className="font-mono text-[10px] text-muted-foreground/60">{f.cite}</p>
              ) : null}
            </div>
          );
        })}
        <p className="border-t pt-2 text-[10px] text-muted-foreground/70">
          {t("coverage.boundary")}
        </p>
      </CardContent>
    </Card>
  );
}
