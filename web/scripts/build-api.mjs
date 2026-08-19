// Mirrors the committed panel JSONs (web/src/data/aionis/) into
// web/public/api/v1/ at build time, producing the deployable static data API:
//
//   /api/v1/catalog.json          — machine-readable index (license/source/freshness)
//   /api/v1/health.json           — freshness/provenance map (data_health panel)
//   /api/v1/panels/<panel>.json   — the 27 panel payloads, verbatim
//   /api/v1/openapi.json          — OpenAPI 3.1 document for the whole surface
//
// Imitation of the xiaoyinsi datahub discipline (per its /api-docs): a
// documented data platform with per-path status/license metadata. Aionis's
// twist: the license annotations ARE the 7-gate intake facts, and the API is
// served straight from GitHub Pages (read-only, no auth, no server).
//
// Runs as `prebuild` (see package.json). Output is a build artifact —
// gitignored (public/api/) and regenerated on every CI/local build, so the
// deployed API can never drift from the panels the terminal renders.

import { copyFile, mkdir, readdir, readFile, writeFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const SRC = path.join(root, "src", "data", "aionis");
const OUT = path.join(root, "public", "api", "v1");
const PANELS_OUT = path.join(OUT, "panels");

const BASE_PATH = "/Aionis";
const DEPLOY_SERVER = "https://rethymus.github.io/Aionis";
const WORKER_SERVER = "https://api.aionis-prices.workers.dev";

const catalog = JSON.parse(await readFile(path.join(SRC, "api_catalog.json"), "utf8"));
const health = JSON.parse(await readFile(path.join(SRC, "data_health.json"), "utf8"));

await mkdir(PANELS_OUT, { recursive: true });

// 1. Panel payloads, verbatim.
const jsonFiles = (await readdir(SRC)).filter((f) => f.endsWith(".json"));
let n = 0;
for (const f of jsonFiles) {
  await copyFile(path.join(SRC, f), path.join(PANELS_OUT, f));
  n += 1;
}

// 2. Health + catalog at the API root.
await copyFile(path.join(SRC, "data_health.json"), path.join(OUT, "health.json"));
await copyFile(path.join(SRC, "api_catalog.json"), path.join(OUT, "catalog.json"));

// 3. OpenAPI 3.1 document assembled from the catalog (single source of truth).
const panelParams = catalog.endpoints.map((e) => ({
  name: e.file.replace(/\.json$/, ""),
  summary: `${e.key} — ${e.freshness} · ${e.license}`,
  "x-aionis-freshness": e.freshness,
  "x-aionis-license": e.license,
  "x-aionis-source": e.source,
  "x-aionis-as-of": e.as_of,
}));

const spec = {
  openapi: "3.1.0",
  info: {
    title: "Aionis Terminal Data API",
    version: "1.0.0",
    summary:
      "Read-only static JSON contract over the Aionis terminal panels, served from GitHub Pages.",
    description: [
      catalog.base_note,
      "",
      catalog.methodology,
    ].join("\n"),
  },
  servers: [
    { url: DEPLOY_SERVER, description: "GitHub Pages deployment (panels, catalog, health)" },
    { url: WORKER_SERVER, description: "Live-prices Cloudflare Worker (display-only)" },
  ],
  paths: {
    "/api/v1/catalog.json": {
      get: {
        summary: "Panel catalog — license / source / freshness for every endpoint",
        "x-aionis-status": "available",
        responses: {
          "200": { description: "Catalog object", content: { "application/json": { schema: { type: "object" } } } },
        },
      },
    },
    "/api/v1/health.json": {
      get: {
        summary: "Freshness/provenance map of all panels (daily / cadence / frozen)",
        "x-aionis-status": "available",
        responses: {
          "200": { description: "Data-health object", content: { "application/json": { schema: { type: "object" } } } },
        },
      },
    },
    "/api/v1/panels/{panel}": {
      get: {
        summary: "Panel payload, verbatim (the same JSON the terminal renders)",
        "x-aionis-status": "available",
        parameters: panelParams,
        responses: {
          "200": { description: "Panel JSON", content: { "application/json": { schema: { type: "object" } } } },
          "404": { description: "Unknown panel key" },
        },
      },
    },
    "/api/prices/{region}": {
      get: {
        summary: "Live quotes (display-only; never enters the research pipeline)",
        "x-aionis-status": "available",
        "x-aionis-license": "Tiingo/Alpaca free tier (vendor ToS, display-only)",
        parameters: [
          { name: "region", in: "path", required: true, schema: { type: "string", enum: ["us", "cn"] } },
          { name: "tickers", in: "query", required: true, schema: { type: "string" }, description: "Comma-separated tickers" },
        ],
        responses: {
          "200": { description: "Quote map", content: { "application/json": { schema: { type: "object" } } } },
        },
      },
    },
  },
};

await writeFile(path.join(OUT, "openapi.json"), JSON.stringify(spec, null, 2));

// 4. Human-facing README at the API root (curl-able entry point).
const readme = [
  "# Aionis Terminal Data API (v1)",
  "",
  catalog.base_note,
  "",
  "## Endpoints",
  `- catalog:      ${BASE_PATH}/api/v1/catalog.json`,
  `- health:       ${BASE_PATH}/api/v1/panels/data_health.json`,
  `- openapi:      ${BASE_PATH}/api/v1/openapi.json`,
  `- panel (n=${n}): ${BASE_PATH}/api/v1/panels/<key>.json`,
  `- live prices:  ${WORKER_SERVER}/api/prices/{us|cn}?tickers=...`,
  "",
  "Frozen endpoints deliberately do NOT advance (anti-leakage contract);",
  "see the catalog's freshness field before expecting updates.",
  "",
].join("\n");
await writeFile(path.join(OUT, "README.md"), readme);

if (!existsSync(path.join(OUT, "openapi.json"))) {
  throw new Error("openapi.json missing after write");
}
console.log(`[build-api] mirrored ${n} panels + catalog + health + openapi to public/api/v1/`);
