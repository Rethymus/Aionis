import type { MetadataRoute } from "next";

// output: "export" requires route handlers to opt into static generation.
export const dynamic = "force-static";

// Served at /Aionis/robots.txt. On a github.io project subpath crawlers only
// honor robots.txt at the DOMAIN root (not ours), so this file is advisory
// today and becomes authoritative the day the site moves to a custom domain.
// It stays tiny and correct rather than empty: allow content, keep the JSON
// panel mirror out of crawl budgets, and point at the sitemap's canonical URL.
export default function robots(): MetadataRoute.Robots {
  return {
    rules: [{ userAgent: "*", allow: "/", disallow: "/api/" }],
    sitemap: "https://rethymus.github.io/Aionis/sitemap.xml",
  };
}
