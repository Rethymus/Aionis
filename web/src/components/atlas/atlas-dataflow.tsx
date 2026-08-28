"use client";

import { aionis, type DataHealthPanel } from "@/data/aionis";
import { useI18n } from "@/i18n/provider";
import { diagram } from "@/components/diagram/tokens";
import { DiagramFigure } from "@/components/diagram/primitives";
import { Card, CardContent } from "@/components/ui/card";
import { fmtEmpty, fmtInt } from "@/lib/format";

// /atlas section 3 — data-lineage three-layer flow (first-hand source family →
// panel category → freshness). Display lane, zero fetches: dataHealth.panels
// is the spine, key-joined against apiCatalog.endpoints for the free-text
// `source`; the join is honest — a panel that misses lands in the
// "Other / mixed" family and is never guessed into a nicer bucket.
//
// Determinism contract (H6 spirit, display edition): every layout coordinate
// is a pure function of the committed panels — no Date.now / new Date /
// Math.random anywhere, fixed sort orders everywhere, and as_of is handled by
// string comparison only (year-month buckets via a literal ^YYYY-MM check).
// The SSG prerender freezes the SVG at build time; the full <table> below is
// the accessibility / degraded / mobile fallback and its column headers render
// even on an honest empty panel (force-camp precedent, P9).
//
// Category colors are a fixed blue/orange/gray mapping (blue↔orange is the
// editorial colorblind-safe pair from the diagram tokens; gray = frozen). No
// --up/--down direction semantics and no red/green enter this figure.

type Cat = DataHealthPanel["category"];

// --- Source-family grouping (deterministic keyword rules) ------------------
//
// Ordered rules: case-insensitive substring match, first family with any
// keyword hit wins, fallback is the "other" bucket. Rule ORDER is load-bearing:
// the derived-artifact rules run FIRST so composite sources that merely name
// raw feeds (e.g. the force-camp graph text mentioning "13F-HR / DEF 14A /
// SC 13D/13G") stay in the derived family they actually belong to.

type FamilyId =
  | "derived"
  | "edgar_sec"
  | "fred_alfred"
  | "gdelt"
  | "reddit"
  | "ark"
  | "cftc"
  | "congress"
  | "other";

type FamilyRule = { id: FamilyId; keywords: readonly string[] };

const FAMILY_RULES: readonly FamilyRule[] = [
  {
    id: "derived",
    keywords: [
      "frozen oos",
      "oos scores",
      "oos picks",
      "ledger",
      "psi",
      "rank-ic",
      "calibration",
      "sigma",
      "sweep",
      "dispersion",
      "power analysis",
      "force-camp",
      "digest of",
      "per-theme signal",
      "d-vs-r",
      "method catalog",
    ],
  },
  {
    id: "edgar_sec",
    keywords: [
      "efts",
      "edgar",
      "13f",
      "13d",
      "13g",
      "def 14a",
      "form 4",
      "form 8-k",
      "form d",
      "s-1",
      "424b4",
      "company_tickers",
    ],
  },
  {
    id: "fred_alfred",
    keywords: ["fred", "alfred", "vintages", "cpi", "payrolls", "macro"],
  },
  { id: "gdelt", keywords: ["gdelt"] },
  { id: "reddit", keywords: ["reddit", "apewisdom", "retail mention"] },
  { id: "ark", keywords: ["ark-funds", "ark invest"] },
  { id: "cftc", keywords: ["commitments of traders", "cftc"] },
  { id: "congress", keywords: ["stock act", "ptr"] },
];

// Language-neutral proper-noun labels (data-derived, like force-camp node
// labels — the preset i18n keys cover the layer/category/table strings only).
const FAMILY_LABEL: Record<FamilyId, string> = {
  derived: "Aionis derived / frozen",
  edgar_sec: "EDGAR / SEC",
  fred_alfred: "FRED / ALFRED",
  gdelt: "GDELT",
  reddit: "Reddit / ApeWisdom",
  ark: "ARK funds",
  cftc: "CFTC",
  congress: "US Congress PTR",
  other: "Other / mixed",
};

function sourceFamily(source: string | null): FamilyId {
  if (!source) return "other";
  const s = source.toLowerCase();
  for (const rule of FAMILY_RULES) {
    for (const kw of rule.keywords) {
      if (s.includes(kw)) return rule.id;
    }
  }
  return "other";
}

// --- Freshness buckets (string comparison only — no date math) -------------

const MONTH_RE = /^\d{4}-\d{2}/;

/** "2026-08-27" / "2026-08-28T01:30:00Z" / "2026-08" → "YYYY-MM";
 *  null or non-conforming → "" (the honest unknown bucket, rendered "—"). */
