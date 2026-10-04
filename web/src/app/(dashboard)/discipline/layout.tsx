import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "纪律 · Aionis",
  description: "账本审计时间线：防泄漏纪律的执行记录。",
};

export default function RouteLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
