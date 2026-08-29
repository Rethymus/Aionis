"use client";

import type { ReactNode } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { useI18n } from "@/i18n/provider";
import { aionis, type ModelCard, type ModelInventory, type ModelInventoryChain } from "@/data/aionis";
import {
  ArrowRightIcon,
  FileTextIcon,
  GitBranchIcon,
  ListIcon,
  ScrollTextIcon,
  ShieldAlertIcon,
  ShieldCheckIcon,
} from "lucide-react";
import Link from "next/link";

const REGIME_STYLE: Record<string, string> = {
  stable: "border-emerald-500/40 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400",
  moderate: "border-amber-500/40 bg-amber-500/10 text-amber-700 dark:text-amber-400",
  significant: "border-rose-500/40 bg-rose-500/10 text-rose-700 dark:text-rose-400",
};

// Literal-keyed so the strict `t(key)` union accepts it (template literals won't).
type RegimeLabelKey =
  | "modelhealth.regime.stable"
  | "modelhealth.regime.moderate"
  | "modelhealth.regime.significant";
const REGIME_LABEL: Record<string, RegimeLabelKey> = {
  stable: "modelhealth.regime.stable",
  moderate: "modelhealth.regime.moderate",
  significant: "modelhealth.regime.significant",
};

function Stat({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div title={hint}>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 text-xl font-bold tabular-nums">{value}</p>
    </div>
  );
}

// --- model card (TASK-H4) -----------------------------------------------------
//
// The machine-readable card of the frozen confirmatory model, rendered as an
// identity row card + per-section field tables. Every value is shown verbatim
// from model_card.json (no formatting beyond joins); hashes render mono; links
// point at the GitHub preregistration doc and the /discipline ledger audit.
// Honest empty state: with no card data the table headers still render.

type KVRow = { k: string; v: ReactNode };

function Sha({ value }: { value: string | null | undefined }) {
  if (!value) return <span className="text-muted-foreground">—</span>;
  return <code className="break-all font-mono text-xs">{value}</code>;
}

function Plain({ value }: { value: string | null | undefined }) {
  return value ? <span>{value}</span> : <span className="text-muted-foreground">—</span>;
}

