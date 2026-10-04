import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "内部人 · Aionis",
  description: "Form 4 申报流：内部人交易信号。",
};

export default function RouteLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
