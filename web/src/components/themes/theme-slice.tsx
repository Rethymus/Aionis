"use client";

import { useI18n } from "@/i18n/provider";
import { aionis } from "@/data/aionis";
import { ThemeCard } from "./themes-view";

/**
 * Renders a filtered subset of the theme cards — the mechanism that dissolves
 * the old "seven themes" silo. Each hub surfaces only the theme data that
 * belongs to its role in the research funnel:
 *   定标 (picks)       → price / fundamentals / risk / market_structure (selection factors)
 *   佐证 (confirmation) → news_sentiment (alternative signal)
 *   问责 (track)       → net_cost (cost-adjusted reality)
 * The /themes page itself becomes the funnel overview; the data lives in the
 * hubs where it logically belongs.
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
      <div className="grid gap-4 md:grid-cols-2">
        {themes.map((tm) => (
          <ThemeCard key={tm.key} theme={tm} />
        ))}
      </div>
    </div>
  );
}
