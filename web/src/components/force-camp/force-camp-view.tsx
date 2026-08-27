"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { XIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import { fmtDateShort, fmtEmpty, fmtInt } from "@/lib/format";
import { useI18n } from "@/i18n/provider";
import { ProvenanceBadge } from "@/components/provenance-badge";
import {
  lineageGraph,
  type LineageEdge,
  type LineageEdgeType,
  type LineageNode,
} from "@/data/aionis/lineage-graph";
import { stockUniverse } from "@/data/aionis/stock-universe";
import { forceCampLayout } from "./layout";

// /force-camp — 势力阵营 lineage graph over the COMMITTED panels (display
// lane, zero fetches): KPI band → edge-type pills + min-weight stepper →
// frozen deterministic SVG force canvas → four permanent tables (one per
// edge type + cross-lane bridges) → methodology footnote. The tables ARE the
// accessibility/reduced-motion/mobile fallback: column headers always render,
// even on an honest empty panel (P9).
//
// Red-line wording discipline: every overlap shown here is a coincidence of
// separately filed disclosures — never a coordination or consortium claim.

// Stock-page deep links resolve ONLY for universe members (client-side gate;
// bridges additionally carry the export-time stock_routable flag).
const STOCK_PAGE_TICKERS_SET: ReadonlySet<string> = new Set(
  stockUniverse.stocks.map((s) => s.ticker),
);

const EDGE_TYPES: LineageEdgeType[] = ["co_hold", "co_board", "co_target"];

// Fixed radius tier per node type — no value-driven scaling to second-guess.
const NODE_R: Record<LineageNode["type"], number> = {
  institution: 8,
  person: 5.5,
  staker: 4,
};

// Non-directional encodings (no --up/--down abuse): edge TYPES ride dash
// patterns so the graph stays readable without hue dependence.
const EDGE_STROKE: Record<LineageEdgeType, string> = {
  co_hold: "",
  co_board: "6 4",
  co_target: "2 4",
};

function StockTk({ tk }: { tk: string | null }) {
  if (!tk) return <span className="text-mute">{fmtEmpty(tk)}</span>;
  if (STOCK_PAGE_TICKERS_SET.has(tk)) {
    return (
      <Link
        href={`/stock/${tk}`}
        className="font-semibold text-brand hover:text-brand-hover"
      >
        {tk}
      </Link>
    );
  }
  return <b className="font-semibold text-ink">{tk}</b>;
}

function SharedLine({ e }: { e: LineageEdge }) {
  const parts = e.shared.map((it, i) => {
    const sep = i > 0 ? <span className="text-faint"> · </span> : null;
    if ("k" in it) {
      return (
        <span key={`${e.a}-${e.b}-${it.k}`}>
          {sep}
          <StockTk tk={it.tk} />
          <span className="text-sub"> {it.issuer}</span>
        </span>
      );
    }
    if ("company" in it) {
      return (
        <span key={`${e.a}-${e.b}-${it.company}`}>
          {sep}
          {it.company}
          {it.tk ? (
            <>
              {" "}
              <StockTk tk={it.tk} />
            </>
          ) : null}
        </span>
      );
    }
    return (
      <span key={`${e.a}-${e.b}-${it.target}`}>
        {sep}
        <StockTk tk={it.tk} />
        <span className="text-sub">
          {" "}
          {it.target}
          {` (${it.forms})`}
        </span>
      </span>
    );
  });
  const hidden = e.w - e.shared.length;
  return (
    <span className="truncate">
      {parts}
      {hidden > 0 ? (
        <span className="text-mute"> +{fmtInt(hidden)}</span>
      ) : null}
    </span>
  );
}

