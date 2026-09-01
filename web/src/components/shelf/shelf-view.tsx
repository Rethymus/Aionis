"use client";

import { useMemo, useState } from "react";
import { ArrowUpRightIcon, BookOpenIcon, FileCheckIcon, TableIcon } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ProvenanceBadge } from "@/components/provenance-badge";
import { cn } from "@/lib/utils";
import { useI18n } from "@/i18n/provider";
import type { DictKey } from "@/i18n/dict";
import {
  aionis,
  type KnowledgeShelfCategory,
  type KnowledgeShelfDoc,
} from "@/data/aionis";

// Method shelf (reference "bookshelf" equivalent, no content appropriation):
// layer 1 catalogs OUR OWN method docs (docs/ + decisions/, repo MIT) —
// metadata + a safe teaser slice exported at build time, body on GitHub
// (link-out). Layer 2 is a FIXED editorially-curated bookmark list of
// first-hand public research sources — link-out + one static sentence,
// nothing fetched. Zero network, zero research-pipeline surface.

const CATEGORY_ORDER: KnowledgeShelfCategory[] = [
  "preregistration",
  "adr",
  "results",
  "rubric",
  "theory",
];

const CATEGORY_LABEL: Record<KnowledgeShelfCategory, DictKey> = {
  preregistration: "shelf.cat.preregistration",
  adr: "shelf.cat.adr",
  results: "shelf.cat.results",
  theory: "shelf.cat.theory",
  rubric: "shelf.cat.rubric",
};

// Matrix row order for the R2-full L5 evidence matrix table (B/C/D/E1 phases
// + the Track C confirmatory OOS row).
const MATRIX_ROW_ORDER = ["B", "C", "D", "E1", "track_c"] as const;

function Kpi({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex flex-col gap-1 rounded-lg border bg-card p-4">
      <span className="text-2xl font-bold tabular-nums">{value}</span>
      <span className="text-xs text-muted-foreground">{label}</span>
    </div>
  );
}

function DocCard({ doc }: { doc: KnowledgeShelfDoc }) {
  const { t } = useI18n();
  return (
    <Card className="flex flex-col py-0 transition-colors hover:border-primary/40">
      <CardContent className="flex flex-1 flex-col gap-2 p-4">
        <div className="flex flex-wrap items-center gap-2">
          <Badge
            variant="outline"
            className="px-1.5 py-0 text-[11px] font-normal text-muted-foreground"
          >
            {t(CATEGORY_LABEL[doc.category])}
          </Badge>
          <span className="font-mono text-[11px] tabular-nums text-muted-foreground">
            {doc.date ?? "—"}
          </span>
          <span className="ml-auto font-mono text-[11px] tabular-nums text-muted-foreground/70">
            {t("shelf.chars").replace("{n}", doc.n_chars.toLocaleString())}
          </span>
        </div>
        <h2 className="text-sm font-semibold leading-snug">{doc.title}</h2>
        {/* Two-line teaser (line-clamp keeps cards even); the body stays on
            GitHub — this is a catalog entry, not a copy. */}
        <p className="line-clamp-2 text-xs leading-relaxed text-muted-foreground">
          {doc.summary}
        </p>
        <a
          href={doc.url}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-auto inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"
        >
          {t("shelf.read")}
          <ArrowUpRightIcon className="size-3" aria-hidden />
        </a>
      </CardContent>
    </Card>
  );
}

const pillCls = (active: boolean) =>
  cn(
    "rounded-full border px-3 py-1 text-xs font-medium transition-colors",
    active
      ? "border-primary bg-primary text-primary-foreground"
      : "border-border text-muted-foreground hover:bg-muted",
  );

