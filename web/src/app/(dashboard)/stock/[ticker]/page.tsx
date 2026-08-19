import type { Metadata } from "next";
import { StockView } from "@/components/stock/stock-view";
import { stockUniverse } from "@/data/aionis/stock-universe";

// Per-stock drill-down over the frozen OOS universe (display-only). Static
// export: one page per ticker in the latest OOS month (both regions).
export function generateStaticParams() {
  return stockUniverse.stocks.map((s) => ({ ticker: s.ticker }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ ticker: string }>;
}): Promise<Metadata> {
  const { ticker } = await params;
  const s = stockUniverse.stocks.find((x) => x.ticker === ticker);
  return { title: s && s.name ? `${s.name} (${ticker}) · Aionis` : `${ticker} · Aionis` };
}

export default async function Page({
  params,
}: {
  params: Promise<{ ticker: string }>;
}) {
  const { ticker } = await params;
  return <StockView ticker={ticker} />;
}
