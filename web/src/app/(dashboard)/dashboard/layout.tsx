// Per-route metadata layouts (round 175): the (dashboard) pages are client
// components (useI18n) and cannot export metadata themselves. These thin
// server-layout shims give each major route a distinct <title> and meta
// description — browser tabs become distinguishable, bookmarks get real
// names, and search engines can differentiate pages (the root layout's
// generic title previously applied to all 38 routes).
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "总览 · Aionis",
  description: "研究总览：四相冻结 NULL 裁决的论证链入口。",
};

export default function RouteLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