export function ShelfView() {
  const { t, lang } = useI18n();
  const shelf = aionis.knowledgeShelf;
  const evidenceMatrix = aionis.evidenceMatrix;
  const [category, setCategory] = useState<KnowledgeShelfCategory | "all">("all");

  const filtered = useMemo(
    () =>
      category === "all"
        ? shelf.docs
        : shelf.docs.filter((d) => d.category === category),
    [category, shelf.docs],
  );

  const countLine = t("shelf.count")
    .replace("{shown}", filtered.length.toLocaleString())
    .replace("{total}", shelf.n_docs.toLocaleString());

  return (
    <div className="space-y-4">
      <p className="text-xs font-medium text-primary">{t("shelf.role")}</p>
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-[-0.032em]">
            {t("shelf.title")}
          </h1>
        </div>
        <ProvenanceBadge ts={shelf.as_of} />
      </header>

      {/* KPI row: cataloged docs / category rails / curated link-outs. */}
      <div className="grid grid-cols-3 gap-3">
        <Kpi label={t("shelf.kpi.docs")} value={shelf.n_docs} />
        <Kpi label={t("shelf.kpi.categories")} value={shelf.n_categories} />
        <Kpi
          label={t("shelf.kpi.sources")}
          value={shelf.research_sources.length}
        />
      </div>

      {/* Category filter pills (the 5 fixed rails, each with its count). */}
      <Card className="py-0">
        <CardContent className="flex flex-wrap items-center gap-2 p-4">
          <span className="text-xs text-muted-foreground">
            {t("shelf.filter.category")}
          </span>
          <button
            type="button"
            onClick={() => setCategory("all")}
            aria-pressed={category === "all"}
            className={pillCls(category === "all")}
          >
            {t("shelf.filter.all")}
          </button>
          {CATEGORY_ORDER.map((c) => (
            <button
              key={c}
              type="button"
              onClick={() => setCategory(c)}
              aria-pressed={category === c}
              className={pillCls(category === c)}
            >
              {t(CATEGORY_LABEL[c])}
              <span className="ml-1 font-mono tabular-nums opacity-70">
                {shelf.categories[c]}
              </span>
            </button>
          ))}
          <span className="ml-auto font-mono text-xs tabular-nums text-muted-foreground">
            {countLine}
          </span>
        </CardContent>
      </Card>

      {/* Bibliography grid. Honest empty state when a rail is empty. */}
      {filtered.length === 0 ? (
        <p className="p-6 text-center text-sm italic text-muted-foreground">
          {t("shelf.empty")}
        </p>
      ) : (
        <div className="grid items-stretch gap-3 md:grid-cols-2 xl:grid-cols-3">
          {filtered.map((d) => (
            <DocCard key={d.path} doc={d} />
          ))}
        </div>
      )}

      {/* Curated outbound layer: editorial bookmarks over first-hand public
          research sources — link-out only, nothing fetched. */}
      <Card className="border-muted py-0">
        <CardHeader className="border-b">
          <CardTitle className="flex items-center gap-2 text-base">
            <BookOpenIcon className="size-4 text-muted-foreground" />
            {t("shelf.sources.title")}
          </CardTitle>
          <CardDescription>{t("shelf.sources.note")}</CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          <div className="grid divide-y md:grid-cols-2 md:divide-y-0 xl:grid-cols-4">
            {shelf.research_sources.map((s) => (
              <a
                key={s.url}
                href={s.url}
                target="_blank"
                rel="noopener noreferrer"
                className="group flex flex-col gap-1 border-border/60 p-4 transition-colors hover:bg-muted/50 md:border-l md:first:border-l-0 xl:[&:nth-child(4n+1)]:border-l-0"
              >
                <span className="flex items-center gap-1 text-sm font-semibold group-hover:text-primary">
                  {s.name}
                  <ArrowUpRightIcon className="size-3 shrink-0" aria-hidden />
                </span>
                <span className="text-[11px] text-muted-foreground">
                  {s.org}
                </span>
                <span className="text-xs leading-relaxed text-muted-foreground">
                  {lang === "zh" ? s.desc_zh : s.desc_en}
                </span>
              </a>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* R2-full L5 — five-claim evidence matrix: verbatim machine-read
          values from the S1 manifest panel (differentials + ledger rows +
          metrics). Non-significance is not equivalence — the note says so. */}
      <Card className="border-muted py-0">
        <CardHeader className="border-b">
          <CardTitle className="flex items-center gap-2 text-base">
            <TableIcon className="size-4 text-muted-foreground" />
            {t("shelf.matrix.title")}
          </CardTitle>
          <CardDescription>{t("shelf.matrix.note")}</CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-line2 text-muted-foreground">
                <tr>
                  <th className="px-4 py-2.5 font-medium">{t("shelf.matrix.col.phase")}</th>
                  <th className="px-4 py-2.5 font-medium">{t("shelf.matrix.col.metric")}</th>
                  <th className="px-4 py-2.5 font-medium">{t("shelf.matrix.col.ci")}</th>
                  <th className="px-4 py-2.5 font-medium">{t("shelf.matrix.col.p")}</th>
                  <th className="px-4 py-2.5 font-medium">{t("shelf.matrix.col.n")}</th>
                  <th className="px-4 py-2.5 font-medium">{t("shelf.matrix.col.verdict")}</th>
                  <th className="px-4 py-2.5 font-medium">{t("shelf.matrix.prereg")}</th>
                </tr>
              </thead>
              <tbody>
                {MATRIX_ROW_ORDER.map((phase) => {
                  const c = evidenceMatrix.claims[phase];
                  if (!c) return null;
                  const metric = c.combined_ic ?? c.mean_diff ?? 0;
                  const p = c.p_hac ?? c.dm_p_mbb ?? null;
                  return (
                    <tr key={phase} className="border-t border-line2">
                      <td className="px-4 py-2.5 font-mono font-semibold">{c.phase}</td>
                      <td className="px-4 py-2.5 font-mono tabular-nums">
                        {metric > 0 ? "+" : ""}{metric.toFixed(4)}
                      </td>
                      <td className="px-4 py-2.5 font-mono tabular-nums">
                        [{c.ci_lo.toFixed(4)}, {c.ci_hi.toFixed(4)}]
                      </td>
                      <td className="px-4 py-2.5 font-mono tabular-nums">
                        {p !== null && p !== undefined ? p.toFixed(3) : "—"}
                      </td>
                      <td className="px-4 py-2.5 font-mono tabular-nums">{c.n_months}</td>
                      <td className="px-4 py-2.5">
                        {c.phase === "track_c" && c.verdict ? (
                          <Badge variant="secondary" className="bg-slate-500/15 text-slate-600 dark:text-slate-300">
                            {c.verdict}
                          </Badge>
                        ) : (
                          <span className="text-muted-foreground">
                            {t("shelf.matrix.verdict.nullincr")}
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-2.5">
                        <a
                          href={`https://github.com/Rethymus/Aionis/blob/main/${c.prereg_doc}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-0.5 text-primary hover:underline"
                        >
                          {t("shelf.matrix.prereg")}
                          <ArrowUpRightIcon className="size-3 shrink-0" aria-hidden />
                        </a>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Generated evidence layer: the round-produced self-contained HTML
          artifacts — export-time sha256 pins let the reader verify the
          downloaded bytes against the catalog (missing file degrades to "—",
          never fabricated). */}
      <Card className="border-muted py-0">
        <CardHeader className="border-b">
          <CardTitle className="flex items-center gap-2 text-base">
            <FileCheckIcon className="size-4 text-muted-foreground" />
            {t("shelf.artifacts.title")}
          </CardTitle>
          <CardDescription>{t("shelf.artifacts.note")}</CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          <div className="grid divide-y md:grid-cols-2 md:divide-y-0">
            {shelf.evidence_artifacts.map((a) => (
              <a
                key={a.id}
                href={a.url}
                target="_blank"
                rel="noopener noreferrer"
                className="group flex flex-col gap-1 border-border/60 p-4 transition-colors hover:bg-muted/50 md:border-l md:first:border-l-0"
              >
                <span className="flex items-center gap-1 text-sm font-semibold group-hover:text-primary">
                  {lang === "zh" ? a.name_zh : a.name_en}
                  <ArrowUpRightIcon className="size-3 shrink-0" aria-hidden />
                </span>
                <span className="font-mono text-[11px] text-muted-foreground">
                  {a.id}
                </span>
                <span className="text-xs leading-relaxed text-muted-foreground">
                  {lang === "zh" ? a.desc_zh : a.desc_en}
                </span>
                {/* sha256 first 12 chars + byte count — the reader-side
                    verification pair; "—" is the honest-null degradation. */}
                <span className="flex flex-wrap items-center gap-x-3 font-mono text-[11px] tabular-nums text-muted-foreground/70">
                  <span>
                    {t("shelf.artifacts.sha")}{" "}
                    {a.sha256 ? a.sha256.slice(0, 12) : "—"}
                  </span>
                  <span>
                    {a.n_bytes !== null ? `${a.n_bytes.toLocaleString()} B` : "—"}
                  </span>
                </span>
              </a>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Methodology: own-content MIT + editorial link-out framing — part of
          the page, not a footnote. */}
      <Card className="border-muted">
        <CardHeader>
          <CardTitle className="text-sm">
            {t("shelf.methodology.title")}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <p className="text-xs leading-relaxed text-muted-foreground">
            {t("shelf.intro")}
          </p>
          <p className="font-mono text-xs leading-relaxed text-muted-foreground">
            {shelf.methodology}
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
