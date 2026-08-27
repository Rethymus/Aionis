import { SegmentHeader } from "@/components/segment-header";
import { ForceCampView } from "@/components/force-camp/force-camp-view";
import { lineageGraph } from "@/data/aionis/lineage-graph";
import { fmtInt } from "@/lib/format";

// /force-camp — 势力阵营血缘图谱（display lane：导出期从已提交面板派生，
// 零新抓取、零研究面接触）。SegmentHeader 用 evidence 段——本图是三条独立
// 申报证据的交叉投影；component 的 Segment 联合类型没有 institution 值。
export default function ForceCampPage() {
  const g = lineageGraph;
  const ready = g.status === "ok" && g.n_edges > 0;
  return (
    <div className="space-y-6 p-4 md:p-6">
      <SegmentHeader
        segment="evidence"
        introKey="forcecamp.intro"
        asOf={g.as_of ?? undefined}
        countHint={
          ready
            ? `${fmtInt(g.n_edges)} · 13F-Q × DEF-14A × 13D/G · G ${g.windows.stakes_visible_dates.start?.slice(5) ?? "—"}→${g.windows.stakes_visible_dates.end?.slice(5) ?? "—"} / D ${g.windows.smart_money_visible_dates.start?.slice(5) ?? "—"}→${g.windows.smart_money_visible_dates.end?.slice(5) ?? "—"}`
            : undefined
        }
      />
      <ForceCampView />
    </div>
  );
}
