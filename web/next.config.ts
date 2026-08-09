import type { NextConfig } from "next";

// GitHub Pages serves the static export from /Aionis/, so production keeps the
// basePath. `next dev` (NODE_ENV !== production) omits it so routes resolve at
// /dashboard etc. without the prefix — otherwise dev 404s on every page.
const isProd = process.env.NODE_ENV === "production";

const nextConfig: NextConfig = {
  // Static export → GitHub Pages (served from /Aionis/).
  output: "export",
  basePath: isProd ? "/Aionis" : undefined,
  images: { unoptimized: true },
};

export default nextConfig;
