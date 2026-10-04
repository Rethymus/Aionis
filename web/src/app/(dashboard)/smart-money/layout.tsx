import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "聪明钱 · Aionis",
  description: "13D/13G 聪明钱流与明星经理。",
};

export default function RouteLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
