import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "功效下限 · Aionis",
  description: "统计功效监控：SESOI 等价检验下限。",
};

export default function RouteLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
