import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "证据 · Aionis",
  description: "入账估计证据表与 S-registry。",
};

export default function RouteLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
