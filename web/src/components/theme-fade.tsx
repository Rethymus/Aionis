"use client";

// ThemeFade — Apple-Settings-style theme-switch crossfade.
//
// next-themes flips the `.dark` class on <html> instantly; this component
// watches for that flip with a MutationObserver and applies `.theme-fade`
// to the document element for ~400ms, letting every background/color/
// border/fill transition glide (the CSS in globals.css carries the rules).
//
// Skipped entirely when the user prefers reduced motion (the snap IS the
// reduced-motion behavior). The observer is cheap: it fires twice per theme
// toggle and does nothing otherwise.

import { useEffect } from "react";

export function ThemeFade() {
  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    let timer: ReturnType<typeof setTimeout> | null = null;
    let previous = document.documentElement.classList.contains("dark");

    const observer = new MutationObserver(() => {
      const now = document.documentElement.classList.contains("dark");
      if (now === previous) return; // irrelevant class mutations
      previous = now;
      document.documentElement.classList.add("theme-fade");
      if (timer) clearTimeout(timer);
      timer = setTimeout(() => {
        document.documentElement.classList.remove("theme-fade");
        timer = null;
      }, 400);
    });

    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["class"],
    });
    return () => {
      observer.disconnect();
      if (timer) clearTimeout(timer);
    };
  }, []);

  return null;
}
