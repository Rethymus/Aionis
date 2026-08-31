// Circular name-initials avatar (reference alignment P1): the reference site
// leads every stream row (insider / politician / filer names) with a small
// muted circle carrying the name's initials — a visual anchor so rows scan by
// person, not by date. Purely decorative identity chrome: bg-muted /
// text-muted-foreground project tokens (never hardcoded colors), and the
// full name stays in the row text + title/aria so the avatar adds no
// information of its own.

import { cn } from "@/lib/utils";

/** English-person initials: first letter of the first word + first letter of
 *  the last word ("Althoff Judson" → "AJ", "Morrison, Hon. Kelly Louise" →
 *  "ML"), always uppercase, ≤2 letters; a single word keeps its first letter;
 *  an empty name renders the honest em-dash glyph (never a guessed letter). */
export function nameInitials(name: string): string {
  const words = name.trim().split(/\s+/).filter(Boolean);
  if (words.length === 0) return "—";
  if (words.length === 1) return words[0].slice(0, 1).toUpperCase();
  return (words[0][0] + words[words.length - 1][0]).toUpperCase();
}

/** size-7 circle (leading-7 centers the single line without flex). */
export function AvatarInitials({
  name,
  className,
}: {
  name: string;
  className?: string;
}) {
  return (
    <span
      aria-hidden="true"
      title={name}
      className={cn(
        "size-7 shrink-0 rounded-full bg-muted text-center text-[11px] font-semibold leading-7 text-muted-foreground",
        className,
      )}
    >
      {nameInitials(name)}
    </span>
  );
}
