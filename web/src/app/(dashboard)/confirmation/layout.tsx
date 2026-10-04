import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "多源确认 · Aionis",
  description: "聪明钱 · 内部人 · Reddit · 新闻情绪：四源交叉验证。",
};

export default function RouteLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
