import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Static export → GitHub Pages (served from /Aionis/).
  output: "export",
  basePath: "/Aionis",
  images: { unoptimized: true },
};

export default nextConfig;
