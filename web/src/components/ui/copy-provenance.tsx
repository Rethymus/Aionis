"use client";

// CopyProvenance (round 161): a compact button that copies a markdown
// citation for the current page's data provenance to the clipboard.
// This turns the anti-leakage trust chain into shareable social currency:
// "here's my data, here's the frozen config that produced it, here's the
// ledger row you can audit."

import { useState } from "react";
import { CheckIcon, CopyIcon } from "lucide-react";
import { cn } from "@/lib/utils";

export function CopyProvenance({
  citation,
  className,
}: {
  /** Pre-formatted markdown citation string. */
  citation: string;
  className?: string;
}) {
  const [copied, setCopied] = useState(false);

  const onCopy = async () => {
    try {
      await navigator.clipboard.writeText(citation);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // clipboard API unavailable (http, permissions) — silently fail
    }
  };

  return (
    <button
      type="button"
      onClick={onCopy}
      aria-label="Copy provenance citation"
      className={cn(
        "inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-[11px] font-mono transition-colors",
        "text-muted-foreground hover:bg-soft hover:text-foreground",
        copied && "text-emerald-600 dark:text-emerald-400",
        className,
      )}
    >
      {copied ? (
        <CheckIcon className="size-3" />
      ) : (
        <CopyIcon className="size-3" />
      )}
      {copied ? "Copied" : "Cite"}
    </button>
  );
}
