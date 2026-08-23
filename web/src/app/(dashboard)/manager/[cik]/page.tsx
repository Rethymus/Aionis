import type { Metadata } from "next";
import { SegmentHeader } from "@/components/segment-header";
import { ManagerView } from "@/components/institutions/manager-view";
import { form13f } from "@/data/aionis/form13f";

// Per-manager drill-down over the star-manager 13F registry (display-only).
// Static export: one page per manager CIK in the committed form13f.json —
// mirrors /stock/[ticker]'s generateStaticParams pattern. The CIK param is
// the 10-digit zero-padded EDGAR identifier carried in the JSON payload.
export function generateStaticParams() {
  return form13f.managers.map((m) => ({ cik: m.cik }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ cik: string }>;
}): Promise<Metadata> {
  const { cik } = await params;
  const m = form13f.managers.find((x) => x.cik === cik);
  return {
    title: m ? `${m.name} · Aionis` : `Manager ${cik} · Aionis`,
  };
}

export default async function Page({
  params,
}: {
  params: Promise<{ cik: string }>;
}) {
  const { cik } = await params;
  return (
    <div className="space-y-6 p-4 md:p-6">
      <SegmentHeader
        segment="evidence"
        introKey="manager.intro"
        asOf={form13f.as_of ?? undefined}
      />
      <ManagerView cik={cik} />
    </div>
  );
}
