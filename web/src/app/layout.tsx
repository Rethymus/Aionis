import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { ThemeProvider } from "next-themes";
import { TooltipProvider } from "@/components/ui/tooltip";
import { I18nProvider } from "@/i18n/provider";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  metadataBase: new URL("https://rethymus.github.io"),
  title: "Aionis — 反泄漏选股研究终端",
  description:
    "Anti-leakage stock-pick research terminal: stock-pick ranking, evidence wall, and power-floor monitor. Null is the intended, publishable outcome.",
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
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased font-sans`}
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
