import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "市场全景 · Aionis",
  description: "美股等权指数 × VIX（2016→），总统↔美联储博弈事件标记。",
};

export default function RouteLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
