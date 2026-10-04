import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "国会交易 · Aionis",
  description: "众议院 PTR 交易披露流。",
};

export default function RouteLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
