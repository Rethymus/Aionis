import type { ReactNode } from "react";

// Server-safe primitives for the research-atlas editorial diagrams (zero
// client JS — layout is computed at build time; see
// reports/design/2026-08-28-editorial-diagram-language.md).

// Linear scale with a clamped, invertible mapping — the only math these
// deterministic SVGs need.
export function scaleLinear(
  domain: readonly [number, number],
  range: readonly [number, number],
): (v: number) => number {
  const [d0, d1] = domain;
  const [r0, r1] = range;
  const span = d1 - d0;
  return (v: number) => {
    const t = span === 0 ? 0 : (v - d0) / span;
    return r0 + Math.max(0, Math.min(1, t)) * (r1 - r0);
  };
}

// "Nice" axis ticks: round 1/2/5-step ticks covering [min, max].
export function niceTicks(min: number, max: number, count = 5): number[] {
  if (!Number.isFinite(min) || !Number.isFinite(max) || min === max) {
    return [min];
  }
  const span = max - min;
  const rawStep = span / Math.max(1, count - 1);
  const mag = 10 ** Math.floor(Math.log10(rawStep));
  const norm = rawStep / mag;
  const step = (norm >= 5 ? 5 : norm >= 2 ? 2 : norm >= 1 ? 1 : 0.5) * mag;
  const start = Math.ceil(min / step) * step;
  const ticks: number[] = [];
  for (let v = start; v <= max + step * 1e-6; v += step) {
    ticks.push(Number(v.toFixed(10)));
  }
  return ticks;
}

// Accessible figure wrapper: visible caption, screen-reader description, and
// a slot for the always-rendered data table fallback (force-camp precedent:
// column headers render even on an honest empty panel).
export function DiagramFigure({
  title,
  desc,
  caption,
  children,
  table,
}: {
  title: string;
  desc: string;
  caption?: string;
  children: ReactNode;
  table?: ReactNode;
}) {
  return (
    <figure className="space-y-3">
      <figcaption>
        <p className="text-sm font-semibold">{title}</p>
        <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{desc}</p>
      </figcaption>
      <div role="img" aria-label={`${title} — ${desc}`}>
        {children}
      </div>
      {table}
      {caption ? (
        <p className="text-xs text-muted-foreground">{caption}</p>
      ) : null}
    </figure>
  );
}