function KVTable({
  title,
  rows,
  emptyText,
}: {
  title: string;
  rows: KVRow[];
  emptyText?: string;
}) {
  const { t } = useI18n();
  const empty = emptyText !== undefined;
  return (
    <div>
      <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        {title}
      </p>
      <table className="w-full border-collapse text-[13px]">
        <thead>
          <tr className="border-b text-left text-xs text-muted-foreground">
            <th className="w-56 py-1.5 pr-4 font-medium">{t("modelcard.col.field")}</th>
            <th className="py-1.5 font-medium">{t("modelcard.col.value")}</th>
          </tr>
        </thead>
        <tbody>
          {empty ? (
            <tr>
              <td className="py-2 text-muted-foreground" colSpan={2}>
                {emptyText}
              </td>
            </tr>
          ) : (
            rows.map((r) => (
              <tr key={r.k} className="border-b align-top last:border-0">
                <td className="py-1.5 pr-4 text-muted-foreground">{r.k}</td>
                <td className="py-1.5">{r.v}</td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}

function joinRecord(
  record: Record<string, number | string | null> | null,
  sep: string,
): string | null {
  if (!record || Object.keys(record).length === 0) return null;
  return Object.entries(record)
    .map(([k, v]) => `${k}${sep}${v === null ? "—" : String(v)}`)
    .join(" · ");
}

function ModelCardSection() {
  const { t } = useI18n();
  const card: ModelCard | undefined = aionis.modelCard;
  const present = !!card?.identity?.config_sig;
  const id = card?.identity;
  const res = card?.results;
  const gov = card?.governance;
  const ciText =
    res?.ci_lo != null && res.ci_hi != null ? `[${String(res.ci_lo)}, ${String(res.ci_hi)}]` : null;
  const freeze = gov?.ledger_freeze_row;
  const freezeText =
    freeze != null
      ? `#${freeze.row} · ${freeze.ts ?? "—"}`
      : null;

  return (
    <Card className="border-dashed">
      <CardHeader className="border-b">
        <CardTitle className="flex items-center gap-2 text-base">
          <FileTextIcon className="size-4" /> {t("modelcard.title")}
        </CardTitle>
        <CardDescription>{t("modelcard.subtitle")}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-5 p-4">
        <KVTable
          title={t("modelcard.section.identity")}
          emptyText={present ? undefined : t("modelcard.empty")}
          rows={
            present && id
              ? [
                  { k: t("modelcard.field.phase"), v: <Plain value={id.phase} /> },
                  {
                    k: t("modelcard.field.configSig"),
                    v: <Sha value={id.config_sig} />,
                  },
                  {
                    k: t("modelcard.field.resultsDir"),
                    v: <Sha value={id.results_dir} />,
                  },
                  {
                    k: t("modelcard.field.aionisVersion"),
                    v: <Plain value={id.aionis_version} />,
                  },
                  { k: t("modelcard.field.schema"), v: <Plain value={id.schema == null ? null : String(id.schema)} /> },
                  {
                    k: t("modelcard.field.h6"),
                    v: id.h6_deterministic ? (
                      <Badge variant="outline" className="border-emerald-500/40 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400">
                        PASS
                      </Badge>
                    ) : (
                      <Plain value={id.h6_deterministic == null ? null : "FAIL"} />
                    ),
                  },
                  {
                    k: t("modelcard.field.runTs"),
                    v: <Plain value={id.run_ts} />,
                  },
                ]
              : []
          }
        />

        {present && card && (
          <>
            <KVTable
              title={t("modelcard.section.intendedUse")}
              rows={[
                { k: t("modelcard.field.primaryUse"), v: <Plain value={card.intended_use.primary_use} /> },
                {
                  k: t("modelcard.field.displayOnly"),
                  v: <Plain value={card.intended_use.display_only ? "true" : "false"} />,
                },
                {
                  k: t("modelcard.field.notAdvice"),
                  v: (
                    <Plain
                      value={card.intended_use.not_investment_advice ? "true" : "false"}
                    />
                  ),
                },
                {
                  k: t("modelcard.field.prereg"),
                  v: (
                    <span className="flex flex-col gap-0.5">
                      <Sha value={card.intended_use.prereg.sha256} />
                      <a
                        className="inline-flex items-center gap-1 text-xs text-primary underline-offset-2 hover:underline"
                        href={`https://github.com/Rethymus/Aionis/blob/main/${card.intended_use.prereg.path}`}
                        target="_blank"
                        rel="noreferrer"
                      >
                        {t("modelcard.link.prereg")}
                      </a>
                    </span>
                  ),
                },
              ]}
            />

            <KVTable
              title={t("modelcard.section.data")}
              rows={[
                { k: t("modelcard.field.fundSha"), v: <Sha value={card.data.fund_sha256} /> },
                { k: t("modelcard.field.pricesSha"), v: <Sha value={card.data.prices_sha256} /> },
                {
                  k: t("modelcard.field.membershipSha"),
                  v: <Sha value={card.data.membership_sha256} />,
                },
                {
                  k: t("modelcard.field.endLag"),
                  v: <Plain value={joinRecord(card.data.end_lag_months, ": ")} />,
                },
                {
                  k: t("modelcard.field.featureCols"),
                  v: (
                    <Plain
                      value={
                        card.data.feature_cols && card.data.feature_cols_n != null
                          ? `${card.data.feature_cols_n} · ${card.data.feature_cols.join(", ")}`
                          : null
                      }
                    />
                  ),
                },
                { k: t("modelcard.field.universe"), v: <Plain value={card.data.universe_note} /> },
              ]}
            />

            <KVTable
              title={t("modelcard.section.model")}
              rows={[
                {
                  k: t("modelcard.field.learner"),
                  v: (
                    <Plain
                      value={
                        card.model.learner
                          ? `${card.model.learner} ${card.model.learner_version ?? ""}`.trim()
                          : null
                      }
                    />
                  ),
                },
                {
                  k: t("modelcard.field.versions"),
                  v: <Plain value={joinRecord(card.model.versions, " ")} />,
                },
                {
                  k: t("modelcard.field.frozenParams"),
                  v: <Plain value={joinRecord(card.model.frozen_params, "=")} />,
                },
                {
                  k: t("modelcard.field.determinism"),
                  v: <Plain value={joinRecord(card.model.determinism, "=")} />,
                },
              ]}
            />

            <KVTable
              title={t("modelcard.section.evaluation")}
              rows={[
                { k: t("modelcard.field.cvScheme"), v: <Plain value={card.evaluation_protocol.cv_scheme} /> },
                {
                  k: t("modelcard.field.horizon"),
                  v: <Plain value={card.evaluation_protocol.horizon == null ? null : String(card.evaluation_protocol.horizon)} />,
                },
                {
                  k: t("modelcard.field.nSplits"),
                  v: <Plain value={card.evaluation_protocol.n_splits == null ? null : String(card.evaluation_protocol.n_splits)} />,
                },
                {
                  k: t("modelcard.field.embargo"),
                  v: <Plain value={card.evaluation_protocol.embargo_sessions == null ? null : String(card.evaluation_protocol.embargo_sessions)} />,
                },
              ]}
            />

            <KVTable
              title={t("modelcard.section.results")}
              rows={[
                { k: t("modelcard.field.ic"), v: <Plain value={res?.combined_ic == null ? null : String(res.combined_ic)} /> },
                { k: t("modelcard.field.ci"), v: <Plain value={ciText} /> },
                { k: t("modelcard.field.p"), v: <Plain value={res?.p == null ? null : String(res.p)} /> },
                {
                  k: t("modelcard.field.nMonths"),
                  v: <Plain value={res?.n_months == null ? null : String(res.n_months)} />,
                },
                { k: t("modelcard.field.verdict"), v: <Plain value={res?.verdict} /> },
                {
                  k: t("modelcard.field.sesoi"),
                  v: <Plain value={res?.sesoi == null ? null : String(res.sesoi)} />,
                },
                { k: t("modelcard.field.resultSig"), v: <Sha value={res?.config_sig_short ?? null} /> },
                {
                  k: t("modelcard.field.ledgerRow"),
                  v: <Plain value={res?.ledger_row == null ? null : `#${res.ledger_row}`} />,
                },
              ]}
            />

            <KVTable
              title={t("modelcard.section.governance")}
              rows={[
                {
                  k: t("modelcard.field.freezeRow"),
                  v: <Plain value={freezeText} />,
                },
                { k: `${t("modelcard.field.freezeRow")} · sha256`, v: <Sha value={freeze?.line_sha256 ?? null} /> },
                {
                  k: t("modelcard.field.resultRow"),
                  v: <Plain value={gov ? `#${gov.ledger_result_row.row}` : null} />,
                },
                { k: t("modelcard.field.contract"), v: <Plain value={gov?.contract_note} /> },
                { k: t("modelcard.field.uvLockFrozen"), v: <Sha value={gov?.uv_lock_sha256} /> },
                {
                  k: t("modelcard.field.uvLockCurrent"),
                  v: <Sha value={gov?.uv_lock_recomputed_sha256} />,
                },
                {
                  k: t("modelcard.field.uvMatch"),
                  v: (
                    <span className="flex flex-col gap-0.5">
                      <Plain
                        value={
                          gov?.uv_lock_match == null
                            ? null
                            : gov.uv_lock_match
                              ? "true"
                              : "false"
                        }
                      />
                      {gov?.uv_lock_note ? (
                        <span className="text-xs text-muted-foreground">
                          {gov.uv_lock_note}
                        </span>
                      ) : null}
                    </span>
                  ),
                },
                {
                  k: t("modelcard.link.ledgerAudit"),
                  v: (
                    <Link
                      className="text-xs text-primary underline-offset-2 hover:underline"
                      href="/discipline"
                    >
                      {t("modelcard.link.ledgerAudit")}
                    </Link>
                  ),
                },
              ]}
            />

            <KVTable
              title={t("modelcard.section.provenance")}
              rows={[
                { k: t("modelcard.field.generatedBy"), v: <Plain value={card.provenance.generated_by} /> },
                { k: t("modelcard.field.regenCommand"), v: <Sha value={card.provenance.regen_command} /> },
                { k: t("modelcard.field.byteStability"), v: <Plain value={card.provenance.byte_stability} /> },
                {
                  k: t("modelcard.field.sources"),
                  v: (
                    <span className="flex flex-col gap-1">
                      {card.provenance.sources.map((s) => (
                        <span key={s.sid} className="text-xs">
                          <span className="font-mono font-semibold">{s.sid}</span>{" "}
                          <span className="text-muted-foreground">{s.type} · </span>
                          <code className="break-all font-mono">{s.locator}</code>
                          {s.integrity ? (
                            <>
                              {" — "}
                              <code className="break-all font-mono text-muted-foreground">{s.integrity}</code>
                            </>
                          ) : null}
                        </span>
                      ))}
                    </span>
                  ),
                },
              ]}
            />
          </>
        )}

        <p className="flex items-center gap-1.5 text-xs text-amber-700 dark:text-amber-400">
          <ScrollTextIcon className="size-3.5 shrink-0" />
          {t("modelcard.disclaimer")}
        </p>
      </CardContent>
    </Card>
  );
}

// --- model inventory (TASK-H5) -------------------------------------------------
//
// SR 11-7 style inventory: the tracked ledger's confirmatory:first runs
// reconciled against their frozen run directories — one row per phase
// (freeze row+ts · H6 · differential mean_diff [CI] · null badge), and the
// config-only commits collapsed into a count + one-sentence disclosure.
// Every value is verbatim from model_inventory.json; a missing local
// directory renders the honest "no dir" state, never a guessed value.
// Honest empty state: with no inventory rows the table headers still render.

const HOLD_BADGE =
  "border-emerald-500/40 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400";
const BREAK_BADGE =
  "border-amber-500/40 bg-amber-500/10 text-amber-700 dark:text-amber-400";

function NullBadge({ holds }: { holds: boolean | null }) {
  const { t } = useI18n();
  if (holds === true) {
    return (
      <Badge variant="outline" className={HOLD_BADGE}>
        {t("inventory.verdict.holds")}
      </Badge>
    );
  }
  if (holds === false) {
    return (
      <Badge variant="outline" className={BREAK_BADGE}>
        {t("inventory.verdict.broken")}
      </Badge>
    );
  }
  return <span className="text-xs text-muted-foreground">{t("inventory.verdict.unknown")}</span>;
}

function H6Cell({ value }: { value: boolean | null }) {
  if (value === true) {
    return (
      <Badge variant="outline" className={HOLD_BADGE}>
        PASS
      </Badge>
    );
  }
  return (
    <span className="text-xs text-muted-foreground">{value === false ? "FAIL" : "—"}</span>
  );
}

// --- modeling decision genealogy (TASK-H6) ------------------------------------
//
// Rendered below the inventory listing: every supersession chain the exporter
// derived from the tracked ledger, one block per chain — phase title, kind
// badge, and the linked row row `#46 → #47 → #48`. Explicit chains hang each
// supersede reason (verbatim ledger amendment text) under the row it replaced;
// ledger-sequence chains carry no reason quotes (an inferred arrangement, not
// an explicit supersession claim — the honest distinction lives in the note).
// Emerald chips reuse the section's existing resulted semantics; amber flags
// the inferred kind (caution, not a direction color).

const GENEALOGY_KIND_STYLE: Record<ModelInventoryChain["kind"], string> = {
  "explicit-supersede": "border-sky-500/40 bg-sky-500/10 text-sky-700 dark:text-sky-400",
  "ledger-sequence": "border-amber-500/40 bg-amber-500/10 text-amber-700 dark:text-amber-400",
};
const GENEALOGY_RESULTED_STYLE =
  "border-emerald-500/40 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400";

function ModelInventoryGenealogy() {
  const { t } = useI18n();
  const chains = aionis.modelInventory?.chains ?? [];
  if (chains.length === 0) return null;
  return (
    <div className="space-y-2">
      <p className="flex items-center gap-1.5 text-xs font-medium">
        <GitBranchIcon className="size-3.5" /> {t("inventory.genealogy.title")}
      </p>
      {chains.map((chain) => (
        <div
          key={chain.phase}
          className="space-y-1.5 rounded-md border border-dashed p-3 text-xs"
        >
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-medium">{chain.phase}</span>
            <Badge variant="outline" className={GENEALOGY_KIND_STYLE[chain.kind]}>
              {chain.kind === "explicit-supersede"
                ? t("inventory.genealogy.kind.explicit")
                : t("inventory.genealogy.kind.sequence")}
            </Badge>
          </div>
          <div className="flex flex-wrap items-start gap-x-1.5 gap-y-2">
            {chain.links.map((link, i) => {
              const reason =
                chain.kind === "explicit-supersede"
                  ? (chain.links[i + 1]?.amendment_excerpt ?? null)
                  : null;
              return (
                <span key={link.row} className="flex flex-col items-start gap-1">
                  <span className="flex items-center gap-1.5">
                    {i > 0 ? (
                      <ArrowRightIcon className="size-3 shrink-0 text-muted-foreground" />
                    ) : null}
                    <code
                      title={t("inventory.genealogy.resulted")}
                      className={cn(
                        "rounded border px-1.5 py-0.5 font-mono tabular-nums",
                        link.resulted && GENEALOGY_RESULTED_STYLE
                      )}
                    >
                      #{link.row}
                    </code>
                  </span>
                  {reason ? (
                    <span className="block max-w-[22rem] border-l-2 border-l-muted-foreground/30 pl-2 text-[11px] text-muted-foreground">
                      <span className="block font-medium">
                        {t("inventory.genealogy.reason")}
                      </span>
                      {reason}
                    </span>
                  ) : null}
                </span>
              );
            })}
          </div>
        </div>
      ))}
      <p className="text-xs text-muted-foreground">{t("inventory.genealogy.note")}</p>
    </div>
  );
}

function ModelInventorySection() {
  const { t } = useI18n();
  const inv: ModelInventory | undefined = aionis.modelInventory;
  const runs = inv?.runs ?? [];
  const coCount = inv?.summary?.n_config_only ?? 0;
  const asOfDate = inv?.as_of ? inv.as_of.split("T")[0] : null;

  return (
    <Card className="border-dashed">
      <CardHeader className="border-b">
        <CardTitle className="flex items-center gap-2 text-base">
          <ListIcon className="size-4" /> {t("inventory.title")}
        </CardTitle>
        <CardDescription>{t("inventory.subtitle")}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4 p-4">
        {asOfDate ? (
          <p className="text-xs text-muted-foreground">
            {t("inventory.asof")}: <span className="tabular-nums">{asOfDate}</span>
          </p>
        ) : null}
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-[13px]">
            <thead>
              <tr className="border-b text-left text-xs text-muted-foreground">
                <th className="py-1.5 pr-3 font-medium">{t("inventory.col.phase")}</th>
                <th className="py-1.5 pr-3 font-medium">{t("inventory.col.sig")}</th>
                <th className="py-1.5 pr-3 font-medium">{t("inventory.col.freezeTs")}</th>
                <th className="py-1.5 pr-3 font-medium">{t("inventory.col.h6")}</th>
                <th className="py-1.5 pr-3 font-medium">{t("inventory.col.diff")}</th>
                <th className="py-1.5 pr-3 font-medium">{t("inventory.col.verdict")}</th>
                <th className="py-1.5 font-medium">{t("inventory.col.local")}</th>
              </tr>
            </thead>
            <tbody>
              {runs.length === 0 ? (
                <tr>
                  <td className="py-2 text-muted-foreground" colSpan={7}>
                    {t("inventory.empty")}
                  </td>
                </tr>
              ) : (
                runs.map((r) => {
                  const diff = r.diff;
                  const diffText =
                    diff?.mean_diff != null && diff.ci_lo != null && diff.ci_hi != null
                      ? `${String(diff.mean_diff)} [${String(diff.ci_lo)}, ${String(diff.ci_hi)}]`
                      : null;
                  return (
                    <tr key={r.config_sig} className="border-b align-top last:border-0">
                      <td className="py-1.5 pr-3 font-medium">{r.phase ?? "—"}</td>
                      <td className="py-1.5 pr-3">
                        <code className="font-mono text-xs">{r.config_sig.slice(0, 12)}</code>
                      </td>
                      <td className="py-1.5 pr-3 text-xs tabular-nums">
                        #{r.freeze_row ?? "—"} · {r.freeze_ts ?? "—"}
                      </td>
                      <td className="py-1.5 pr-3">
                        <H6Cell value={r.h6_deterministic} />
                      </td>
                      <td className="py-1.5 pr-3 tabular-nums">
                        {diffText ?? <span className="text-muted-foreground">—</span>}
                      </td>
                      <td className="py-1.5 pr-3">
                        <NullBadge holds={diff?.null_holds ?? null} />
                      </td>
                      <td className="py-1.5">
                        {r.local_dir_present ? (
                          <span className="text-xs">v{r.aionis_version ?? "—"}</span>
                        ) : (
                          <Badge variant="outline" className={BREAK_BADGE}>
                            {t("inventory.local.missing")}
                          </Badge>
                        )}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        <details className="rounded-md border border-dashed p-3 text-xs">
          <summary className="cursor-pointer font-medium">
            {t("inventory.configOnly")}: <span className="tabular-nums">{coCount}</span>
          </summary>
          <p className="mt-1 text-muted-foreground">{t("inventory.configOnlyNote")}</p>
        </details>

        <ModelInventoryGenealogy />

        <p className="flex items-center gap-1.5 text-xs text-amber-700 dark:text-amber-400">
          <ScrollTextIcon className="size-3.5 shrink-0" />
          {t("inventory.disclaimer")}
        </p>
      </CardContent>
    </Card>
  );
}

export function ModelHealthView() {
  const { t } = useI18n();
  const mh = aionis.modelHealth;
  const regions = Object.values(mh.regions ?? {});

  return (
    <div className="flex flex-col gap-4">
      <p className="text-xs font-medium text-primary">{t("modelhealth.role")}</p>
      <header>
        <h1 className="text-2xl font-semibold tracking-[-0.032em]" title={t("modelhealth.termHint")}>{t("modelhealth.title")}</h1>
        <p className="mt-2 text-[13px] text-mute">{t("modelhealth.window")}</p>
      </header>

      {mh.status !== "ok" || regions.length === 0 ? (
        <Card className="border-amber-500/30 bg-amber-500/5">
          <CardContent className="p-4 text-sm text-muted-foreground">
            {t("modelhealth.awaiting")}
          </CardContent>
        </Card>
      ) : (
        regions.map((r) => (
          <Card key={r.region} className="overflow-hidden py-0">
            <CardHeader className="border-b">
              <CardTitle className="flex items-center justify-between text-base">
                <span className="font-mono uppercase">{r.region}</span>
                <Badge variant="outline" className={cn(REGIME_STYLE[r.regime] ?? "")}>
                  {t(REGIME_LABEL[r.regime] ?? "modelhealth.regime.moderate")}
                </Badge>
              </CardTitle>
              <CardDescription>
                {t("modelhealth.regimehint")} · <span title={t("modelhealth.psiTermHint")}>PSI = {r.psi.toFixed(3)}</span> · <span title={t("modelhealth.nRecentHint")}>n<sub>recent</sub> {r.n_recent}</span> / <span title={t("modelhealth.nHistoryHint")}>n<sub>hist</sub> {r.n_history}</span>
              </CardDescription>
            </CardHeader>
            <CardContent className="grid grid-cols-2 gap-3 p-4 md:grid-cols-4">
              <Stat label={t("modelhealth.psi")} value={r.psi.toFixed(3)} hint={t("modelhealth.psiTermHint")} />
              <Stat label={t("modelhealth.icrecent")} value={r.ic_recent.toFixed(3)} hint={t("modelhealth.icTermHint")} />
              <Stat label={t("modelhealth.icfull")} value={r.ic_full.toFixed(3)} hint={t("modelhealth.icTermHint")} />
              <Stat
                label={t("modelhealth.baserate")}
                value={`${r.base_rate_full.toFixed(2)}→${r.base_rate_recent.toFixed(2)}`}
                hint={t("modelhealth.baseRateTermHint")}
              />
            </CardContent>
          </Card>
        ))
      )}

      <ModelCardSection />

      <ModelInventorySection />

      <Card className="border-dashed">
        <CardHeader className="border-b">
          <CardTitle className="flex items-center gap-2 text-base">
            <ShieldCheckIcon className="size-4" /> {t("modelhealth.howto")}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 p-4">
          <p className="text-xs text-muted-foreground">{mh.methodology}</p>
          <p className="flex items-center gap-1.5 text-xs text-amber-700 dark:text-amber-400">
            <ShieldAlertIcon className="size-3.5 shrink-0" />
            {t("modelhealth.disclaimer")}
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