function monthBucket(asOf: string | null): string {
  return asOf && MONTH_RE.test(asOf) ? asOf.slice(0, 7) : "";
}

// --- Deterministic sankey-style layout --------------------------------------

const VB_W = 1000;
const VB_H = 480;
const CHART_TOP = 44;
const CHART_BOTTOM = 464;
const NODE_W = 130;
const L1_X = 180;
const L2_X = 455;
const L3_X = 730;
const GAP_L1 = 10;
const GAP_MID = 14;

const CAT_ORDER: readonly Cat[] = ["daily", "cadence", "frozen"];

// Fixed category colors — light steps of the token file's colorblind-safe
// blue↔orange pair plus the theme gray; ink text stays readable on all three.
const CAT_FILL: Record<Cat, string> = {
  daily: "oklch(0.66 0.09 264)",
  cadence: "oklch(0.78 0.09 60)",
  frozen: diagram.mutedBg,
};

type FamilyNode = { id: FamilyId; label: string; count: number; y: number; h: number };
type CatNode = { cat: Cat; count: number; y: number; h: number };
type MonthNode = { month: string; count: number; y: number; h: number };
type Link = { sy: number; ty: number; w: number; title: string };
type Row = {
  key: string;
  cat: Cat;
  asOf: string | null;
  family: FamilyId;
  license: string;
  month: string;
};

function stack<T extends { count: number }>(
  items: T[],
  unit: number,
  gap: number,
): (T & { y: number; h: number })[] {
  let y = CHART_TOP;
  return items.map((it) => {
    const node = { ...it, y, h: it.count * unit };
    y += node.h + gap;
    return node;
  });
}

function ribbonPath(x1: number, y1: number, x2: number, y2: number, w: number): string {
  const xm = (x1 + x2) / 2;
  return [
    `M ${x1} ${y1}`,
    `C ${xm} ${y1} ${xm} ${y2} ${x2} ${y2}`,
    `L ${x2} ${y2 + w}`,
    `C ${xm} ${y2 + w} ${xm} ${y1 + w} ${x1} ${y1 + w}`,
    "Z",
  ].join(" ");
}

function buildFlow(rows: Row[]) {
  const total = rows.length;

  // Layer 1 — families, count desc then id asc (fixed tie-break).
  const famCount = new Map<FamilyId, number>();
  for (const r of rows) famCount.set(r.family, (famCount.get(r.family) ?? 0) + 1);
  const famOrder = [...famCount.entries()]
    .sort((a, b) => b[1] - a[1] || (a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0))
    .map(([id]) => id);

  // Unit height: linear px-per-panel, quantized to .5 so the busiest layer
  // (families) fits the chart band exactly. Same unit drives ALL layers, so
  // node heights stay comparable across columns.
  const usable = CHART_BOTTOM - CHART_TOP;
  const unit =
    total > 0
      ? Math.max(
          0.5,
          Math.floor(((usable - (famOrder.length - 1) * GAP_L1) / total) * 2) / 2,
        )
      : 0;

  const families: FamilyNode[] = stack(
    famOrder.map((id) => ({ id, label: FAMILY_LABEL[id], count: famCount.get(id) ?? 0 })),
    unit,
    GAP_L1,
  );

  // Layer 2 — categories in the fixed daily/cadence/frozen order.
  const catCount = new Map<Cat, number>();
  for (const r of rows) catCount.set(r.cat, (catCount.get(r.cat) ?? 0) + 1);
  const cats: CatNode[] = stack(
    CAT_ORDER.map((cat) => ({ cat, count: catCount.get(cat) ?? 0 })),
    unit,
    GAP_MID,
  );

  // Layer 3 — as_of year-month buckets ascending (string sort), unknown last.
  const monthCount = new Map<string, number>();
  for (const r of rows) monthCount.set(r.month, (monthCount.get(r.month) ?? 0) + 1);
  const monthOrder = [...monthCount.keys()].sort((a, b) => {
    if (a === "") return 1;
    if (b === "") return -1;
    return a < b ? -1 : a > b ? 1 : 0;
  });
  const months: MonthNode[] = stack(
    monthOrder.map((month) => ({ month, count: monthCount.get(month) ?? 0 })),
    unit,
    GAP_MID,
  );

  // Ribbons: flows aggregate per (source, target); slots walk each node edge
  // in the same fixed orders as the stacks, so ribbons tile the nodes exactly.
  const links12: Link[] = [];
  const famSlot = new Map(families.map((n) => [n.id, n.y]));
  const catLeft = new Map(cats.map((n) => [n.cat, n.y]));
  for (const f of families) {
    for (const c of cats) {
      const n = rows.filter((r) => r.family === f.id && r.cat === c.cat).length;
      if (!n) continue;
      const w = n * unit;
      links12.push({
        sy: famSlot.get(f.id) ?? f.y,
        ty: catLeft.get(c.cat) ?? c.y,
        w,
        title: `${f.label} → ${c.cat} · ${n}`,
      });
      famSlot.set(f.id, (famSlot.get(f.id) ?? f.y) + w);
      catLeft.set(c.cat, (catLeft.get(c.cat) ?? c.y) + w);
    }
  }

  const links23: Link[] = [];
  const catRight = new Map(cats.map((n) => [n.cat, n.y]));
  const monthLeft = new Map(months.map((n) => [n.month, n.y]));
  for (const c of cats) {
    for (const m of months) {
      const n = rows.filter((r) => r.cat === c.cat && r.month === m.month).length;
      if (!n) continue;
      const w = n * unit;
      links23.push({
        sy: catRight.get(c.cat) ?? c.y,
        ty: monthLeft.get(m.month) ?? m.y,
        w,
        title: `${c.cat} → ${m.month === "" ? "no as_of" : m.month} · ${n}`,
      });
      catRight.set(c.cat, (catRight.get(c.cat) ?? c.y) + w);
      monthLeft.set(m.month, (monthLeft.get(m.month) ?? m.y) + w);
    }
  }

  return { total, unit, families, cats, months, links12, links23 };
}

