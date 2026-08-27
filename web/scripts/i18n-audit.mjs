#!/usr/bin/env node
/**
 * i18n orphan-key audit (static, conservative).
 *
 * Usage:  node scripts/i18n-audit.mjs            # stdout summary + writes i18n-audit-report.json
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
const DICT_PATH = join(SRC_DIR, "i18n", "dict.ts");
const REPORT_PATH = join(WEB_ROOT, "i18n-audit-report.json");

// ---------- dict.ts parsing ----------

/** Parse the zh and en blocks of dict.ts. Returns { zh: Map, en: Map } key -> { line }. */
function parseDict(text) {
  const lines = text.split("\n");
  const blocks = { zh: new Map(), en: new Map() };
  let current = null;
  const blockOpen = /^  (zh|en): \{\s*$/; // 2-space indent object literal opens
  // Inside a block, entries look like: 4-space indent, double-quoted key, colon, string value.
  const entry = /^\s{4}"((?:[^"\\]|\\.)*)":\s*(?:"|)/;
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const open = line.match(blockOpen);
    if (open) {
      current = open[1];
      continue;
    }
    if (current && /^  \},?\s*$/.test(line)) {
      current = null; // block closed
      continue;
    }
    if (!current) continue;
    const m = line.match(entry);
    if (m) {
      const key = m[1];
      if (blocks[current].has(key)) {
        console.error(`[warn] duplicate key in ${current} block: ${key} (line ${i + 1})`);
      }
      blocks[current].set(key, { line: i + 1 });
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

const dictText = readFileSync(DICT_PATH, "utf8");
const { zh, en } = parseDict(dictText);

const exact = new Set();
const prefixes = new Set();
for (const f of listFiles(SRC_DIR, [".ts", ".tsx", ".mjs", ".json"])) {
  if (f === DICT_PATH) continue; // never treat dict.ts as its own reference corpus
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
  dictPath: relative(WEB_ROOT, DICT_PATH),
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
console.log(`report written -> ${REPORT_PATH}`);
