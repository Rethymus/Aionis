import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "研究图谱 · Aionis",
  description: "编辑级研究叙事图：主张 · 分差 · 诊断 · 血缘。",
};

export default function RouteLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
