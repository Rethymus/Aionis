import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "效度论证 · Aionis",
  description: "校准 · 功效下限 · 模型健康 · 纪律 · 证据链。",
};

export default function RouteLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