// --- Component ---------------------------------------------------------------

export default function AtlasDataflow() {
  const { t } = useI18n();

  // Spine = dataHealth.panels; key-join to the API catalog for source/license.
  const epByKey = new Map(aionis.apiCatalog.endpoints.map((e) => [e.key, e]));
  const rows: Row[] = aionis.dataHealth.panels.map((p) => {
    const ep = epByKey.get(p.key) ?? null;
    return {
      key: p.key,
      cat: p.category,
      asOf: p.as_of,
      family: sourceFamily(ep ? ep.source : null),
      license: ep ? ep.license : "",
      month: monthBucket(p.as_of),
    };
  });
  const flow = buildFlow(rows);

  const catLabel = (c: Cat) => t(`atlas.flow.cat.${c}`);
  const famPos = new Map(flow.families.map((n, i) => [n.id, i]));

  // Table rows follow the figure's own ordering (family stack → category → key).
  const tableRows = [...rows].sort((a, b) => {
    const fa = famPos.get(a.family) ?? 0;
    const fb = famPos.get(b.family) ?? 0;
    if (fa !== fb) return fa - fb;
    const ca = CAT_ORDER.indexOf(a.cat);
    const cb = CAT_ORDER.indexOf(b.cat);
    if (ca !== cb) return ca - cb;
    return a.key < b.key ? -1 : a.key > b.key ? 1 : 0;
  });

  const stamped = flow.months.map((m) => m.month).filter((m) => m !== "");
  const span =
    stamped.length > 1 ? `${stamped[0]} → ${stamped[stamped.length - 1]}` : "";
  const caption = [
    t("atlas.flow.n").replace("{n}", fmtInt(flow.total)),
    span,
  ]
    .filter(Boolean)
    .join(" · ");

  const table = (
    <section className="overflow-hidden rounded-xl border border-line bg-card">
      <header className="flex items-center justify-between border-b border-line2 bg-soft px-5 py-2">
        <h3 className="text-[13px] font-semibold">{t("atlas.flow.table")}</h3>
        <span className="font-mono text-[11px] text-mute">{fmtInt(flow.total)}</span>
      </header>
      <table className="w-full text-left text-[12px]">
        <thead>
          <tr className="text-mute">
            <th className="w-[20%] px-4 py-1.5 font-medium">panel key</th>
            <th className="w-[20%] px-4 py-1.5 font-medium">source family</th>
            <th className="w-[12%] px-2 py-1.5 font-medium">category</th>
            <th className="w-[14%] px-2 py-1.5 font-medium">as_of</th>
            <th className="px-4 py-1.5 font-medium">license</th>
          </tr>
        </thead>
        <tbody>
          {tableRows.map((r) => (
            <tr key={r.key} className="border-t border-line2">
              <td className="px-4 py-1.5 font-mono font-semibold">{r.key}</td>
              <td className="px-4 py-1.5 text-sub">{FAMILY_LABEL[r.family]}</td>
              <td className="px-2 py-1.5">{catLabel(r.cat)}</td>
              <td className="px-2 py-1.5 font-mono tabular-nums text-sub">
                {fmtEmpty(r.asOf)}
              </td>
              <td className="max-w-0 truncate px-4 py-1.5 text-sub">
                {fmtEmpty(r.license || null)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );

  return (
    <Card className="py-0">
      <CardContent className="px-5 py-5">
        <DiagramFigure
          title={t("atlas.flow.title")}
          desc={t("atlas.flow.desc")}
          caption={caption}
          table={table}
        >
          <div className="overflow-hidden rounded-xl border border-line bg-card p-2">
            <svg viewBox={`0 0 ${VB_W} ${VB_H}`} className="h-auto w-full">
              {/* Layer headers */}
              {(
                [
                  [L1_X + NODE_W / 2, t("atlas.flow.l1")],
                  [L2_X + NODE_W / 2, t("atlas.flow.l2")],
                  [L3_X + NODE_W / 2, t("atlas.flow.l3")],
                ] as const
              ).map(([x, label]) => (
                <text
                  key={label}
                  x={x}
                  y={26}
                  textAnchor="middle"
                  fontSize={11}
                  fill={diagram.muted}
                >
                  {label}
                </text>
              ))}

              {/* Ribbons: family→category (primary), category→freshness (muted) */}
              {flow.links12.map((l) => (
                <path
                  key={`f2c-${l.sy}-${l.ty}`}
                  d={ribbonPath(L1_X + NODE_W, l.sy, L2_X, l.ty, l.w)}
                  fill={diagram.primary}
                  fillOpacity={0.3}
                >
                  <title>{l.title}</title>
                </path>
              ))}
              {flow.links23.map((l) => (
                <path
                  key={`c2m-${l.sy}-${l.ty}`}
                  d={ribbonPath(L2_X + NODE_W, l.sy, L3_X, l.ty, l.w)}
                  fill={diagram.muted}
                  fillOpacity={0.55}
                >
                  <title>{l.title}</title>
                </path>
              ))}

              {/* Layer 1 nodes + labels */}
              {flow.families.map((n) => (
                <g key={n.id}>
                  <rect
                    x={L1_X}
                    y={n.y}
                    width={NODE_W}
                    height={n.h}
                    fill={diagram.mutedBg}
                    stroke={diagram.border}
                  >
                    <title>{`${n.label} · ${n.count}`}</title>
                  </rect>
                  <text
                    x={L1_X - 10}
                    y={n.y + n.h / 2 + 3.5}
                    textAnchor="end"
                    fontSize={11.5}
                    fill={diagram.ink}
                  >
                    {n.label}
                    <tspan fill={diagram.muted}> · {fmtInt(n.count)}</tspan>
                  </text>
                </g>
              ))}

              {/* Layer 2 nodes (fixed category colors) + inline labels */}
              {flow.cats.map((n) => (
                <g key={n.cat}>
                  <rect
                    x={L2_X}
                    y={n.y}
                    width={NODE_W}
                    height={n.h}
                    fill={CAT_FILL[n.cat]}
                    stroke={diagram.border}
                  >
                    <title>{`${catLabel(n.cat)} · ${n.count}`}</title>
                  </rect>
                  <text
                    x={L2_X + 9}
                    y={n.h < 18 ? n.y - 5 : n.y + n.h / 2 + 3.5}
                    fontSize={11.5}
                    fill={diagram.ink}
                  >
                    {catLabel(n.cat)}
                    <tspan fill={diagram.muted}> · {fmtInt(n.count)}</tspan>
                  </text>
                </g>
              ))}

              {/* Layer 3 nodes + labels (as_of year-month buckets, unknown last) */}
              {flow.months.map((n) => (
                <g key={n.month || "unknown"}>
                  <rect
                    x={L3_X}
                    y={n.y}
                    width={NODE_W}
                    height={n.h}
                    fill={diagram.card}
                    stroke={diagram.border}
                  >
                    <title>{`${n.month === "" ? "no as_of" : n.month} · ${n.count}`}</title>
                  </rect>
                  <text
                    x={L3_X + NODE_W + 10}
                    y={n.y + n.h / 2 + 3.5}
                    fontSize={11.5}
                    fill={diagram.ink}
                    className="font-mono"
                  >
                    {n.month === "" ? fmtEmpty(null) : n.month}
                    <tspan fill={diagram.muted}> · {fmtInt(n.count)}</tspan>
                  </text>
                </g>
              ))}
            </svg>
          </div>
        </DiagramFigure>

        {/* Data-provided freshness/provenance methodology (force-camp precedent:
            committed methodology prose rendered verbatim, never rewritten). */}
        <p className="mt-3 line-clamp-4 font-mono text-[11px] leading-relaxed text-mute">
          {aionis.dataHealth.methodology}
        </p>
      </CardContent>
    </Card>
  );
}
