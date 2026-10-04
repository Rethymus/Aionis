import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "热力图 · Aionis",
  description: "US 492 + CN 929 双市场树图：冻结评分全景。",
};

export default function RouteLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
