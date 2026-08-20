"use client";

import Link from "next/link";
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
import { useI18n } from "@/i18n/provider";
import { aionis } from "@/data/aionis";

function fmtUsd(v: number): string {
  if (Math.abs(v) >= 1e12) return `$${(v / 1e12).toFixed(2)}T`;
  if (Math.abs(v) >= 1e9) return `$${(v / 1e9).toFixed(1)}B`;
  if (Math.abs(v) >= 1e6) return `$${(v / 1e6).toFixed(1)}M`;
  if (Math.abs(v) >= 1e3) return `$${(v / 1e3).toFixed(0)}K`;
  return `$${v.toFixed(0)}`;
}

function fmtShares(v: number): string {
  if (Math.abs(v) >= 1e9) return `${(v / 1e9).toFixed(2)}B`;
  if (Math.abs(v) >= 1e6) return `${(v / 1e6).toFixed(1)}M`;
  if (Math.abs(v) >= 1e3) return `${(v / 1e3).toFixed(0)}K`;
  return `${v.toFixed(0)}`;
}

// Quarter-over-quarter change chips. Direction color convention follows the
// project's up/down utility classes (never hardcoded emerald/rose):
// new = primary emphasis, increased = up, reduced = down, exited = muted.
const DIRECTION_CLASS: Record<string, string> = {
  new: "",
  increased: "text-up",
  reduced: "text-down",
  exited: "text-muted-foreground",
};

// Map the JSON direction enum onto i18n keys (t() takes a strict DictKey —
// no template-literal keys).
const DIRECTION_LABEL: Record<string, "institutions.change_new" | "institutions.change_increased" | "institutions.change_reduced" | "institutions.change_exited"> = {
  new: "institutions.change_new",
  increased: "institutions.change_increased",
  reduced: "institutions.change_reduced",
  exited: "institutions.change_exited",
};

function IssuerLabel({
  issuer,
  ticker,
}: {
  issuer: string;
  ticker: string | null;
}) {
  if (ticker) {
    return (
      <Link
        href={`/stock/${ticker}`}
        className="font-medium text-primary hover:underline"
      >
        {issuer}
      </Link>
    );
  }
  // No ticker link (CUSIP→ticker map has no entry) — honest plain text.
  return <span className="font-medium">{issuer}</span>;
}

