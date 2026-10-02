import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";

// Deployed-terminal alignment: Geist + Geist Mono as the latin faces
// (self-hosted at build time via next/font; CJK falls back to the native
// system stack).
const geist = Geist({ subsets: ["latin"], variable: "--font-geist", display: "swap" });
const geistMono = Geist_Mono({ subsets: ["latin"], variable: "--font-geist-mono", display: "swap" });
// Moved from the (dashboard) group layout with the shell (round 116).
const colorConvScript = `try{if(localStorage.getItem("aionis-colorconv")==="cn"){document.documentElement.dataset.colorconv="cn"}}catch(e){}`;
import { ThemeProvider } from "next-themes";
import { ThemeFade } from "@/components/theme-fade";
import { TooltipProvider } from "@/components/ui/tooltip";
import { I18nProvider } from "@/i18n/provider";
import { BackToTop } from "@/components/back-to-top";
import { LiquidGlassFilter } from "@/components/liquid-glass-filter";
import { TopNav } from "@/components/top-nav";
import "./globals.css";

// Typography is the native system stack (SF Pro on Apple, Segoe UI elsewhere,
// PingFang/YaHei for CJK) defined in globals.css — the Apple signature, no
// webfont approximation, zero network font cost.

// Shell (round 116, root-landing brief option B): the nav/main/BackToTop rail
// moved up from the (dashboard) group layout so `/` — now a real page, not a
// redirect shell — gets the same chrome as every route (not-found included).

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
      className={`${geist.variable} ${geistMono.variable} h-full antialiased font-sans`}
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
            <ThemeFade />
            <TooltipProvider>
              {/* Pre-paint application of the saved up/down color convention
                  (same pattern next-themes uses for theme): ships inside the
                  prerendered HTML and runs before hydration, so a CN-convention
                  user never sees a green-up flash. */}
              {/* eslint-disable-next-line react/no-danger -- static pre-paint seed, no user input */}
              <script dangerouslySetInnerHTML={{ __html: colorConvScript }} />
              <div className="flex min-h-screen flex-col">
                <TopNav />
                {/* Chrome-path Liquid Glass lensing filter for the nav dropdown
                    (backdrop-filter: url(#liquid-glass-lens)); other browsers
                    keep the plain blur()/saturate() material from globals.css. */}
                <LiquidGlassFilter />
                {/* Aligned-site main rail: 1320px, px-5/py-8 (md:px-6). Sticky
                    descendants (hot-ticker strip) stay valid — no
                    overflow-hidden ancestor. */}
                <main className="mx-auto w-full max-w-[1320px] flex-1 px-5 py-8 md:px-6">
                  {children}
                </main>
                <BackToTop />
              </div>
            </TooltipProvider>
          </I18nProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
