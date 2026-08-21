"use client";

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
import { useI18n } from "@/i18n/provider";
import { aionis } from "@/data/aionis";

export function CongressView() {
  const { t } = useI18n();
  const f = aionis.politicianTrades;

  if (f.status !== "ok" || f.house.filings.length === 0) {
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

      <Card>
        <CardHeader className="pb-3">
          <CardTitle>{t("congress.top_filers")}</CardTitle>
          <CardDescription>{t("congress.top_filers_note")}</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          {f.house.top_members.map((m) => (
            <Badge key={`${m.member}-${m.office}`} variant="secondary" className="gap-1">
              {m.member}
              <span className="text-muted-foreground">{m.office}</span>
              <span className="tabular-nums text-muted-foreground">×{m.count}</span>
            </Badge>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle>{t("congress.stream_title")}</CardTitle>
          <CardDescription>{t("congress.stream_note")}</CardDescription>
        </CardHeader>
        <CardContent>
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
              {f.house.filings.map((p) => (
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
                    {p.party ? (
                      <Badge variant="outline" className="ml-2 px-1.5 py-0 font-mono text-[11px]">
                        {p.party}
                      </Badge>
                    ) : null}
                  </TableCell>
                  <TableCell className="font-mono text-xs text-muted-foreground">
                    {p.office}
                  </TableCell>
                  <TableCell>
                    <Badge variant="secondary">{p.filing_type}</Badge>
                  </TableCell>
                  <TableCell className="whitespace-nowrap tabular-nums text-muted-foreground">
                    {p.filing_date ?? "—"}
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
        </CardContent>
      </Card>

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
