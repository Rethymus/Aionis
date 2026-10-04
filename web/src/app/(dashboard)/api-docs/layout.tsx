import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "API 文档 · Aionis",
  description: "静态 JSON 面板 API 端点目录。",
};

export default function RouteLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
