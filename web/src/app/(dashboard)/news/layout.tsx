import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "新闻流 · Aionis",
  description: "美股/市场新闻双语流。",
};

export default function RouteLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
