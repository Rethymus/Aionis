// Sitemap ↔ exported pages parity gate (round 188).
//
// Runs AFTER `next build` in CI: every URL in out/sitemap.xml must resolve to
// an exported .html page — a dangling sitemap entry hands crawlers a 404. Two
// exclusions are by design:
//   - _not-found.html — the error page, never a sitemap entry;
//   - index.html — round 144 canonical fold: "/" renders dashboard.html's
//     content and the sitemap lists the canonical URL only. It is therefore
//     allowed to be exported without a sitemap entry.
//
// Usage: node scripts/sitemap-parity.mjs   (from web/, with out/ present)

import { readdir } from "node:fs/promises";
import { readFileSync, existsSync } from "node:fs";
import { join, relative, sep } from "node:path";

const OUT = "out";
const BASE = "https://rethymus.github.io/Aionis/";

if (!existsSync(join(OUT, "sitemap.xml"))) {
  console.error("::error::out/sitemap.xml missing — run after `next build`");
  process.exit(1);
}

const xml = readFileSync(join(OUT, "sitemap.xml"), "utf8");
const urls = new Set();
for (const m of xml.matchAll(/<loc>([^<]+)<\/loc>/g)) {
  urls.add(m[1].replace(BASE, ""));
}

const htmlFiles = new Set();
async function walk(dir) {
  for (const ent of await readdir(dir, { withFileTypes: true })) {
    const p = join(dir, ent.name);
    if (ent.isDirectory()) await walk(p);
    else if (ent.name.endsWith(".html")) {
      htmlFiles.add(relative(OUT, p).split(sep).join("/"));
    }
  }
}
await walk(OUT);
htmlFiles.delete("_not-found.html");

const dangling = [...urls].filter((u) => !htmlFiles.has(u)).sort();
if (dangling.length > 0) {
  console.error(
    `::error::${dangling.length} sitemap URL(s) have no exported page:`,
  );
  for (const u of dangling) console.error(`  ${u}`);
  process.exit(1);
}

console.log(
  `sitemap parity OK: ${urls.size} URLs all resolve ` +
    `(${htmlFiles.size} exported pages; index.html excluded by the ` +
    `round-144 canonical fold)`,
);