export function ForceCampView() {
  const { t } = useI18n();
  const [on, setOn] = useState<Record<LineageEdgeType, boolean>>({
    co_hold: true,
    co_board: true,
    co_target: true,
  });
  const [minW, setMinW] = useState(1);
  const [drawerId, setDrawerId] = useState<string | null>(null);

  const g = lineageGraph;

  // Frozen layout: computed once over the FULL graph (filters hide elements,
  // they never re-run the simulation).
  const layout = useMemo(() => {
    if (g.status !== "ok" || !g.nodes.length) return [];
    return forceCampLayout(g.nodes, g.edges);
  }, [g.status, g.nodes, g.edges]);
  const posById = useMemo(
    () => new Map(layout.map((p) => [p.id, p])),
    [layout],
  );

  const counts = useMemo(() => {
    const c: Record<LineageEdgeType, number> = {
      co_hold: 0,
      co_board: 0,
      co_target: 0,
    };
    for (const e of g.edges) c[e.type] += 1;
    return c;
  }, [g.edges]);

  const nInstitutions = useMemo(
    () => g.nodes.filter((n) => n.type === "institution").length,
    [g.nodes],
  );

  const visible = useMemo(() => {
    let min = Infinity;
    let max = -Infinity;
    const edges = g.edges.filter((e) => on[e.type] && e.w >= minW);
    const ids = new Set<string>();
    for (const e of edges) {
      ids.add(e.a);
      ids.add(e.b);
      if (e.w < min) min = e.w;
      if (e.w > max) max = e.w;
    }
    const span = max > min ? max - min : 1;
    const width = new Map(
      edges.map((e) => [e, 1 + (3 * (e.w - min)) / span] as const),
    );
    return { edges, ids, width };
  }, [g.edges, on, minW]);

  const byId = useMemo(
    () => new Map(g.nodes.map((n) => [n.id, n])),
    [g.nodes],
  );

  // Adjacent items per node (whole-graph) power the drawer detail lists.
  const adjacency = useMemo(() => {
    const m = new Map<string, LineageEdge[]>();
    for (const e of g.edges) {
      (m.get(e.a) ?? m.set(e.a, []).get(e.a))!.push(e);
      (m.get(e.b) ?? m.set(e.b, []).get(e.b))!.push(e);
    }
    return m;
  }, [g.edges]);

  const byType = useMemo(() => {
    const m: Record<LineageEdgeType, LineageEdge[]> = {
      co_hold: [],
      co_board: [],
      co_target: [],
    };
    for (const e of [...g.edges].sort((a, b) => b.w - a.w)) m[e.type].push(e);
    return m;
  }, [g.edges]);

  const ready = g.status === "ok" && g.nodes.length > 0 && layout.length > 0;
  const drawer = drawerId ? byId.get(drawerId) ?? null : null;
  const seatItems = drawer
    ? (adjacency.get(drawer.id) ?? [])
        .flatMap((e) => e.shared.slice(0, 2))
        .slice(0, 5)
    : [];

  const laneLabel = (lane: string) =>
    lane === "13f"
      ? "13F"
      : lane === "def14a"
        ? "DEF 14A"
        : "13D/G";

  return (
    <div className="flex flex-col gap-4">
      {!ready ? (
        <div className="rounded-xl border border-line bg-card px-5 py-10 text-center text-[13px] text-mute">
          {t("forcecamp.empty")}
        </div>
      ) : (
        <>
          {/* KPI band */}
          <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
            {(
              [
                ["forcecamp.kpi.nodes", fmtInt(g.n_nodes)],
                ["forcecamp.kpi.edges", fmtInt(g.n_edges)],
                ["forcecamp.kpi.components", fmtInt(g.components.n)],
                ["forcecamp.kpi.holders", fmtInt(nInstitutions)],
              ] as const
            ).map(([key, v]) => (
              <div key={key} className="rounded-xl border border-line bg-card px-4 py-3">
                <p className="text-[11px] font-medium text-mute">{t(key)}</p>
                <p className="mt-1 font-mono text-xl font-semibold tabular-nums">{v}</p>
              </div>
            ))}
          </div>

          {/* Filter pills + min-weight stepper */}
          <div className="flex flex-wrap items-center gap-2">
            {EDGE_TYPES.filter((kind) => counts[kind] > 0).map((kind) => (
              <button
                key={kind}
                type="button"
                aria-pressed={on[kind]}
                onClick={() => setOn((s) => ({ ...s, [kind]: !s[kind] }))}
                className={cn(
                  "rounded-full border px-3 py-1 font-mono text-xs font-semibold transition-colors motion-reduce:transition-none",
                  on[kind]
                    ? "border-brand bg-brand-tint text-brand"
                    : "border-line bg-card text-sub hover:border-faint hover:text-ink",
                )}
              >
                {t(`forcecamp.type.${kind}`)} ({counts[kind]})
              </button>
            ))}
            <div className="ml-auto flex items-center gap-1 rounded-full border border-line bg-card px-2 py-1">
              <span className="pl-1 pr-1 text-[11px] text-mute">
                {t("forcecamp.min_weight")}
              </span>
              {[1, 2, 3, 4, 5].map((v) => (
                <button
                  key={v}
                  type="button"
                  aria-pressed={minW === v}
                  onClick={() => setMinW(v)}
                  className={cn(
                    "size-6 rounded-full font-mono text-[11px] font-semibold",
                    minW === v ? "bg-soft text-ink" : "text-mute hover:text-ink",
                  )}
                >
                  {v}
                </button>
              ))}
            </div>
          </div>

          {/* Frozen-layout SVG canvas */}
          <div className="overflow-hidden rounded-xl border border-line bg-card p-2">
            <svg
              viewBox="0 0 1000 640"
              className="h-auto w-full"
              role="img"
              aria-label={`${t("nav.forcecamp")} · ${fmtInt(visible.edges.length)} ${t("forcecamp.kpi.edges")}`}
            >
              <g>
                {visible.edges.map((e) => {
                  const pa = posById.get(e.a);
                  const pb = posById.get(e.b);
                  if (!pa || !pb) return null;
                  const na = byId.get(e.a);
                  const nb = byId.get(e.b);
                  return (
                    <line
                      key={`${e.type}-${e.a}-${e.b}`}
                      x1={pa.x}
                      y1={pa.y}
                      x2={pb.x}
                      y2={pb.y}
                      strokeWidth={visible.width.get(e) ?? 1}
                      stroke="currentColor"
                      strokeDasharray={EDGE_STROKE[e.type]}
                      className="text-mute opacity-40 transition-opacity motion-reduce:transition-none hover:opacity-80"
                    >
                      <title>
                        {`${na?.label ?? e.a} ↔ ${nb?.label ?? e.b} · w=${e.w}`}
                      </title>
                    </line>
                  );
                })}
              </g>
              <g>
                {g.nodes.filter((n) => visible.ids.has(n.id)).map((n) => {
                  const p = posById.get(n.id)!;
                  return (
                    <circle
                      key={n.id}
                      cx={p.x}
                      cy={p.y}
                      r={NODE_R[n.type]}
                      tabIndex={0}
                      role="button"
                      aria-label={`${n.label} · w=${n.degree.co_hold + n.degree.co_board + n.degree.co_target}`}
                      onClick={() => setDrawerId(n.id)}
                      onKeyDown={(ev) => {
                        if (ev.key === "Enter" || ev.key === " ") setDrawerId(n.id);
                      }}
                      className={cn(
                        "cursor-pointer stroke-card transition-opacity motion-reduce:transition-none",
                        n.type === "institution"
                          ? "fill-brand"
                          : n.type === "person"
                            ? "fill-ink"
                            : "fill-sub",
                        drawerId === n.id
                          ? "opacity-100"
                          : "opacity-70 hover:opacity-100",
                      )}
                    />
                  );
                })}
              </g>
            </svg>
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1 px-2 pb-1 pt-1 text-[11px] text-mute">
              {(
                [
                  ["institution", "bg-brand"],
                  ["person", "bg-ink"],
                  ["staker", "bg-sub"],
                ] as const
              ).map(([kind, dot]) => (
                <span key={kind} className="inline-flex items-center gap-1.5">
                  <span className={cn("inline-block size-2 rounded-full", dot)} />
                  {t(`forcecamp.legend.${kind}`)}
                </span>
              ))}
              <span className="ml-auto font-mono">— / ‑ ‑ : co_board · · : co_target</span>
            </div>
          </div>

          {/* Node drawer card */}
          {drawer ? (
            <div className="rounded-xl border border-line bg-card px-5 py-4">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="truncate text-[15px] font-semibold">{drawer.label}</p>
                  {drawer.zh_label ? (
                    <p className="text-[12px] text-sub">{drawer.zh_label}</p>
                  ) : null}
                </div>
                <button
                  type="button"
                  aria-label="close"
                  onClick={() => setDrawerId(null)}
                  className="rounded-md p-1 text-mute hover:bg-soft hover:text-ink"
                >
                  <XIcon className="size-4" />
                </button>
              </div>
              <div className="mt-3 flex flex-wrap gap-x-6 gap-y-2 text-[12px]">
                <div>
                  <span className="text-mute">{t("forcecamp.drawer.roles")}: </span>
                  {drawer.lanes.length ? (
                    drawer.lanes.map((ln) => (
                      <span
                        key={ln}
                        className="mr-1 rounded bg-soft px-1.5 py-0.5 font-mono text-[11px] text-sub"
                      >
                        {laneLabel(ln)}
                      </span>
                    ))
                  ) : (
                    <span>{fmtEmpty(null)}</span>
                  )}
                </div>
                <div className="font-mono tabular-nums">
                  {EDGE_TYPES.map((kind) => (
                    <span key={kind} className="mr-3 whitespace-nowrap text-sub">
                      {t(`forcecamp.type.${kind}`)}{" "}
                      <b className="text-ink">{fmtInt(drawer.degree[kind])}</b>
                    </span>
                  ))}
                </div>
              </div>
              <div className="mt-2 flex flex-wrap items-center gap-x-6 gap-y-2 text-[12px]">
                <div className="min-w-0">
                  <span className="text-mute">{t("forcecamp.drawer.seats")}: </span>
                  {seatItems.length ? (
                    seatItems.map((it, i) => {
                      const label =
                        "company" in it ? it.company : "target" in it ? it.target : it.issuer;
                      const tk = it.tk;
                      return (
                        <span key={`${label}-${i}`} className="mr-2 whitespace-nowrap text-sub">
                          {fmtEmpty(label)}
                          {tk ? <> · <StockTk tk={tk} /></> : null}
                        </span>
                      );
                    })
                  ) : (
                    <span>{fmtEmpty(null)}</span>
                  )}
                </div>
                {drawer.type === "institution" && drawer.manager_routable && drawer.cik ? (
                  <Link
                    href={`/manager/${drawer.cik}`}
                    className="shrink-0 font-semibold text-brand hover:text-brand-hover"
                  >
                    /manager/{drawer.cik}
                  </Link>
                ) : drawer.type !== "institution" ? (
                  <span className="text-mute">{fmtEmpty(null)}</span>
                ) : null}
              </div>
            </div>
          ) : null}

          {/* Four permanent tables — the always-there fallback surface. */}
          {(["co_hold", "co_board", "co_target"] as const).map((kind) => (
            <section
              key={kind}
              className="overflow-hidden rounded-xl border border-line bg-card"
            >
              <header className="flex items-center justify-between border-b border-line2 bg-soft px-5 py-2">
                <h2 className="text-[13px] font-semibold">
                  {t(`forcecamp.type.${kind}`)}
                </h2>
                <span className="font-mono text-[11px] text-mute">
                  {fmtInt(counts[kind])}
                </span>
              </header>
              <table className="w-full text-left text-[12px]">
                <thead>
                  <tr className="text-mute">
                    <th className="w-[26%] px-4 py-1.5 font-medium">{t("forcecamp.table.edge_a")}</th>
                    <th className="w-[26%] px-4 py-1.5 font-medium">{t("forcecamp.table.edge_b")}</th>
                    <th className="w-[10%] px-2 py-1.5 text-right font-medium">{t("forcecamp.table.weight")}</th>
                    <th className="px-4 py-1.5 font-medium">{t("forcecamp.table.shared")}</th>
                  </tr>
                </thead>
                <tbody>
                  {byType[kind].slice(0, 12).map((e) => (
                    <tr key={`${e.a}-${e.b}`} className="border-t border-line2">
                      <td className="max-w-0 truncate px-4 py-1.5">
                        <button
                          type="button"
                          className="max-w-full truncate text-left hover:text-brand-hover"
                          onClick={() => setDrawerId(e.a)}
                        >
                          {byId.get(e.a)?.label ?? fmtEmpty(null)}
                        </button>
                      </td>
                      <td className="max-w-0 truncate px-4 py-1.5">
                        <button
                          type="button"
                          className="max-w-full truncate text-left hover:text-brand-hover"
                          onClick={() => setDrawerId(e.b)}
                        >
                          {byId.get(e.b)?.label ?? fmtEmpty(null)}
                        </button>
                      </td>
                      <td className="px-2 py-1.5 text-right font-mono tabular-nums">{e.w}</td>
                      <td className="max-w-0 truncate px-4 py-1.5 text-sub">
                        <SharedLine e={e} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {!byType[kind].length ? (
                <p className="px-5 py-6 text-center text-[12px] text-mute">
                  {t("forcecamp.empty")}
                </p>
              ) : null}
            </section>
          ))}

          {/* Cross-lane bridge table */}
          <section className="overflow-hidden rounded-xl border border-line bg-card">
            <header className="flex items-center justify-between border-b border-line2 bg-soft px-5 py-2">
              <h2 className="text-[13px] font-semibold">{t("forcecamp.bridge.title")}</h2>
              <span className="font-mono text-[11px] text-mute">
                {fmtInt(g.bridges.length)}
              </span>
            </header>
            <table className="w-full text-left text-[12px]">
              <thead>
                <tr className="text-mute">
                  <th className="w-[14%] px-4 py-1.5 font-medium">TK</th>
                  <th className="w-[20%] px-4 py-1.5 font-medium">in</th>
                  <th className="w-[36%] px-4 py-1.5 font-medium">{t("forcecamp.drawer.seats")}</th>
                  <th className="px-4 py-1.5 text-right font-medium">
                    13F / DEF 14A / 13D-G
                  </th>
                </tr>
              </thead>
              <tbody>
                {g.bridges.map((b) => (
                  <tr key={b.tk} className="border-t border-line2">
                    <td className="px-4 py-1.5 font-mono font-semibold">
                      {b.stock_routable ? (
                        <Link
                          href={`/stock/${b.tk}`}
                          className="text-brand hover:text-brand-hover"
                        >
                          {b.tk}
                        </Link>
                      ) : (
                        <span className="text-ink">{b.tk}</span>
                      )}
                    </td>
                    <td className="px-4 py-1.5 font-mono text-sub">
                      {b.in.map(laneLabel).join(" · ")}
                    </td>
                    <td className="max-w-0 truncate px-4 py-1.5 text-sub">
                      {fmtEmpty(b.name)}
                    </td>
                    <td className="px-4 py-1.5 text-right font-mono tabular-nums text-sub">
                      {fmtInt(b.counts.managers)} / {fmtInt(b.counts.persons)} /{" "}
                      {fmtInt(b.counts.stakers)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!g.bridges.length ? (
              <p className="px-5 py-6 text-center text-[12px] text-mute">
                {t("forcecamp.empty")}
              </p>
            ) : null}
          </section>
        </>
      )}

      {/* Methodology + red-line disclaimers */}
      <div className="rounded-xl border border-line bg-card px-5 py-4">
              <div className="flex items-center justify-between gap-3">
                <p className="text-[13px] font-semibold">
                  {t("overview.explore.t_forcecamp")}
                </p>
                <ProvenanceBadge ts={g.as_of ?? undefined} />
              </div>
        <p className="mt-1 text-[12px] leading-relaxed text-sub">
          {t("forcecamp.disclaimer.coordination")}
        </p>
        <p className="mt-1 text-[12px] leading-relaxed text-sub">
          {t("forcecamp.disclaimer.window")}
        </p>
        {ready ? (
          <p className="mt-2 line-clamp-4 font-mono text-[11px] leading-relaxed text-mute">
            {g.methodology}
          </p>
        ) : null}
        <p className="mt-1 font-mono text-[11px] text-mute">
          {ready
            ? `${g.windows.form13f_quarter} · ${fmtDateShort(g.windows.stakes_visible_dates.start)}→${fmtDateShort(g.windows.stakes_visible_dates.end)} · ${fmtDateShort(g.windows.smart_money_visible_dates.start)}→${fmtDateShort(g.windows.smart_money_visible_dates.end)}`
            : ""}
        </p>
      </div>
    </div>
  );
}
