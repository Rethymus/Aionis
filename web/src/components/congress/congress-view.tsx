"use client";

import { useMemo, useState } from "react";
import { ExternalLinkIcon, ShieldAlertIcon } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { cn } from "@/lib/utils";
import { fmtDateShort } from "@/lib/format";
import { FilterPills, LoadMoreFooter, usePaged } from "@/components/stream/stream-kit";
import { AvatarInitials } from "@/components/stream/avatar-initials";
import { useI18n } from "@/i18n/provider";
import { aionis } from "@/data/aionis";

const PAGE_SIZE = 50;

type PartyFilter = "all" | "R" | "D" | "I";

/** Party chip, xiaoyinsi-alignment style: US-convention tinted fill (blue for
 *  D, red for R — identity colors, not semantic colors, so the project's
 *  emerald/rose/amber semantics stay untouched). Small square-ish radius,
 *  mono, 11px — matches the measured 10px/600/4px reference. */
function PartyBadge({ party }: { party: string | null }) {
  if (!party) return null;
  const cls =
    party === "D"
      ? "bg-primary/10 text-primary"
      : party === "R"
        ? "bg-rose-500/10 text-rose-600 dark:text-rose-400"
        : "bg-muted text-muted-foreground";
  return (
    <span
      className={cn(
        "ml-2 inline-block rounded-[4px] px-1.5 py-px font-mono text-[11px] font-semibold leading-4",
        cls,
      )}
    >
      {party}
    </span>
  );
}

export function CongressView() {
  const { t } = useI18n();
  const f = aionis.politicianTrades;
  const [party, setParty] = useState<PartyFilter>("all");
  const { visibleCount, reset, loadMore } = usePaged(PAGE_SIZE);

  const filings = f.status === "ok" ? f.house.filings : [];
  const partyCounts = useMemo(() => {
    const c: Record<string, number> = { R: 0, D: 0, I: 0 };
    for (const p of filings) {
      if (p.party && p.party in c) c[p.party] += 1;
    }
    return c;
  }, [filings]);

  const filtered = useMemo(
    () => (party === "all" ? filings : filings.filter((p) => p.party === party)),
    [filings, party],
  );
  const visible = filtered.slice(0, visibleCount);

  const applyParty = (k: PartyFilter) => {
    setParty(k);
    reset();
  };

  if (f.status !== "ok" || filings.length === 0) {
    return (
      <div className="space-y-6 p-4 md:p-6">
        <header className="space-y-1">
          <h1 className="text-2xl font-bold tracking-tight">
            {t("congress.title")}
          </h1>
          <p className="text-sm text-muted-foreground">{t("congress.window")}</p>
        </header>
        <Card className="border-amber-500/30 bg-amber-500/5">
          <CardContent className="space-y-1 p-4">
            <p className="text-sm font-medium text-amber-700 dark:text-amber-400">
              {t("congress.awaiting")}
            </p>
            <p className="text-xs text-muted-foreground">{f.methodology}</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>{t("congress.total")}</CardDescription>
            <CardTitle className="text-2xl tabular-nums">{f.house.total}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>{t("congress.members")}</CardDescription>
            <CardTitle className="text-2xl tabular-nums">{f.house.members}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>{t("congress.window_label")}</CardDescription>
            <CardTitle className="text-sm font-medium tabular-nums">
              {f.window_years.join(" · ")}
            </CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>{t("congress.by_year")}</CardDescription>
            <CardTitle className="text-sm font-medium tabular-nums">
              {Object.entries(f.house.by_year)
                .map(([y, n]) => `${y}: ${n}`)
                .join(" / ")}
            </CardTitle>
          </CardHeader>
        </Card>
      </div>

      <div className="grid items-start gap-6 lg:grid-cols-[1fr_320px]">
        <Card className="min-w-0">
          <CardHeader className="pb-3">
            <CardTitle>{t("congress.stream_title")}</CardTitle>
            <CardDescription>{t("congress.stream_note")}</CardDescription>
            <div className="pt-1">
              <FilterPills<PartyFilter>
                label={t("congress.party.label")}
                value={party}
                onChange={applyParty}
                options={[
                  { key: "all", label: t("congress.party.all"), count: filings.length },
                  { key: "R", label: t("congress.party.R"), count: partyCounts.R },
                  { key: "D", label: t("congress.party.D"), count: partyCounts.D },
                  { key: "I", label: t("congress.party.I"), count: partyCounts.I },
                ]}
              />
            </div>
          </CardHeader>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t("congress.member")}</TableHead>
                  <TableHead>{t("congress.office")}</TableHead>
                  <TableHead>{t("congress.type")}</TableHead>
                  <TableHead>{t("congress.date")}</TableHead>
                  <TableHead className="text-right">{t("congress.source")}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {visible.map((p) => (
                  <TableRow key={p.doc_url}>
                    <TableCell>
                      <a
                        href={p.doc_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="font-medium text-primary hover:underline"
                      >
                        {p.member}
                      </a>
                      <PartyBadge party={p.party} />
                    </TableCell>
                    <TableCell className="font-mono text-xs text-muted-foreground">
                      {p.office}
                    </TableCell>
                    <TableCell>
                      <Badge variant="secondary">{p.filing_type}</Badge>
                    </TableCell>
                    <TableCell
                      className="whitespace-nowrap tabular-nums text-muted-foreground"
                      title={p.filing_date ?? undefined}
                    >
                      {fmtDateShort(p.filing_date)}
                    </TableCell>
                    <TableCell className="text-right">
                      <a
                        href={p.doc_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-primary hover:underline"
                      >
                        PDF
                        <ExternalLinkIcon className="size-3" />
                      </a>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            <LoadMoreFooter
              shown={visible.length}
              total={filtered.length}
              onLoadMore={loadMore}
              pageSize={PAGE_SIZE}
            />
          </CardContent>
        </Card>

        {/* "Most active filers" sidebar (xiaoyinsi-style person list): avatar
            initials + member + district + filing count. top_members carries NO
            party field (member/office/count only) — party chips stay on the
            stream rows where the join is per-filing, never fabricated here. */}
        <Card className="overflow-hidden py-0">
          <CardHeader className="border-b">
            <CardTitle className="text-base">{t("congress.top_filers")}</CardTitle>
            <CardDescription>{t("congress.top_filers_note")}</CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            <div className="divide-y">
              {f.house.top_members.map((m) => (
                <div
                  key={`${m.member}-${m.office}`}
                  className="flex items-center gap-2.5 px-4 py-2"
                >
                  <AvatarInitials name={m.member} />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium" title={m.member}>
                      {m.member}
                    </p>
                    <p className="font-mono text-[11px] text-muted-foreground">
                      {m.office}
                    </p>
                  </div>
                  <span className="ml-auto shrink-0 font-mono text-xs tabular-nums text-muted-foreground">
                    ×{m.count}
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      <Card className="border-amber-500/30 bg-amber-500/5">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <ShieldAlertIcon className="size-4 text-amber-600 dark:text-amber-400" />
            {t("congress.senate_blocked")}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-xs leading-relaxed text-muted-foreground">
            {f.senate.note}
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle>{t("congress.methodology")}</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-xs leading-relaxed text-muted-foreground">
            {f.methodology}
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
