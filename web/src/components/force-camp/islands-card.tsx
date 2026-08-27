"use client";

import { ChevronDownIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import { fmtInt } from "@/lib/format";
import { useI18n } from "@/i18n/provider";
import type {
  LineageEdge,
  LineageEdgeType,
  LineageNode,
} from "@/data/aionis/lineage-graph";

// Micro-component ("island") handling for /force-camp — display-lane craft,
// zero contract surface: the exported JSON / Python side is untouched; this
// module only partitions what the view already ships.
//
// Adjudicated threshold (measured on the committed panel): every component
// smaller than 3 nodes is exactly a "2 entities + one w=1 edge" pair, and the
// frozen full-graph FR layout flings all 23 such pairs onto the canvas
// margins (median 503 px from center; 103/146 nodes hugging the border).
// Excluding them re-runs nothing on the research lane, keeps 99.3% of total
// edge weight on-canvas, and cuts near-touching dot pairs ~64%. Components
// here are computed over the FULL edge list (filter toggles hide elements,
// they never change composition).
export const ISLAND_MIN_NODES = 3;

export type IslandGroup = {
  /** Member nodes, original payload order (stable). */
  nodes: LineageNode[];
  /** Edges fully inside this component (>= size-1 for connected comps). */
  edges: LineageEdge[];
};

export type IslandPartition = {
  /** Components kept on the SVG canvas (size >= ISLAND_MIN_NODES). */
  canvasIds: ReadonlySet<string>;
  /** Sub-graph whose components all clear the threshold — the frozen layout
   * and the canvas render consume ONLY these, deterministically. */
  canvasNodes: LineageNode[];
  canvasEdges: LineageEdge[];
  /** Excluded micro-components, deterministic order: heavier first, then by
   * first member id, so the summary card never reshuffles across loads. */
  islands: IslandGroup[];
};

/** Union-find partition of the FULL graph into kept / island sides. */
export function partitionIslands(
  nodes: ReadonlyArray<LineageNode>,
  edges: ReadonlyArray<LineageEdge>,
): IslandPartition {
  const parent = new Map(nodes.map((n) => [n.id, n.id]));
  const find = (x: string): string => {
    let root = x;
    while (parent.get(root) !== root) root = parent.get(root)!;
    while (parent.get(x) !== root) {
      const next = parent.get(x)!;
      parent.set(x, root);
      x = next;
    }
    return root;
  };
  for (const e of edges) {
    const ra = find(e.a);
    const rb = find(e.b);
    if (ra !== rb) parent.set(ra, rb);
  }
  const members = new Map<string, string[]>();
  for (const n of nodes) {
    const r = find(n.id);
    const m = members.get(r);
    if (m) m.push(n.id);
    else members.set(r, [n.id]);
  }
  const idsByRoot = [...members.values()];
  const canvasIds = new Set<string>();
  for (const ids of idsByRoot) {
    if (ids.length >= ISLAND_MIN_NODES) for (const id of ids) canvasIds.add(id);
  }
  const byId = new Map(nodes.map((n) => [n.id, n]));
  const canvasEdges = edges.filter(
    (e) => canvasIds.has(e.a) && canvasIds.has(e.b),
  );
  // Deterministic island order: total internal weight desc, then first
  // member id lexicographic — never reshuffles across loads.
  const roots = idsByRoot
    .filter((ids) => ids.length < ISLAND_MIN_NODES)
    .map((ids) => ({ head: ids[0], ids }));
  roots.sort((a, b) => weightOf(new Set(b.ids)) - weightOf(new Set(a.ids)));
  return {
    canvasIds,
    canvasNodes: nodes.filter((n) => canvasIds.has(n.id)),
    canvasEdges,
    islands: roots.map(({ ids }) => {
      const idset = new Set(ids);
      return {
        nodes: ids.map((id) => byId.get(id)).filter((n) => !!n) as LineageNode[],
        edges: edges.filter((e) => idset.has(e.a) && idset.has(e.b)),
      };
    }),
  };

  function weightOf(idset: ReadonlySet<string>): number {
    let w = 0;
    for (const e of edges) if (idset.has(e.a) && idset.has(e.b)) w += e.w;
    return w;
  }
}

const NODE_DOT: Record<LineageNode["type"], string> = {
  institution: "bg-brand",
  person: "bg-ink",
  staker: "bg-sub",
};

/**
 * Collapsible honest-accounting card below the canvas: each excluded
 * micro-component lists member chips (+ shared-edge weights) and chip clicks
 * reuse the existing node drawer. Nothing here invents data — members and
 * weights come verbatim from the committed panel.
 */
export function IslandsCard({
  islands,
  drawerId,
  onSelect,
}: {
  islands: ReadonlyArray<IslandGroup>;
  drawerId: string | null;
  onSelect: (id: string) => void;
}) {
  const { t } = useI18n();
  if (!islands.length) return null;
  const entityCount = islands.reduce((s, g) => s + g.nodes.length, 0);
  return (
    <section className="overflow-hidden rounded-xl border border-line bg-card">
      <details className="group/islands">
        <summary className="flex cursor-pointer list-none select-none items-center justify-between gap-3 bg-soft px-5 py-2 [&::-webkit-details-marker]:hidden">
          <h2 className="text-[13px] font-semibold">
            {t("forcecamp.islands.title")}
          </h2>
          <span className="flex shrink-0 items-center gap-2 font-mono text-[11px] tabular-nums text-mute">
            {fmtInt(islands.length)} · {fmtInt(entityCount)}
            <ChevronDownIcon
              className="size-4 transition-transform group-open/islands:rotate-180 motion-reduce:transition-none"
              aria-hidden
            />
          </span>
        </summary>
        <p className="border-b border-line2 px-5 py-2 text-[12px] leading-relaxed text-sub">
          {t("forcecamp.islands.hint")
            .replace("{n}", fmtInt(islands.length))
            .replace("{m}", fmtInt(entityCount))}
        </p>
        <div className="max-h-80 divide-y divide-line2 overflow-y-auto">
          {islands.map((g, gi) => {
            const weights = g.edges
              .slice()
              .sort((a, b) => b.w - a.w)
              .map((e) => ({ kind: e.type as LineageEdgeType, w: e.w }));
            return (
              <div
                key={g.nodes[0]?.id ?? gi}
                className="flex flex-wrap items-center gap-x-3 gap-y-1.5 px-5 py-2"
              >
                <div className="flex min-w-0 flex-wrap items-center gap-1.5">
                  {g.nodes.map((n) => (
                    <button
                      key={n.id}
                      type="button"
                      aria-pressed={drawerId === n.id}
                      onClick={() => onSelect(n.id)}
                      className={cn(
                        "inline-flex max-w-full items-center gap-1.5 truncate rounded-full border px-2 py-0.5 text-xs transition-colors motion-reduce:transition-none",
                        drawerId === n.id
                          ? "border-brand bg-brand-tint text-brand"
                          : "border-line bg-card text-sub hover:border-faint hover:text-ink",
                      )}
                    >
                      <span
                        className={cn(
                          "inline-block size-2 shrink-0 rounded-full",
                          NODE_DOT[n.type],
                        )}
                        aria-hidden
                      />
                      <span className="truncate">{n.label}</span>
                    </button>
                  ))}
                </div>
                <span className="ml-auto shrink-0 font-mono text-[11px] tabular-nums text-mute">
                  {weights
                    .map((x) => `${t(`forcecamp.type.${x.kind}`)} ${x.w}`)
                    .join(" · ") || ""}
                </span>
              </div>
            );
          })}
        </div>
      </details>
    </section>
  );
}
