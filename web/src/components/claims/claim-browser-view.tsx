"use client";

import { useI18n } from "@/i18n/provider";
import { aionis } from "@/data/aionis";
import { CLAIM_STATEMENTS, claimBibtex, type ClaimKey } from "./claim-bibtex";

const allBounds = Object.values(aionis.evidenceMatrix.claims).flatMap((c) =>
  c.ci_lo !== null && c.ci_hi !== null ? [c.ci_lo, c.ci_hi] : [],
);
const AXIS_MIN = Math.min(...allBounds, -0.01);
const AXIS_MAX = Math.max(...allBounds, 0.01);
const pct = (v: number) => ((v - AXIS_MIN) / (AXIS_MAX - AXIS_MIN)) * 100;

export function ClaimBrowserView({ claim }: { claim: ClaimKey }) {
  const { t } = useI18n();
  const c = aionis.evidenceMatrix.claims[claim];
  const doc = aionis.knowledgeShelf.docs.find((d) => d.path === c.prereg_doc);
  const row = aionis.ledgerAudit.entries.find((e) => e.row === c.ledger_row);
  const estimate = c.mean_diff !== undefined ? c.mean_diff : c.combined_ic;
  const p = c.dm_p_mbb ?? c.p_hac;
  const isTrackC = claim === "track_c";

  return (
    <div className="flex flex-col gap-4">
      <p className="text-xs font-medium text-primary">{t("claims.role")}</p>
      <header className="space-y-2">
        <h1 className="text-2xl font-semibold tracking-[-0.032em]">
          {isTrackC ? "Track C" : `Phase ${claim}`} · {t("claims.title.suffix")}
        </h1>
        <p className="max-w-3xl text-sm text-muted-foreground">
          {CLAIM_STATEMENTS[claim]}
        </p>
      </header>

      {/* Verdict banner */}
      <div className="rounded-lg border bg-primary/5 p-4">
        <div className="flex flex-wrap items-baseline gap-x-6 gap-y-1">
          <span className="text-lg font-bold">
            {estimate !== undefined ? estimate.toFixed(4) : "—"}
          </span>
          <span className="text-xs text-muted-foreground tabular-nums">
            95% CI [{c.ci_lo?.toFixed(4)}, {c.ci_hi?.toFixed(4)}]
            {p !== undefined && p !== null ? ` · p ${Number(p).toFixed(3)}` : ""}
            {" · n="}{c.n_months}
          </span>
          <span className="rounded-full border border-primary/60 bg-primary/10 px-2 py-0.5 text-[10px] font-semibold text-primary">
            {t("claims.badge.null")}
          </span>
          {c.zero_llm && (
            <span className="rounded-full border px-2 py-0.5 text-[10px] font-medium text-muted-foreground">
              zero-LLM
            </span>
          )}
        </div>
        {/* shared-zero-line CI bar */}
        <div className="relative mt-3 h-5">
          <div className="absolute inset-y-0 w-px bg-border" style={{ left: `${pct(0)}%` }} />
          <div
            className="absolute top-1/2 h-[6px] -translate-y-1/2 rounded-sm bg-primary/45"
            style={{ left: `${pct(c.ci_lo!)}%`, width: `${pct(c.ci_hi!) - pct(c.ci_lo!)}%` }}
          />
          {estimate !== undefined && (
            <div
              className="absolute top-1/2 size-[10px] -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-primary bg-background"
              style={{ left: `${pct(estimate)}%` }}
            />
          )}
        </div>
      </div>

      {/* Chain summary (proof-page excerpt) */}
      <div className="grid grid-cols-1 gap-2 md:grid-cols-3">
        <div className="rounded-lg border bg-card p-3">
          <p className="text-[10px] font-medium uppercase tracking-wide text-primary">
            ① prereg
          </p>
          <a
            href={doc?.url}
            target="_blank"
            rel="noreferrer"
            className="mt-1 block text-xs font-medium hover:underline"
          >
            {c.prereg_doc}
          </a>
          <p className="mt-0.5 text-[10px] text-muted-foreground">{doc?.date}</p>
        </div>
        <div className="rounded-lg border bg-card p-3">
          <p className="text-[10px] font-medium uppercase tracking-wide text-primary">
            ② ledger #{c.ledger_row}
          </p>
          <p className="mt-1 text-xs font-medium">{row?.ts}</p>
          <p className="mt-0.5 text-[10px] text-muted-foreground">
            {row?.event} · sig {row?.config_sig_short || (c.results_sig ?? "").slice(0, 8)}
          </p>
        </div>
        <div className="rounded-lg border bg-card p-3">
          <p className="text-[10px] font-medium uppercase tracking-wide text-primary">
            ④ verify
          </p>
          <p className="mt-1 text-[10px] leading-relaxed text-muted-foreground">
            {t("claims.verify.hint")}
          </p>
          <code className="mt-1 block text-[10px]">
            uv run python scripts/verify_claim.py {claim}
          </code>
        </div>
      </div>

      {/* Citable BibTeX */}
      <div className="rounded-lg border bg-muted/30 p-4">
        <p className="text-xs font-semibold">{t("claims.cite.title")}</p>
        <pre className="mt-2 overflow-x-auto rounded bg-background p-3 text-[11px] leading-relaxed">
{claimBibtex(claim)}
        </pre>
        <p className="mt-1 text-[10px] text-muted-foreground">{t("claims.cite.note")}</p>
      </div>
    </div>
  );
}
