import type { MetadataRoute } from "next";

// Web app manifest (round 177): makes the terminal installable as a PWA —
// proper app name, theme color matching the dark-first design, and the
// existing SVG icon. Next static export supports manifest.ts natively.
//
// output: "export" requires route handlers to opt into static generation.
export const dynamic = "force-static";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Aionis — 反泄漏选股研究终端",
    short_name: "Aionis",
    description:
      "Anti-leakage stock-pick research terminal: frozen OOS picks, evidence wall, and power-floor monitor.",
    start_url: "/Aionis/dashboard",
    display: "standalone",
    background_color: "#0a0a0a",
    theme_color: "#00ca50",
    icons: [
      {
        src: "/Aionis/icon.svg",
        sizes: "any",
        type: "image/svg+xml",
        purpose: "any",
      },
    ],
  };
}
