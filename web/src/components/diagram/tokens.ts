// Editorial diagram design tokens (see reports/design/2026-08-28-editorial-
// diagram-language.md). Research-atlas SVGs bind to the app's CSS variables
// (inline SVG inherits them), so light/dark themes stay in sync with zero JS
// and zero client-side theme listeners.
//
// Direction semantics are deliberately NOT used here: these diagrams encode
// categories and magnitudes centered on zero, not price direction, so the
// --up/--down colorconv contract does not apply. The diverging scale is a
// colorblind-safe blue↔orange pair (also the editorial default accent), fixed
// across both themes and tuned to stay readable on --card surfaces in light
// and dark (WCAG-checked pairs from the 2026-08-16 contrast audit).

export const diagram = {
  ink: "var(--foreground)",
  muted: "var(--muted-foreground)",
  border: "var(--border)",
  card: "var(--card)",
  mutedBg: "var(--muted)",
  primary: "var(--primary)",
} as const;

// Diverging scale centered at zero for cross-sectional rank-IC style values.
// Index 0 = strongest negative, 4 = ~zero, 8 = strongest positive. Fixed
// oklch values: theme-independent by design (the card surface behind them is
// the only thing that changes), colorblind-safe, no red/green direction
// semantics.
export const divergingScale: readonly string[] = [
  "oklch(0.42 0.15 264)", // strong negative
  "oklch(0.52 0.13 264)",
  "oklch(0.66 0.09 264)",
  "oklch(0.8 0.04 264)",
  "oklch(0.72 0.02 75)", // ~zero (warm gray-orange)
  "oklch(0.78 0.09 60)",
  "oklch(0.72 0.14 48)",
  "oklch(0.64 0.17 40)",
  "oklch(0.55 0.19 36)", // strong positive
];

// Map a value onto the diverging scale. `symMax` is the |value| that maps to
// the strongest bucket (values are clamped); v >= 0 uses the warm half.
export function divergingIndex(v: number, symMax: number): number {
  if (symMax <= 0) return 4;
  const t = Math.max(-1, Math.min(1, v / symMax));
  // t in [-1,1] → bucket 0..8 with 4 at zero.
  return Math.round(((t + 1) / 2) * 8);
}

export function divergingColor(v: number, symMax: number): string {
  return divergingScale[divergingIndex(v, symMax)];
}
