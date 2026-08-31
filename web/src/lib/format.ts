// Shared display-format layer (reference alignment P0-1). One place for the
// terminal's number/date/empty conventions so stream views stop scattering
// toFixed/toLocaleString/ISO-passthrough:
//   money  → US-style $T/$B/$M/$K (never 亿/万), 1-2 decimals
//   counts → thousands separators
//   dates  → short MM/DD in stream rows; ISO stays for report periods/as_of
//   empty  → "—" (never blank cells)

/** Money with US magnitude suffix. Whole-dollar 13F values, per-ticker
 *  prices, delta values — all share this single convention. */
export function fmtUsd(v: number | null | undefined): string {
  if (v == null || Number.isNaN(v)) return "—";
  const a = Math.abs(v);
  if (a >= 1e12) return `$${(v / 1e12).toFixed(2)}T`;
  if (a >= 1e9) return `$${(v / 1e9).toFixed(1)}B`;
  if (a >= 1e6) return `$${(v / 1e6).toFixed(1)}M`;
  if (a >= 1e3) return `$${(v / 1e3).toFixed(0)}K`;
  return `$${v.toFixed(0)}`;
}

/** Share counts with magnitude suffix (no $ prefix). */
export function fmtShares(v: number | null | undefined): string {
  if (v == null || Number.isNaN(v)) return "—";
  const a = Math.abs(v);
  if (a >= 1e9) return `${(v / 1e9).toFixed(2)}B`;
  if (a >= 1e6) return `${(v / 1e6).toFixed(1)}M`;
  if (a >= 1e3) return `${(v / 1e3).toFixed(0)}K`;
  return `${v.toFixed(0)}`;
}

/** Integer counts with locale thousands separators. */
export function fmtInt(v: number | null | undefined): string {
  if (v == null || Number.isNaN(v)) return "—";
  return v.toLocaleString("en-US");
}

/** Short stream-row date: ISO "2026-08-21" → "08/21" (reference P6). Invalid
 *  or missing input renders honestly as the raw value / em-dash. */
export function fmtDateShort(iso: string | null | undefined): string {
  if (!iso) return "—";
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso);
  if (!m) return iso;
  return `${m[2]}/${m[3]}`;
}

/** The single empty-value glyph for tables and stats. */
export function fmtEmpty<T>(v: T | null | undefined, fallback: string = "—"): string {
  return v == null || v === "" ? fallback : String(v);
}
