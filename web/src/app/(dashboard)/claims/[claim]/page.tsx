import type { Metadata } from "next";
import { ClaimBrowserView } from "@/components/claims/claim-browser-view";

// Mirror of CLAIM_KEYS in claim-bibtex.ts (defined locally: this server
// component must not enumerate exports of a "use client" module).
const CLAIM_KEYS = ["B", "C", "E1", "D", "track_c"] as const;
type ClaimKey = (typeof CLAIM_KEYS)[number];

// One citable card per pre-registered claim (OSAP Signal Browser analogue,
// payload inverted: nulls). Static export: one page per claim key.
export function generateStaticParams() {
  return CLAIM_KEYS.map((claim) => ({ claim }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ claim: string }>;
}): Promise<Metadata> {
  const { claim } = await params;
  const label = claim === "track_c" ? "Track C" : `Phase ${claim}`;
  return { title: `${label} claim · Aionis` };
}

export default async function Page({
  params,
}: {
  params: Promise<{ claim: string }>;
}) {
  const { claim } = await params;
  return <ClaimBrowserView claim={claim as ClaimKey} />;
}
