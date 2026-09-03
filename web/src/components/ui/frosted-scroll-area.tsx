"use client";

// FrostedScrollArea — the project's Apple-style scroll viewport for long
// data tables (2026-09 visual pass).
//
// Design contract (owner brief): show a LIMITED number of rows by default,
// keep the rest reachable by dragging a scrollbar; scrollbars are HIDDEN by
// default project-wide; frosted-glass (backdrop-blur) cues; silky motion
// with zero jank.
//
// Mechanics:
//  * Native scrolling is preserved (wheel/touch/keyboard) — only the
//    visuals are replaced: the container hides its native scrollbar
//    (globals.css sets thin/transparent; here fully hidden) and we render
//    an overlay thumb that fades in on hover/scroll and out when idle.
//  * The thumb is a frosted pill (translucent + backdrop-blur) positioned
//    with transform: translateY and sized with height — compositor-only
//    updates from a rAF-throttled passive scroll listener: no layout
//    reads/writes in the hot path, no scroll-jank.
//  * Draggable (pointer capture) — dragging the thumb scrolls the content
//    1:1, with the pointer offset honored so it never "jumps".
//  * Frosted edge masks (gradient + backdrop-blur strips) hint at more
//    content above/below and hide themselves at the scroll extremes.
//  * prefers-reduced-motion: the fade transitions collapse to instant.

import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";

const THUMB_MIN_H = 36; // px — never a sliver (Apple minimum-gesture size)
const IDLE_MS = 900; // thumb fades out after this much scroll inactivity

export function FrostedScrollArea({
  children,
  maxHeight = 380,
  label,
  className = "",
}: {
  children: ReactNode;
  /** Viewport height cap — bounds the visible row count. */
  maxHeight?: number;
  /** Accessible label for the scroll region. */
  label: string;
  className?: string;
}) {
  const viewportRef = useRef<HTMLDivElement>(null);
  const thumbRef = useRef<HTMLDivElement>(null);
  const rafRef = useRef(0);
  const idleTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const drag = useRef({ active: false, startY: 0, startTop: 0 });
  const [active, setActive] = useState(false); // thumb visible
  const [edge, setEdge] = useState({ top: false, bottom: false });
  const [scrollable, setScrollable] = useState(false);

  const sync = useCallback(() => {
    const el = viewportRef.current;
    if (!el) return;
    const { scrollTop, scrollHeight, clientHeight } = el;
    const canScroll = scrollHeight > clientHeight + 1;
    setScrollable(canScroll);
    setEdge({ top: scrollTop > 2, bottom: scrollTop < scrollHeight - clientHeight - 2 });
    // thumb styling is guarded separately: on the first post-hydration sync
    // the thumb is not mounted yet (it renders only once scrollable=true),
    // so an early return here would deadlock it out of the DOM.
    // pin the column header: JS transform instead of native position:sticky
    // (ancestor overflow:hidden from Card clipping hijacks sticky context)
    const thead = el.querySelector("thead");
    if (thead) thead.style.transform = `translateY(${Math.round(scrollTop)}px)`;
    const thumb = thumbRef.current;
    if (!canScroll || !thumb) return;
    const track = clientHeight;
    const th = Math.max(THUMB_MIN_H, (clientHeight / scrollHeight) * track);
    const maxTop = track - th;
    const top = (scrollTop / (scrollHeight - clientHeight)) * maxTop;
    thumb.style.height = `${th}px`;
    thumb.style.transform = `translateY(${top}px)`;
  }, []);

  // once the thumb/masks mount (scrollable flipped true), size the thumb —
  // the mount render has no inline geometry yet.
  useEffect(() => {
    if (scrollable) sync();
  }, [scrollable, sync]);

  const schedule = useCallback(() => {
    if (rafRef.current) return;
    rafRef.current = requestAnimationFrame(() => {
      rafRef.current = 0;
      sync();
    });
  }, [sync]);

  const wake = useCallback(() => {
    setActive(true);
    if (idleTimer.current) clearTimeout(idleTimer.current);
    idleTimer.current = setTimeout(() => setActive(false), IDLE_MS);
  }, []);

  useEffect(() => {
    const el = viewportRef.current;
    if (!el) return;
    sync();
    const onScroll = () => {
      wake();
      schedule();
    };
    el.addEventListener("scroll", onScroll, { passive: true });
    const ro = new ResizeObserver(() => schedule());
    ro.observe(el);
    return () => {
      el.removeEventListener("scroll", onScroll);
      ro.disconnect();
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      if (idleTimer.current) clearTimeout(idleTimer.current);
    };
  }, [schedule, sync, wake]);

  // --- thumb dragging (pointer capture; 1:1 with content, no jump) -------
  const onThumbPointerDown = (e: React.PointerEvent<HTMLDivElement>) => {
    const el = viewportRef.current;
    const thumb = thumbRef.current;
    if (!el || !thumb) return;
    e.preventDefault();
    const tr = thumb.getBoundingClientRect();
    drag.current = { active: true, startY: e.clientY, startTop: tr.top };
    thumb.setPointerCapture(e.pointerId);
    setActive(true);
  };
  const onThumbPointerMove = (e: React.PointerEvent<HTMLDivElement>) => {
    const el = viewportRef.current;
    if (!drag.current.active || !el) return;
    const { scrollHeight, clientHeight } = el;
    const track = clientHeight;
    const th = Math.max(THUMB_MIN_H, (clientHeight / scrollHeight) * track);
    const maxTop = track - th;
    const delta = e.clientY - drag.current.startY;
    const top = Math.max(0, Math.min(maxTop, drag.current.startTop + delta));
    el.scrollTop = (top / maxTop) * (scrollHeight - clientHeight);
  };
  const onThumbPointerUp = (e: React.PointerEvent<HTMLDivElement>) => {
    drag.current.active = false;
    e.currentTarget.releasePointerCapture(e.pointerId);
    wake();
  };

  return (
    <div
      className={`relative ${className}`}
      style={{ maxHeight }}
      onMouseEnter={wake}
      onMouseLeave={() => {
        if (!drag.current.active) setActive(false);
      }}
    >
      {/* viewport: native scrollbar hidden, native scroll behavior kept */}
      <div
        ref={viewportRef}
        role="region"
        aria-label={label}
        onScroll={schedule}
        className="frost-scroll overflow-y-auto overscroll-contain rounded-md border border-border/60"
        style={{ maxHeight }}
      >
        {children}
      </div>

      {/* frosted edge masks — blur + fade, hidden at the extremes */}
      {scrollable && edge.top ? (
        <div
          aria-hidden="true"
          className="frost-mask pointer-events-none absolute inset-x-0 top-0 h-8 rounded-t-md"
        />
      ) : null}
      {scrollable && edge.bottom ? (
        <div
          aria-hidden="true"
          className="frost-mask frost-mask-bottom pointer-events-none absolute inset-x-0 bottom-0 h-8 rounded-b-md"
        />
      ) : null}

      {/* overlay thumb — frosted pill, fades in on hover/scroll, draggable */}
      {scrollable ? (
        <div
          ref={thumbRef}
          role="scrollbar"
          aria-label={label}
          aria-orientation="vertical"
          tabIndex={0}
          onPointerDown={onThumbPointerDown}
          onPointerMove={onThumbPointerMove}
          onPointerUp={onThumbPointerUp}
          className={`frost-thumb-pill absolute right-0.5 top-0 w-[7px] cursor-pointer rounded-full outline-none transition-opacity duration-300 ${
            active ? "opacity-100" : "opacity-0"
          }`}
          style={{ willChange: "transform" }}
        />
      ) : null}
    </div>
  );
}
