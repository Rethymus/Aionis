"use client";

import { useI18n } from "@/i18n/provider";
import { aionis } from "@/data/aionis";
import { ThemeCard } from "./themes-view";

/**
 * Renders a filtered subset of the theme cards — the mechanism that dissolves
 * the old "seven themes" silo into the validity-argument chain (paradigm α).
 * Each segment surfaces only the theme data that belongs to its place in the
 * argument:
 *   证据 (picks)        → price / fundamentals / risk / market_structure (selection features = evidence)
 *   独立佐证 (confirm)   → news_sentiment (independent corroboration source)
 *   效度 (track)        → net_cost (cost-adjusted verdict reality)
 * The /themes page is the full argument-chain overview; the data lives in the
 * segments where it logically belongs.
 */
export function ThemeSlice({
  keys,
  showTitle = true,
}: {
  keys: string[];
  showTitle?: boolean;
}) {
  const { t } = useI18n();
  const themes = (aionis.themes.themes ?? []).filter((tm) => keys.includes(tm.key));
  if (themes.length === 0) return null;
  return (
    <div className="space-y-3">
      {showTitle ? (
        <p className="text-xs text-muted-foreground">{t("theme.slice.note")}</p>
      ) : null}
      {/* A single-theme slice (the /confirmation news tab, the /track verdict)
          spans full width — a lone half-width card left the other half of the
          page empty and read as broken. */}
      <div className={themes.length === 1 ? "" : "grid gap-4 md:grid-cols-2"}>
        {themes.map((tm) => (
          <ThemeCard key={tm.key} theme={tm} />
        ))}
      </div>
    </div>
  );
}
