"use client";

// Human-visible subscription affordance for the build-time atom.xml (round
// 181). The href is the canonical deployed URL (not a relative path) so the
// chip works identically from the GitHub Pages site, local preview, and
// copied-out builds — a feed URL is meant to be copied into a reader.
import { useI18n } from "@/i18n/provider";

const FEED_URL = "https://rethymus.github.io/Aionis/atom.xml";

export function FeedChip() {
  const { t } = useI18n();
  return (
    <a
      href={FEED_URL}
      className="inline-flex items-center gap-1 rounded-full border border-border bg-card px-2.5 py-0.5 text-xs text-muted-foreground transition-colors hover:border-primary/40 hover:text-foreground"
      title={FEED_URL}
    >
      <svg
        aria-hidden="true"
        viewBox="0 0 24 24"
        className="h-3 w-3"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      >
        <path d="M4 11a9 9 0 0 1 9 9" />
        <path d="M4 4a16 16 0 0 1 16 16" />
        <circle cx="5" cy="19" r="1" fill="currentColor" stroke="none" />
      </svg>
      {t("news.chip.feed")}
    </a>
  );
}
