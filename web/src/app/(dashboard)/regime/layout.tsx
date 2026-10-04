import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "市场域 · Aionis",
  description: "宏观语境 · 定位 · 关税 · 宏观制度。",
};

export default function RouteLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
