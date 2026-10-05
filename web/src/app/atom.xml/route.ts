// Atom feed for the bilingual /news panel — the sitemap's companion for
// content discovery (round 181). Built at export time (force-static, same
// contract as sitemap.ts); entries are the exact news_feed.json items the
// /news page renders, newest-first as stored, with the upstream article URL
// as the entry link (the terminal is a display layer, not the publisher).
// Dates are the panel's own as_of / per-item seendate — no fabricated times.
import { aionis } from "@/data/aionis";

export const dynamic = "force-static";

const BASE = "https://rethymus.github.io/Aionis";
const FEED_URL = `${BASE}/atom.xml`;

function _esc(s: string): string {
  return s
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&apos;");
}

export function GET(): Response {
  const nf = aionis.newsFeed;
  const entries = nf.items
    .map((it) => {
      const cats = [
        `  <category term="${_esc(it.lang)}" />`,
        `  <category term="${_esc(it.domain)}" label="source" />`,
      ];
      if (it.sourcecountry) {
        cats.push(`  <category term="${_esc(it.sourcecountry)}" label="country" />`);
      }
      return [
        " <entry>",
        `  <title>${_esc(it.title)}</title>`,
        `  <id>${_esc(it.url)}</id>`,
        `  <link href="${_esc(it.url)}" rel="alternate" type="text/html" />`,
        `  <updated>${_esc(it.seendate)}</updated>`,
        ...cats,
        " </entry>",
      ].join("\n");
    })
    .join("\n");

  const xml = `<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
 <id>${FEED_URL}</id>
 <title>Aionis — Market News (EN/中文)</title>
 <subtitle>Bilingual GDELT-derived financial news window rendered by the Aionis display terminal. Research artifacts: ${BASE}/news.html</subtitle>
 <link href="${FEED_URL}" rel="self" type="application/atom+xml" />
 <link href="${BASE}/news.html" rel="alternate" type="text/html" />
 <updated>${_esc(nf.as_of)}</updated>
 <rights>Display layer; article content belongs to its upstream publishers.</rights>
${entries}
</feed>
`;

  return new Response(xml, {
    headers: {
      "Content-Type": "application/atom+xml; charset=utf-8",
      "Cache-Control": "public, max-age=3600",
    },
  });
}
