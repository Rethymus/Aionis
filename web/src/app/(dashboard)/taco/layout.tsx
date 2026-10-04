import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "关税博弈 · Aionis",
  description: "总统↔美联储关税博弈时间线。",
};

export default function RouteLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
