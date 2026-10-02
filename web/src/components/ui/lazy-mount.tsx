"use client";

// LazyMount — defer a below-fold subtree's MOUNT until near-viewport.
//
// Why not plain content-visibility: the round-113 measurement showed cv skips
// layout/paint but NOT React hydration — the market page's cost center was
// react-dom hydrating five recharts cards (4.68s in the framework chunk).
// LazyMount with a dynamic(ssr:false) child keeps the subtree out of the
// initial hydration entirely; React mounts it when the user approaches.
//
// The placeholder carries the caller's minHeight so the scrollbar and layout
// stay stable (CLS discipline: this repo measures 0 and keeps it there).
// `prefers-reduced-motion` users still get lazy mounting (energy), only the
// eventual reveal is instant — IO fires identically.
//
// Round 114 pairing rule: the child should be a `next/dynamic(..., {ssr:false})`
// component — SSR renders only the placeholder, so hydration cannot mismatch
// and the card's code evaluates on approach, not at boot.

import { useEffect, useRef, useState, type ReactNode } from "react";

export function LazyMount({
  children,
  minHeight,
  rootMargin = "400px",
  className = "",
}: {
  children: ReactNode;
  /** Placeholder height in px — approximate the real card, protect CLS. */
  minHeight: number;
  /** Start mounting this far before the element enters the viewport. */
  rootMargin?: string;
  className?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (typeof IntersectionObserver === "undefined") {
      setVisible(true); // ancient engine: mount everything, correctness first
      return;
    }
    const io = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          if (e.isIntersecting) {
            setVisible(true);
            io.disconnect();
          }
        }
      },
      { rootMargin: `${rootMargin} 0px ${rootMargin} 0px` },
    );
    io.observe(el);
    return () => io.disconnect();
  }, [rootMargin]);

  return (
    <div ref={ref} className={className}>
      {visible ? (
        children
      ) : (
        <div
          aria-hidden="true"
          style={{ minHeight }}
          className="w-full animate-pulse rounded-xl border border-line bg-soft/50"
        />
      )}
    </div>
  );
}
