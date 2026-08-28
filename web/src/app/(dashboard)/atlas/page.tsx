"use client";

import { SegmentHeader } from "@/components/segment-header";
import AtlasClaims from "@/components/atlas/atlas-claims";
import AtlasDivergence from "@/components/atlas/atlas-divergence";
import AtlasDiagnostics from "@/components/atlas/atlas-diagnostics";
import AtlasDataflow from "@/components/atlas/atlas-dataflow";
import { useI18n } from "@/i18n/provider";
import { aionis } from "@/data/aionis";
import { fmtInt } from "@/lib/format";

// /atlas — 研究图谱(编辑级确定性研究图表;display lane:全部从已提交面板
// 派生,零新抓取、零研究面接触)。四区块各答一个可信度问题:主张说了什么
// (claims)/预测与实现分差多大(divergence)/分数面形态如何(diagnostics)/
// 每个数字从哪来(dataflow)。
// 设计规格:reports/design/2026-08-28-editorial-diagram-language.md。
// Client shell(shelf 先例):sr-only h1 用既有 nav.atlas 键——server 壳拿
// 不到 i18n,轮㉕审计标准要求每页恰好一个 h1。
export default function AtlasPage() {
  const { t } = useI18n();
  const dh = aionis.dataHealth;
  const s = dh.summary;
  return (
    <div className="space-y-6 p-4 md:p-6">
      <h1 className="sr-only">{t("nav.atlas")}</h1>
      <SegmentHeader
        segment="validity"
        introKey="atlas.intro"
        asOf={dh.snapshot_ts?.slice(0, 10) ?? undefined}
        countHint={`${fmtInt(s.n_panels)} panels · ${fmtInt(s.n_daily)} daily / ${fmtInt(s.n_cadence)} cadence / ${fmtInt(s.n_frozen)} frozen`}
      />
      <AtlasClaims />
      <AtlasDivergence />
      <AtlasDiagnostics />
      <AtlasDataflow />
    </div>
  );
}
