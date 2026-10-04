import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "校准 · Aionis",
  description: "可靠性散点 + ECE 时间线：概率校准质量。",
};

export default function RouteLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
