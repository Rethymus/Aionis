"use client";

// "What changed last night" strip (round 213) — the 2026 dashboard trend of
// systems proactively surfacing change, applied to this terminal's honesty
// mission: the nightly lane's committed per-panel transitions, rendered as a
// one-glance band on the home page. Data: panel_changes.json (META panel,
// captured by the export wrapper — content fingerprints excluding
// snapshot_ts, so changed=true means real content moved).
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useI18n } from "@/i18n/provider";
import { aionis } from "@/data/aionis";
import { ArrowUpRightIcon } from "lucide-react";

export function PanelChangesStrip() {
  const { t } = useI18n();
  const pc = aionis.panelChanges;
  if (pc.status !== "ok" || pc.n_tracked === 0) return null;

  const changed = pc.changes.filter((c) => c.changed);
  const date = pc.as_of?.slice(0, 10) ?? "—";

  return (
    <Card className="py-0">
      <CardHeader className="border-b">
        <CardTitle className="flex flex-wrap items-center gap-2 text-sm">
          <ArrowUpRightIcon className="size-4 text-primary" />
          {t("overview.changes.title")}
          <span className="font-mono text-xs font-normal text-muted-foreground tabular-nums">
            {t("overview.changes.count")
              .replace("{changed}", String(changed.length))
              .replace("{tracked}", String(pc.n_tracked))}{" "}
            · {date}
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        <div className="flex flex-wrap gap-1.5 p-4">
          {changed.slice(0, 18).map((c) => {
            const key = c.file.replace(/\.json$/, "");
            const advanced = c.as_of_after && c.as_of_after !== c.as_of_before;
            return (
              <span
                key={c.file}
                title={`${c.as_of_before ?? "—"} → ${c.as_of_after ?? "—"} · ${c.sha_before ?? "∅"}→${c.sha_after}`}
                className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 font-mono text-[11px] ${
                  advanced
                    ? "border-primary/30 bg-primary/10 text-primary"
                    : "border-border bg-card text-muted-foreground"
                }`}
              >
                {key}
                {advanced ? (
                  <span className="font-semibold">
                    {String(c.as_of_after).slice(0, 10)}
                  </span>
                ) : null}
              </span>
            );
          })}
          {changed.length > 18 ? (
            <span className="self-center px-1 text-xs text-muted-foreground">
              +{changed.length - 18}
            </span>
          ) : null}
          {changed.length === 0 ? (
            <span className="text-xs text-muted-foreground">
              {t("overview.changes.none")}
            </span>
          ) : null}
        </div>
      </CardContent>
    </Card>
  );
}
