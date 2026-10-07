"use client";

import { useI18n } from "@/i18n/provider";
import { aionis } from "@/data/aionis";
import { cn } from "@/lib/utils";

// The chain every claim carries: prereg doc (committed) → config_committed
// ledger row (append-only, BEFORE any OOS metric) → frozen results dir
// (runs/results/<sig>) → verdict. Rendered from committed panels only.
const CLAIM_ORDER = ["B", "C", "D", "E1", "track_c"] as const;

type ChainNode = {
  label: string;
  main: string;
  sub: string;
  href?: string;
};

function chainFor(claimKey: string): { title: string; nodes: ChainNode[] } {
  const c = aionis.evidenceMatrix.claims[claimKey];
  const doc = aionis.knowledgeShelf.docs.find((d) => d.path === c.prereg_doc);
  const row = aionis.ledgerAudit.entries.find((e) => e.row === c.ledger_row);
  const estimate =
    c.mean_diff !== undefined ? c.mean_diff : c.combined_ic;
  const ci =
    c.ci_lo !== null && c.ci_hi !== null
      ? `[${c.ci_lo.toFixed(4)}, ${c.ci_hi.toFixed(4)}]`
      : "—";
  return {
    title: claimKey === "track_c" ? "Track C（时序 confirmatory）" : `Phase ${claimKey}`,
    nodes: [
      {
        label: "① prereg",
        main: doc ? doc.title.split("—")[0].trim() : c.prereg_doc,
        sub: doc ? `${doc.path} · ${doc.date}` : c.prereg_doc,
        href: doc?.url,
      },
      {
        label: "② ledger",
        main: `#${c.ledger_row} · ${row?.ts ?? ""}`,
        sub: `${row?.event ?? ""} · sig ${row?.config_sig_short || (c.results_sig ?? "").slice(0, 8)}`,
      },
      {
        label: "③ frozen",
        main: c.results_sig ? c.results_sig.slice(0, 16) + "…" : "walk-forward",
        sub: c.results_sig ? "runs/results/<sig>/ · bit-identical reruns" : "71-month walk-forward OOS",
      },
      {
        label: "④ verdict",
        main: estimate !== undefined ? estimate.toFixed(4) : "—",
        sub: `95% CI ${ci}`,
      },
    ],
  };
}

export function ProofView() {
  const { t } = useI18n();

  return (
    <div className="flex flex-col gap-4">
      <p className="text-xs font-medium text-primary">{t("proof.role")}</p>
      <header className="space-y-2">
        <h1 className="text-2xl font-semibold tracking-[-0.032em]">
          {t("module.proof.title")}
        </h1>
        <p className="max-w-3xl text-sm text-muted-foreground">{t("proof.intro")}</p>
      </header>

      {CLAIM_ORDER.map((key) => {
        const chain = chainFor(key);
        return (
          <section key={key} className="space-y-2">
            <h2 className="text-sm font-semibold">{chain.title}</h2>
            <div className="grid grid-cols-1 gap-2 md:grid-cols-4">
              {chain.nodes.map((n, i) => (
                <div key={n.label} className="relative">
                  <div className="h-full rounded-lg border bg-card p-3">
                    <p className="text-[10px] font-medium uppercase tracking-wide text-primary">
                      {n.label}
                    </p>
                    {n.href ? (
                      <a
                        href={n.href}
                        target="_blank"
                        rel="noreferrer"
                        className="mt-1 block truncate text-xs font-medium underline-offset-2 hover:underline"
                        title={n.sub}
                      >
                        {n.main}
                      </a>
                    ) : (
                      <p className="mt-1 truncate text-xs font-medium" title={n.main}>
                        {n.main}
                      </p>
                    )}
                    <p className="mt-0.5 break-words text-[10px] leading-tight text-muted-foreground" title={n.sub}>
                      {n.sub}
                    </p>
                  </div>
                  {i < chain.nodes.length - 1 && (
                    <span
                      aria-hidden
                      className="absolute -right-[9px] top-1/2 hidden -translate-y-1/2 text-muted-foreground md:block"
                    >
                      →
                    </span>
                  )}
                </div>
              ))}
            </div>
          </section>
        );
      })}

      {/* Self-verification */}
      <div className="rounded-lg border bg-muted/30 p-4">
        <p className="text-xs font-semibold">{t("proof.verify.title")}</p>
        <pre className="mt-2 overflow-x-auto rounded bg-background p-3 text-[11px] leading-relaxed">
{`# ① prereg doc predates the run — check its commit history
git log --follow --format='%ci %h' -- docs/phase-b-preregistration.md | tail -1

# ② the append-only ledger row (Phase B example, row #28)
sed -n '28p' runs/ledger.jsonl | python -m json.tool

# ③ the frozen config sha in that row must equal the results dir name
ls runs/results/ | grep 17245a75

# ④ evidence artifact hashes are pinned in the committed matrix
python -c "import json;print(json.load(open('web/src/data/aionis/evidence_matrix.json'))['artifacts'][0])"`}
        </pre>
        <p className="mt-2 text-[11px] text-muted-foreground">{t("proof.verify.note")}</p>
        <p className="mt-1 text-[11px] text-muted-foreground">
          one command: <code className="rounded bg-background px-1">uv run python scripts/verify_claim.py</code>
        </p>
      </div>

      <p className="text-xs text-muted-foreground">{t("proof.footer")}</p>
    </div>
  );
}
