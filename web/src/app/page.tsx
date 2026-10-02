import type { Metadata } from "next";
import { Overview } from "@/components/overview/overview";

// Root-landing brief option B (round 116, reports/design/2026-10-02 brief):
// `/` used to be a client redirect shell — every first visit paid ~2.4s of
// redirect-chain LCP tax (Lighthouse 5.8s). `/` now renders the dashboard
// overview directly inside the shared shell (lifted to the root layout).
// `/dashboard` keeps the same content; canonical consolidates search signals
// onto the long-established URL, and the sitemap (round 111) is unchanged.
export const metadata: Metadata = {
  title: "Aionis — 反泄漏选股研究终端",
  alternates: {
    canonical: "https://rethymus.github.io/Aionis/dashboard.html",
  },
};

export default function Home() {
  return <Overview />;
}
