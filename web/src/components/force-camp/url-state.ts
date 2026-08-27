// URL query-string sync for the /force-camp filter pills — pure display-lane,
// zero research-lane surface. Refresh/share keeps filter state; first load
// reads it back.
//
// Why NOT next/link's useSearchParams: this repo's static export has no
// useSearchParams precedent anywhere — every existing URL-state surface
// (picks/regime/discipline/track/confirmation pages) reads window.location
// client-side against a deterministic SSR-first-render default, exactly like
// the i18n provider defers its localStorage read until after mount. This
// module follows that in-repo convention instead of introducing a new
// Suspense-boundary pattern on one route:
//   read  — parseForceCampQuery(window.location.search), applied once after
//           mount via setState-in-effect (prerendered HTML stays "all on"
//           and byte-deterministic, then the URL wins).
//   write — history.replaceState only: no navigation, no scroll jump, no
//           history entries created, so back/forward need no interception.
//
// Wire schema (?t=co_hold,co_board&w=2):
//   t — comma-separated ENABLED edge types from the canonical order
//       co_hold,co_board,co_target. Absent  -> all three enabled (default).
//       Present tokens are validated; unknown tokens are ignored; an empty/
//       all-invalid value means ALL disabled (the canvas honestly empties,
//       tables stay). Serialization omits t entirely when all are enabled.
//   w — min shared-item weight, integer 1..5. Absent/invalid/out-of-range
//       -> 1 (default); serialized only when != 1.
// Anything else in the query string is preserved untouched on read; writes
// replace the whole query with our canonical minimal form (this route has no
// other query consumers).

import type { LineageEdgeType } from "@/data/aionis/lineage-graph";

export const FORCE_CAMP_EDGE_TYPES: readonly LineageEdgeType[] = [
  "co_hold",
  "co_board",
  "co_target",
];

export type ForceCampFilters = {
  on: Record<LineageEdgeType, boolean>;
  minW: number;
};

const MIN_W_DEFAULT = 1;
const MIN_W_MAX = 5;

const ALL_ON: Record<LineageEdgeType, boolean> = {
  co_hold: true,
  co_board: true,
  co_target: true,
};

export function parseForceCampQuery(search: string): ForceCampFilters {
  const params = new URLSearchParams(search);
  const on: Record<LineageEdgeType, boolean> = { ...ALL_ON };
  const rawT = params.get("t");
  if (rawT !== null) {
    for (const kind of FORCE_CAMP_EDGE_TYPES) on[kind] = false;
    for (const token of rawT.split(",")) {
      const kind = token.trim();
      if ((FORCE_CAMP_EDGE_TYPES as readonly string[]).includes(kind)) {
        on[kind as LineageEdgeType] = true;
      }
    }
  }
  let minW = MIN_W_DEFAULT;
  const rawW = params.get("w");
  if (rawW !== null) {
    const n = Number(rawW);
    if (Number.isInteger(n) && n >= 1 && n <= MIN_W_MAX) minW = n;
  }
  return { on, minW };
}

export function serializeForceCampQuery(f: ForceCampFilters): string {
  const params = new URLSearchParams();
  if (!f.on.co_hold || !f.on.co_board || !f.on.co_target) {
    params.set(
      "t",
      FORCE_CAMP_EDGE_TYPES.filter((kind) => f.on[kind]).join(","),
    );
  }
  if (f.minW !== MIN_W_DEFAULT) params.set("w", String(f.minW));
  // Bare commas are legal query sub-delims — keep ?t=a,b human-readable
  // instead of %2C-escaped (parse side accepts either).
  return params.toString().split("%2C").join(",");
}
