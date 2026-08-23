"use client";

import Link from "next/link";
import { useState } from "react";
import { ArrowLeftIcon, ExternalLinkIcon } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { ProvenanceBadge } from "@/components/provenance-badge";
import { useI18n } from "@/i18n/provider";
import { form13f } from "@/data/aionis/form13f";
import {
  categoryLabelKey,
  ChangesBlock,
  ConcentrationBlock,
  fmtUsd,
  PositionsTable,
} from "@/components/institutions/manager-book";

// /manager/[cik] — static per-manager detail page over the same committed
// form13f.json the /institutions directory reads (generateStaticParams covers
// every manager CIK; the data barrel is inlined at build time, so the page
// renders with zero client fetches). Visible book (up to 50 positions) +
// concentration widget and the quarter-over-quarter changes tab reuse the
// shared manager-book components — the two surfaces cannot drift. EDGAR link
// goes to the filer's public 13F-HR history (provenance).
type BookTab = "holdings" | "changes";

export function ManagerView({ cik }: { cik: string }) {
  const { t } = useI18n();
  const f = form13f;
  const m = f.managers.find((x) => x.cik === cik);
  const [tab, setTab] = useState<BookTab>("holdings");

  if (!m) {
    // Unreachable via generateStaticParams, but honest if a stale link or a
    // hand-typed CIK lands here — never a fabricated book.
    return (
      <div className="space-y-4 p-4 md:p-6">
        <Card className="border-amber-500/30 bg-amber-500/5">
          <CardContent className="space-y-2 p-4">
            <p className="text-sm font-medium text-amber-700 dark:text-amber-400">
              {t("manager.not_found")} (CIK {cik})
            </p>
            <Link
              href="/institutions"
              className="inline-flex items-center gap-1 text-sm text-primary hover:underline"
            >
              <ArrowLeftIcon className="size-3.5" />
              {t("manager.back")}
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-4 md:p-6">
      <Link
        href="/institutions"
        className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
      >
        <ArrowLeftIcon className="size-3.5" />
        {t("manager.back")}
      </Link>

      <header className="space-y-2">
        <p className="text-xs font-medium text-primary">{t("manager.role")}</p>
        <div className="flex flex-wrap items-center gap-2">
          <h1 className="text-2xl font-bold tracking-tight">{m.name}</h1>
          {m.zh_name ? (
            <span className="text-sm text-muted-foreground">{m.zh_name}</span>
          ) : null}
          <Badge variant="secondary">{t(categoryLabelKey(m.category))}</Badge>
          <ProvenanceBadge ts={f.snapshot_ts} source="SEC EDGAR 13F-HR" />
        </div>
        <p className="text-sm text-muted-foreground">
          {t("institutions.window")} · {t("institutions.filed")} {m.filed}
        </p>
        <a
          href={`https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=${m.cik}&type=13F-HR`}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-1 text-xs text-primary hover:underline"
        >
          {t("manager.edgar")}
          <ExternalLinkIcon className="size-3" />
        </a>
      </header>

      <div className="grid grid-cols-3 gap-3">
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">{t("institutions.n_positions")}</p>
            <p className="mt-1 text-2xl font-bold tabular-nums">{m.n_positions}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">{t("institutions.total_value")}</p>
            <p className="mt-1 text-2xl font-bold tabular-nums">
              {fmtUsd(m.total_value)}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">{t("institutions.kpi_quarter")}</p>
            <p className="mt-1 text-2xl font-bold tabular-nums">{m.quarter}</p>
          </CardContent>
        </Card>
      </div>

      <Card className="overflow-hidden py-0">
        <CardHeader className="border-b">
          <div className="flex flex-wrap items-center gap-2">
            <CardTitle className="text-base">{t("institutions.book")}</CardTitle>
            <Badge variant="secondary" className="tabular-nums">{m.quarter}</Badge>
            {/* Book tabs: visible holdings vs quarter-over-quarter changes
                (xiaoyinsi-style two-tab manager page; client state only —
                static-export safe). */}
            <span className="ml-auto flex items-center gap-1">
              {(["holdings", "changes"] as BookTab[]).map((k) => (
                <button
                  key={k}
                  type="button"
                  onClick={() => setTab(k)}
                  aria-pressed={tab === k}
                  className={cn(
                    "rounded-full border px-3 py-1 text-xs font-medium transition-colors",
                    tab === k
                      ? "border-primary bg-primary text-primary-foreground"
                      : "border-border text-muted-foreground hover:bg-muted",
                  )}
                >
                  {t(k === "holdings" ? "manager.tab_holdings" : "manager.tab_changes")}
                  <span className="ml-1.5 font-mono text-[11px] tabular-nums opacity-80">
                    {k === "holdings" ? m.positions.length : m.changes.length}
                  </span>
                </button>
              ))}
            </span>
          </div>
          <CardDescription className="tabular-nums">
            {t("institutions.n_positions")}: {m.n_positions} ·{" "}
            {t("institutions.total_value")}: {fmtUsd(m.total_value)}
          </CardDescription>
        </CardHeader>
        {tab === "holdings" ? (
          <>
            <CardContent className="p-0">
              <PositionsTable manager={m} />
            </CardContent>
            <div className="border-t">
              <ConcentrationBlock manager={m} />
            </div>
          </>
        ) : (
          <CardContent className="space-y-3 p-4">
            {/* Four-state KPI counts (xiaoyinsi's 调仓 header), honest zeros. */}
            <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
              {(["new", "increased", "reduced", "exited"] as const).map((d) => (
                <div key={d} className="rounded-md border p-3">
                  <p className="text-xs text-muted-foreground">
                    {t(`institutions.change_${d}` as const)}
                  </p>
                  <p className="mt-1 text-xl font-bold tabular-nums">
                    {m.changes.filter((c) => c.direction === d).length}
                  </p>
                </div>
              ))}
            </div>
            <ChangesBlock manager={m} />
          </CardContent>
        )}
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">{t("manager.methodology")}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <p className="text-xs text-muted-foreground">{f.methodology}</p>
          <p className="text-xs text-muted-foreground">
            {t("institutions.cat_note")}
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
