import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "方法货架 · Aionis",
  description: "预注册 · ADR · 结果 · 理论：项目方法学文档目录。",
};

export default function RouteLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
