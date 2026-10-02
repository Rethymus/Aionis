// Shared pure helpers for the /atlas claims section (round 119 surgical
// split): kept outside the dynamically-imported charts module so the SSR
// wrappers compute captions/tables without pulling SVG code into the
// initial bundle. Verbatim from the pre-split atlas-claims.tsx.
export const isNum = (v: number | null | undefined): v is number =>
  typeof v === "number" && Number.isFinite(v);

export const fmt = (v: number | null | undefined, dp: number): string =>
  isNum(v) ? v.toFixed(dp) : "—";

export function tf(template: string, params: Record<string, string>): string {
  let out = template;
  for (const [k, v] of Object.entries(params)) {
    out = out.split(`{${k}}`).join(v);
  }
  return out;
}
