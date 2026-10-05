#!/usr/bin/env node
/**
 * i18n orphan-key audit (static, conservative).
 *
 * Usage:  node scripts/i18n-audit.mjs            # stdout summary + writes i18n-audit-report.json
 *         node scripts/i18n-audit.mjs --ci       # gate mode: exit 1 on confirmed orphans or asymmetry
 *
 * Method (deliberately over-preserving — fewer "confirmed orphans" beats false positives):
 *   1. Parse src/i18n/dict.ts zh/en blocks (4-space indent + double-quoted "key": "value").
 *      DictKey = keyof typeof dict["zh"], so zh is the canonical key universe.
 *   2. Collect reference evidence from ALL of src/**(.ts,.tsx,.mjs,.json) except dict.ts:
 *        - every double- or single-quoted string literal  -> exact set
 *          (covers t("k"), t('k'), prop-drilled labelKey:"k", Record<_,DictKey> maps, arrays)
 *        - every static segment of every backtick template -> exact set; a segment ending
 *          in "." additionally becomes a wildcard prefix (covers t(`prefix.${x}`))
 *        - any quoted literal ending in "." becomes a wildcard prefix
 *          (covers t("prefix." + x) concatenation)
 *   3. Classify:
 *        confirmed orphan : no exact hit AND no prefix hit
 *        suspicious       : prefix hit only (dynamic-composition candidates)
 *        asymmetric       : key exists in exactly one language block
 *
 * tsc is the final arbiter per deletion batch (DictKey literal checks); this scanner
 * only nominates candidates. Zero functional change: read-only over src.
 */
import { readFileSync, writeFileSync, readdirSync, statSync } from "node:fs";
import { join, relative, sep } from "node:path";
import { fileURLToPath } from "node:url";

const WEB_ROOT = join(fileURLToPath(import.meta.url), "..", "..");
const SRC_DIR = join(WEB_ROOT, "src");
// Round 201: runtime dictionaries live in per-language modules; dict.ts is the types hub.
const DICT_FILES = {
  zh: join(SRC_DIR, "i18n", "dict-zh.ts"),
  en: join(SRC_DIR, "i18n", "dict-en.ts"),
};
const REPORT_PATH = join(WEB_ROOT, "i18n-audit-report.json");

// ---------- dict.ts parsing ----------

/**
 * Parse ONE per-language dictionary module (round 201 layout): a single
 * top-level object whose entries are 4-space-indented double-quoted keys —
 * the exact entry shape of the old dual-block dict.ts, extracted verbatim.
 * Returns Map key -> { line }.
 */
function parseDictFile(text, lang) {
  const all = text.split("\n");
  const blocks = new Map();
  // Key lines: 4-space indent, double-quoted key, colon (values may be
  // strings, arrays, or line-wrapped continuations; non-key lines don't match).
  const entry = /^\s{4}"((?:[^"\\]|\\.)*)":\s*(?:"|'|\{|\[|$)/;
  for (let i = 0; i < all.length; i++) {
    const m = all[i].match(entry);
    if (m) {
      if (blocks.has(m[1])) {
        console.error(`[warn] duplicate key in ${lang}: ${m[1]} (line ${i + 1})`);
      }
      blocks.set(m[1], { line: i + 1 });
    }
  }
  return blocks;
}

// ---------- reference extraction ----------

function listFiles(dir, exts, out = []) {
  for (const name of readdirSync(dir)) {
    if (name === "node_modules" || name === ".next") continue;
    const p = join(dir, name);
    const st = statSync(p);
    if (st.isDirectory()) listFiles(p, exts, out);
    else if (exts.some((e) => name.endsWith(e))) out.push(p);
  }
  return out;
}

