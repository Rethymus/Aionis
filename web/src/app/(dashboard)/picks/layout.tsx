import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "选股决策 · Aionis",
  description: "冻结 OOS Top 10 美股 + Top 10 A股精选与空头。",
};

export default function RouteLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
