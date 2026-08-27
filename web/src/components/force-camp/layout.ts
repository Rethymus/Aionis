// Frozen deterministic force layout for the force-camp graph — hand-rolled
// Fruchterman-Reingold (no d3/cytoscape, no requestAnimationFrame loop, zero
// new dependencies). Seed-0 mulberry32 PRNG + a FIXED ~300 spring iterations
// mean every load and every SSR/client hydration computes byte-identical
// positions: the H6 determinism spirit carried into display-lane craft.
//
// The view runs this ONCE per graph inside useMemo; toggling filters hides
// elements but never re-runs the simulation, and window resizes only scale
// the SVG viewBox. Pure function in/out — no React imports.

export type LayoutPoint = { id: string; x: number; y: number };

const WIDTH = 1000;
const HEIGHT = 640;
const ITERATIONS = 300;
const MARGIN = 24;

/** mulberry32 — 32-bit PRNG, deterministic, tiny, dependency-free. */
function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a += 0x6d2b79f5;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/**
 * Compute frozen node positions. Node order and edge list are consumed
 * as-given (the panel ships them sorted), so the output is a pure function
 * of the payload.
 */
export function forceCampLayout(
  nodes: ReadonlyArray<{ id: string }>,
  edges: ReadonlyArray<{ a: string; b: string; w: number }>,
): LayoutPoint[] {
  const n = nodes.length;
  if (n === 0) return [];
  const rnd = mulberry32(0);
  const index = new Map(nodes.map((v, i) => [v.id, i] as const));
  const px = new Float64Array(n);
  const py = new Float64Array(n);

  // Deterministic golden-angle spiral with seeded jitter — spreads initials
  // far better than a grid so disconnected stars do not overlap at step 0.
  nodes.forEach((_, i) => {
    const angle = i * 2.399963229728653 + rnd() * 0.9;
    const radius =
      60 + 250 * Math.sqrt((i + 0.5) / n) * (0.72 + 0.56 * rnd());
    px[i] = WIDTH / 2 + radius * Math.cos(angle);
    py[i] = HEIGHT / 2 + radius * Math.sin(angle);
  });

  // FR natural spring length from the canvas area.
  const k = Math.sqrt((WIDTH * HEIGHT) / n) * 0.85;
  const dispX = new Float64Array(n);
  const dispY = new Float64Array(n);
  const cx = WIDTH / 2;
  const cy = HEIGHT / 2;

  // Edge weights are pre-scaled once; attraction uses sqrt(w) so heavy pairs
  // pull harder without collapsing high-degree hubs onto each other.
  const eIdx: Array<[number, number, number]> = [];
  for (const e of edges) {
    const ia = index.get(e.a);
    const ib = index.get(e.b);
    if (ia === undefined || ib === undefined || ia === ib) continue;
    eIdx.push([ia, ib, Math.sqrt(Math.max(1, e.w))]);
  }

  let temp = Math.min(WIDTH, HEIGHT) / 8;
  for (let iter = 0; iter < ITERATIONS; iter++) {
    dispX.fill(0);
    dispY.fill(0);
    // Repulsion (all pairs).
    for (let i = 0; i < n; i++) {
      for (let j = i + 1; j < n; j++) {
        let dx = px[i] - px[j];
        let dy = py[i] - py[j];
        let dist2 = dx * dx + dy * dy;
        if (dist2 < 1e-6) {
          dx = 0.5 + rnd() * 0.01;
          dy = 0.5 + rnd() * 0.01;
          dist2 = dx * dx + dy * dy;
        }
        const dist = Math.sqrt(dist2);
        const force = (k * k) / dist;
        const ux = (dx / dist) * force;
        const uy = (dy / dist) * force;
        dispX[i] += ux;
        dispY[i] += uy;
        dispX[j] -= ux;
        dispY[j] -= uy;
      }
    }
    // Attraction (edges) + mild gravity to keep islands on-canvas.
    for (const [ia, ib, sw] of eIdx) {
      const dx = px[ia] - px[ib];
      const dy = py[ia] - py[ib];
      const dist = Math.max(Math.sqrt(dx * dx + dy * dy), 1e-3);
      const force = (dist * dist) / k;
      const ux = (dx / dist) * force * sw * 0.5;
      const uy = (dy / dist) * force * sw * 0.5;
      dispX[ia] -= ux;
      dispY[ia] -= uy;
      dispX[ib] += ux;
      dispY[ib] += uy;
    }
    for (let i = 0; i < n; i++) {
      dispX[i] += (cx - px[i]) * 0.0025;
      dispY[i] += (cy - py[i]) * 0.0025;
    }
    // Step with temperature cooling; clamp displacement magnitude.
    for (let i = 0; i < n; i++) {
      const dx = dispX[i];
      const dy = dispY[i];
      const mag = Math.max(Math.sqrt(dx * dx + dy * dy), 1e-6);
      const lim = Math.min(mag, temp);
      px[i] += (dx / mag) * lim;
      py[i] += (dy / mag) * lim;
      px[i] = Math.min(Math.max(px[i], MARGIN), WIDTH - MARGIN);
      py[i] = Math.min(Math.max(py[i], MARGIN), HEIGHT - MARGIN);
    }
    temp = Math.max(temp * 0.977, 0.4);
  }

  return nodes.map((v, i) => ({ id: v.id, x: px[i], y: py[i] }));
}