export function InstitutionsView() {
  const { t } = useI18n();
  const f = aionis.form13f;

  if (f.status !== "ok" || f.managers.length === 0) {
    return (
      <div className="space-y-6 p-4 md:p-6">
        <header className="space-y-1">
          <h1 className="text-2xl font-bold tracking-tight">
            {t("institutions.title")}
          </h1>
          <p className="text-sm text-muted-foreground">{t("institutions.window")}</p>
        </header>
        <Card className="border-amber-500/30 bg-amber-500/5">
          <CardContent className="space-y-1 p-4">
            <p className="text-sm font-medium text-amber-700 dark:text-amber-400">
              {t("institutions.awaiting")}
            </p>
            <p className="text-xs text-muted-foreground">{f.methodology}</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const combinedValue = f.managers.reduce((acc, m) => acc + m.total_value, 0);

  return (
    <div className="space-y-6 p-4 md:p-6">
      <p className="text-xs font-medium text-primary">{t("institutions.role")}</p>
      <header className="space-y-1">
        <h1 className="text-2xl font-bold tracking-tight">{t("institutions.title")}</h1>
        <p className="text-sm text-muted-foreground">{t("institutions.window")}</p>
      </header>

      <div className="grid grid-cols-3 gap-3">
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">{t("institutions.kpi_managers")}</p>
            <p className="mt-1 text-2xl font-bold tabular-nums">{f.managers.length}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">{t("institutions.kpi_quarter")}</p>
            <p className="mt-1 text-2xl font-bold tabular-nums">{f.as_of}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">{t("institutions.kpi_value")}</p>
            <p className="mt-1 text-2xl font-bold tabular-nums">{fmtUsd(combinedValue)}</p>
          </CardContent>
        </Card>
      </div>

      {f.managers.map((m) => (
        <Card key={m.cik} className="overflow-hidden py-0">
          <CardHeader className="border-b">
            <div className="flex flex-wrap items-center gap-2">
              <CardTitle className="text-base">{m.name}</CardTitle>
              {m.zh_name ? (
                <span className="text-sm text-muted-foreground">{m.zh_name}</span>
              ) : null}
              <Badge variant="secondary" className="tabular-nums">{m.quarter}</Badge>
              <span className="ml-auto text-xs text-muted-foreground">
                {t("institutions.filed")} {m.filed}
              </span>
            </div>
            <CardDescription className="tabular-nums">
              {t("institutions.n_positions")}: {m.n_positions} ·{" "}
              {t("institutions.total_value")}: {fmtUsd(m.total_value)}
            </CardDescription>
          </CardHeader>

          <CardContent className="p-0">
            <p className="border-b px-4 py-2 text-xs font-medium text-muted-foreground">
              {t("institutions.top10")}
            </p>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-8">#</TableHead>
                  <TableHead>{t("institutions.col_issuer")}</TableHead>
                  <TableHead className="text-right">{t("institutions.col_value")}</TableHead>
                  <TableHead className="text-right">{t("institutions.col_shares")}</TableHead>
                  <TableHead className="text-right">{t("institutions.col_pct")}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {m.top10.map((h, i) => (
                  <TableRow key={`${h.cusip}-${h.option}-${i}`}>
                    <TableCell className="text-muted-foreground tabular-nums">
                      {i + 1}
                    </TableCell>
                    <TableCell>
                      <IssuerLabel issuer={h.issuer} ticker={h.ticker} />
                      {h.option === "CALL" || h.option === "PUT" ? (
                        <Badge variant="outline" className="ml-2 px-1.5 py-0 text-[10px]">
                          {h.option === "CALL"
                            ? t("institutions.option_call")
                            : t("institutions.option_put")}
                        </Badge>
                      ) : null}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {fmtUsd(h.value)}
                    </TableCell>
                    <TableCell className="text-right tabular-nums text-muted-foreground">
                      {fmtShares(h.shares)}
                    </TableCell>
                    <TableCell className="text-right tabular-nums font-medium">
                      {h.pct.toFixed(2)}%
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>

          <div className="border-t px-4 py-3">
            <p className="mb-2 text-xs font-medium text-muted-foreground">
              {t("institutions.changes")}
            </p>
            {m.changes.length === 0 ? (
              <p className="text-xs text-muted-foreground">
                {t("institutions.no_changes")}
              </p>
            ) : (
              <div className="flex flex-wrap items-center gap-1.5">
                {m.changes.map((c, i) => (
                  <span
                    key={`${c.cusip}-${c.direction}-${i}`}
                    className="inline-flex items-center gap-1 text-sm"
                  >
                    {c.direction === "new" ? (
                      <Badge className="px-1.5 text-[11px]">
                        {t("institutions.change_new")}
                      </Badge>
                    ) : (
                      <Badge
                        variant="outline"
                        className={cn(
                          "px-1.5 text-[11px]",
                          DIRECTION_CLASS[c.direction],
                        )}
                      >
                        {t(DIRECTION_LABEL[c.direction])}
                      </Badge>
                    )}
                    {c.ticker ? (
                      <Link
                        href={`/stock/${c.ticker}`}
                        className="text-primary hover:underline"
                      >
                        {c.ticker}
                      </Link>
                    ) : null}
                    <span className="text-muted-foreground">{c.issuer}</span>
                    {c.option === "CALL" || c.option === "PUT" ? (
                      <Badge variant="outline" className="px-1 py-0 text-[10px] text-muted-foreground">
                        {c.option === "CALL"
                          ? t("institutions.option_call")
                          : t("institutions.option_put")}
                      </Badge>
                    ) : null}
                    {c.delta_pct != null ? (
                      <span
                        className={cn(
                          "font-mono text-xs tabular-nums",
                          DIRECTION_CLASS[c.direction],
                        )}
                      >
                        {c.delta_pct > 0 ? "+" : ""}
                        {c.delta_pct.toFixed(1)}%
                      </span>
                    ) : null}
                  </span>
                ))}
              </div>
            )}
          </div>
        </Card>
      ))}

      <p className="text-xs text-muted-foreground">{t("institutions.explain")}</p>
    </div>
  );
}
