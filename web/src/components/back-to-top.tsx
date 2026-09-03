"use client";

import { useEffect, useRef, useState } from "react";
import { ArrowUpIcon } from "lucide-react";
import { useI18n } from "@/i18n/provider";

// Back-to-top affordance for the deep hub pages (picks tab alone is ~10
// screens). Appears only after the user has scrolled 600px, so it never adds
// noise above the fold. 44px target per touch-ergonomics guidance.
//
// 2026-09 motion pass: the button stays MOUNTED and animates in/out
// (opacity + scale + rise, Apple popover easing) instead of popping between
// null renders; the scroll listener is rAF-throttled and only flips state at
// the threshold crossing (no per-scroll-event re-renders). Reduced motion
// collapses the transitions.
export function BackToTop() {
  const { t } = useI18n();
  const [show, setShow] = useState(false);
  const raf = useRef(0);

  useEffect(() => {
    let last = false;
    const onScroll = () => {
      if (raf.current) return;
      raf.current = requestAnimationFrame(() => {
        raf.current = 0;
        const next = window.scrollY > 600;
        if (next !== last) {
          last = next;
          setShow(next);
        }
      });
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => {
      window.removeEventListener("scroll", onScroll);
      if (raf.current) cancelAnimationFrame(raf.current);
    };
  }, []);

  return (
    <button
      type="button"
      aria-label={t("common.back_to_top")}
      title={t("common.back_to_top")}
      aria-hidden={!show}
      tabIndex={show ? 0 : -1}
      onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
      className="press frost-glass fixed right-5 bottom-5 z-40 flex size-11 items-center justify-center rounded-full border bg-background/70 text-foreground shadow-md backdrop-blur-md hover:bg-muted"
      style={{
        opacity: show ? 1 : 0,
        transform: show ? "translateY(0) scale(1)" : "translateY(10px) scale(0.9)",
        pointerEvents: show ? "auto" : "none",
        transition: `opacity 0.3s var(--ease-apple-smooth, var(--ease-apple-smooth-fb, ease-out)), transform 0.42s var(--ease-apple-spring, var(--ease-apple-spring-fb, ease-out)), background-color 0.2s ease`,
      }}
    >
      <ArrowUpIcon className="size-4" />
    </button>
  );
}
