"use client";

// useTabHotkeys (round 166): keyboard navigation for the Tabs pages
// (/track, /regime, /confirmation). Digit keys 1-9 jump to the Nth tab;
// "[" / "]" cycle backward/forward. Skips when the user is typing in an
// input/textarea/select/contenteditable (the home search and ⌘K palette
// must keep their keystrokes).

import { useEffect } from "react";

export function useTabHotkeys(
  tabValues: readonly string[],
  activeTab: string,
  onSelect: (tab: string) => void,
) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      const el = e.target as HTMLElement | null;
      if (
        el &&
        (el.tagName === "INPUT" ||
          el.tagName === "TEXTAREA" ||
          el.tagName === "SELECT" ||
          el.isContentEditable)
      ) {
        return;
      }
      const idx = tabValues.indexOf(activeTab);
      if (idx === -1) return;

      if (e.key === "[") {
        e.preventDefault();
        onSelect(tabValues[(idx - 1 + tabValues.length) % tabValues.length]);
        return;
      }
      if (e.key === "]") {
        e.preventDefault();
        onSelect(tabValues[(idx + 1) % tabValues.length]);
        return;
      }
      if (/^[1-9]$/.test(e.key)) {
        const n = Number(e.key) - 1;
        if (n < tabValues.length) {
          e.preventDefault();
          onSelect(tabValues[n]);
        }
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [tabValues, activeTab, onSelect]);
}
