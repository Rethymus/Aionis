import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "数据健康 · Aionis",
  description: "56 个面板的新鲜度与来源健康。",
};

export default function RouteLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
