"use client";

// Reveal — Apple-style scroll entrance for section-level blocks.
//
// Wraps children in a container that fades in and rises 10px the first time
// it enters the viewport (IntersectionObserver, fires once). Above the fold
// at mount -> revealed immediately with no animation (content is never
// hidden from users who land mid-page: observer still fires for in-view
// nodes). `prefers-reduced-motion: reduce` renders everything instantly.
//
// Motion discipline: opacity + transform only (compositor path), 500ms
// ease-out — no layout properties animated, no scroll listeners.

import { useEffect, useRef, useState, type ReactNode } from "react";

export function Reveal({
  children,
  delay = 0,
  className = "",
}: {
  children: ReactNode;
  /** Stagger delay in ms (optional, for sibling rhythm). */
  delay?: number;
  className?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [shown, setShown] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setShown(true);
      return;
    }
    const io = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          if (e.isIntersecting) {
            setShown(true);
            io.disconnect();
          }
        }
      },
      { rootMargin: "0px 0px -8% 0px" },
    );
    io.observe(el);
    return () => io.disconnect();
  }, []);

  return (
    <div
      ref={ref}
      className={className}
      style={{
        opacity: shown ? 1 : 0,
        transform: shown ? "translateY(0)" : "translateY(10px)",
        transition: `opacity 0.5s cubic-bezier(0.22, 0.61, 0.36, 1) ${delay}ms, transform 0.5s cubic-bezier(0.22, 0.61, 0.36, 1) ${delay}ms`,
      }}
    >
      {children}
    </div>
  );
}