/** Extract string evidence from source text. Mutates given sets. */
function collectEvidence(text, relPath, exact, prefixes) {
  // Strip comments conservatively but keep structure: block comments, line comments,
  // JSX comments {/* ... */} (already covered by block-comment rule after { optional).
  let code = text
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/(^|[^:])\/\/[^\n]*/g, "$1");

  // Backtick templates first (avoid quote regexes eating template innards' quotes).
  code.replace(/`(?:[^`\\]|\\.)*`/g, (raw) => {
    const inner = raw.slice(1, -1);
    // Static segments around ${...} interpolation holes.
    const segs = inner.split(/\$\{[\s\S]*?\}/);
    for (const seg of segs) {
      if (!seg) continue;
      exact.add(seg);
      if (seg.endsWith(".")) prefixes.add(seg);
    }
    return raw; // keep original text for the quote pass below (no-op transform)
  });

  // Double-quoted then single-quoted single-line literals (with escape handling).
  const patterns = [/"(?:[^"\\\n]|\\.)*"/g, /'(?:[^'\\\n]|\\.)*'/g];
  for (const re of patterns) {
    code.replace(re, (raw) => {
      const inner = raw.slice(1, -1);
      const val = inner.replace(/\\(.)/g, "$1"); // minimal unescape
      exact.add(val);
      if (val.endsWith(".")) prefixes.add(val);
      return raw;
    });
  }
  void relPath;
}

// ---------- classification ----------

function classify(keys, exact, prefixes) {
  const confirmed = [];
  const suspicious = [];
  for (const key of keys.sort()) {
    if (exact.has(key)) continue;
    const hit = [...prefixes].find((p) => key.startsWith(p));
    if (hit) suspicious.push({ key, prefix: hit });
    else confirmed.push(key);
  }
  return { confirmed, suspicious };
}

// ---------- main ----------

const zh = parseDictFile(readFileSync(DICT_FILES.zh, "utf8"), "zh");
const en = parseDictFile(readFileSync(DICT_FILES.en, "utf8"), "en");

const exact = new Set();
const prefixes = new Set();
for (const f of listFiles(SRC_DIR, [".ts", ".tsx", ".mjs", ".json"])) {
  if (f === DICT_FILES.zh || f === DICT_FILES.en) {
    continue; // never treat the dictionaries as their own reference corpus
  }
  collectEvidence(readFileSync(f, "utf8"), relative(SRC_DIR, f), exact, prefixes);
}
void sep;

const zhKeys = [...zh.keys()];
const enKeys = [...en.keys()];
const universe = [...new Set([...zhKeys, ...enKeys])];
const { confirmed, suspicious } = classify(universe, exact, prefixes);

const asymExtraZh = zhKeys.filter((k) => !en.has(k));
const asymExtraEn = enKeys.filter((k) => !zh.has(k));

const report = {
  generatedAt: new Date().toISOString(),
  dictPaths: [relative(WEB_ROOT, DICT_FILES.zh), relative(WEB_ROOT, DICT_FILES.en)],
  corpusRoot: relative(WEB_ROOT, SRC_DIR),
  totals: { zhKeys: zhKeys.length, enKeys: enKeys.length, universe: universe.length },
  confirmedOrphans: confirmed,
  suspiciousPrefixOnly: suspicious,
  asymmetric: { zhOnly: asymExtraZh, enOnly: asymExtraEn },
};

writeFileSync(REPORT_PATH, JSON.stringify(report, null, 2) + "\n");

console.log(`dict: zh=${zhKeys.length} keys, en=${enKeys.length} keys`);
console.log(`corpus: ${SRC_DIR} (${exact.size} exact strings, ${prefixes.size} prefixes)`);
console.log("");
console.log(`confirmed orphans : ${confirmed.length}`);
if (confirmed.length) console.log(confirmed.map((k) => `  - ${k}`).join("\n"));
console.log(`suspicious (prefix-only): ${suspicious.length}`);
for (const s of suspicious) console.log(`  - ${s.key}  (prefix "${s.prefix}")`);
console.log(`asymmetric: zhOnly=${asymExtraZh.length}, enOnly=${asymExtraEn.length}`);
for (const k of asymExtraZh) console.log(`  zh-only: ${k}`);
for (const k of asymExtraEn) console.log(`  en-only: ${k}`);
console.log("");
if (process.argv.includes("--ci")) {
  const problems = [];
  if (confirmed.length) problems.push(`${confirmed.length} confirmed orphan key(s): ${confirmed.join(", ")}`);
  if (asymExtraZh.length) problems.push(`${asymExtraZh.length} zh-only key(s): ${asymExtraZh.join(", ")}`);
  if (asymExtraEn.length) problems.push(`${asymExtraEn.length} en-only key(s): ${asymExtraEn.join(", ")}`);
  if (problems.length) {
    console.error(`i18n gate FAILED:\n  - ${problems.join("\n  - ")}`);
    process.exit(1);
  }
  console.log("i18n gate PASSED (0 orphans, zh/en symmetric)");
}
console.log(`report written -> ${REPORT_PATH}`);
