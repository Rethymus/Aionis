"use client";

import { useI18n } from "@/i18n/provider";
import { CLAIM_KEYS, PROJECT_CITATION, claimBibtex, projectBibtex } from "@/components/claims/claim-bibtex";

export function CiteView() {
  const { t } = useI18n();
  return (
    <div className="flex flex-col gap-4">
      <p className="text-xs font-medium text-primary">{t("cite.role")}</p>
      <header className="space-y-2">
        <h1 className="text-2xl font-semibold tracking-[-0.032em]">
          {t("module.cite.title")}
        </h1>
        <p className="max-w-3xl text-sm text-muted-foreground">{t("cite.intro")}</p>
      </header>

      {/* Project citation */}
      <div className="rounded-lg border bg-muted/30 p-4">
        <p className="text-xs font-semibold">{t("cite.project.title")}</p>
        <p className="mt-1 text-xs text-muted-foreground">
          {PROJECT_CITATION.authors} · v{PROJECT_CITATION.version} ·{" "}
          {PROJECT_CITATION.dateReleased} · {PROJECT_CITATION.license}
          {" · "}
          <a className="underline-offset-2 hover:underline" href={PROJECT_CITATION.repository}>
            {PROJECT_CITATION.repository}
          </a>
          {" · "}
          <a className="underline-offset-2 hover:underline" href="/api-docs">
            {t("cite.project.apidocs")}
          </a>
        </p>
        <pre className="mt-2 overflow-x-auto rounded bg-background p-3 text-[11px] leading-relaxed">
{projectBibtex()}
        </pre>
        <p className="mt-1 text-[10px] text-muted-foreground">
          {t("cite.project.ghbutton")}
        </p>
      </div>

      {/* Per-claim cite-this-null */}
      <div className="rounded-lg border p-4">
        <p className="text-xs font-semibold">{t("cite.claims.title")}</p>
        <div className="mt-2 flex flex-col gap-3">
          {CLAIM_KEYS.map((k) => (
            <details key={k} className="rounded border bg-card">
              <summary className="cursor-pointer px-3 py-2 text-xs font-medium">
                {k === "track_c" ? "Track C" : `Phase ${k}`}
                {" — "}
                <span className="text-muted-foreground">{t("cite.claims.nullbadge")}</span>
              </summary>
              <pre className="mx-3 mb-3 overflow-x-auto rounded bg-background p-3 text-[11px] leading-relaxed">
{claimBibtex(k)}
              </pre>
            </details>
          ))}
        </div>
        <p className="mt-2 text-[10px] text-muted-foreground">{t("cite.claims.note")}</p>
      </div>

      {/* Publications — the honest inverted table */}
      <div className="rounded-lg border p-4">
        <p className="text-xs font-semibold">{t("cite.pubs.title")}</p>
        <table className="mt-2 w-full border-collapse text-xs">
          <thead>
            <tr className="border-b bg-muted/40 text-left text-[10px] text-muted-foreground">
              <th className="px-2 py-1.5 font-medium">{t("cite.pubs.venue")}</th>
              <th className="px-2 py-1.5 font-medium">{t("cite.pubs.status")}</th>
              <th className="px-2 py-1.5 font-medium">{t("cite.pubs.note")}</th>
            </tr>
          </thead>
          <tbody>
            <tr className="border-b last:border-0">
              <td className="px-2 py-1.5">{t("cite.pubs.row1.venue")}</td>
              <td className="px-2 py-1.5">{t("cite.pubs.row1.status")}</td>
              <td className="px-2 py-1.5 text-muted-foreground">{t("cite.pubs.row1.note")}</td>
            </tr>
          </tbody>
        </table>
        <p className="mt-2 text-[10px] text-muted-foreground">{t("cite.pubs.footer")}</p>
      </div>
    </div>
  );
}
