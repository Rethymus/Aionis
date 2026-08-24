import type { Metadata } from "next";
import { Geist } from "next/font/google";

// Deployed-terminal alignment: Geist as the latin display face (self-hosted
// at build time via next/font; CJK falls back to the native system stack).
const geist = Geist({ subsets: ["latin"], variable: "--font-geist", display: "swap" });
import { ThemeProvider } from "next-themes";
import { TooltipProvider } from "@/components/ui/tooltip";
import { I18nProvider } from "@/i18n/provider";
import "./globals.css";

// Typography is the native system stack (SF Pro on Apple, Segoe UI elsewhere,
// PingFang/YaHei for CJK) defined in globals.css — the Apple signature, no
// webfont approximation, zero network font cost.

export const metadata: Metadata = {
  metadataBase: new URL("https://rethymus.github.io"),
  title: "Aionis — 反泄漏选股研究终端",
  description:
    "Anti-leakage stock-pick research terminal: stock-pick ranking, evidence wall, and power-floor monitor. Null is the intended outcome.",
  openGraph: {
    title: "Aionis — 反泄漏选股研究终端",
    description:
      "Anti-leakage stock-pick research terminal. Personal research · non-investment advice.",
    type: "website",
    url: "https://rethymus.github.io/Aionis/",
  },
  twitter: {
    card: "summary_large_image",
    title: "Aionis — 反泄漏选股研究终端",
    description: "Anti-leakage stock-pick research terminal.",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="zh-CN"
      className={`${geist.variable} h-full antialiased font-sans`}
      suppressHydrationWarning
    >
      <body className="min-h-full flex flex-col">
        <ThemeProvider
          attribute="class"
          defaultTheme="dark"
          enableSystem
          disableTransitionOnChange
        >
          <I18nProvider>
            <TooltipProvider>{children}</TooltipProvider>
          </I18nProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
