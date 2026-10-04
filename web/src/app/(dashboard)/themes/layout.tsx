import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "主题 · Aionis",
  description: "主题信号与情绪追踪。",
};

export default function RouteLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
