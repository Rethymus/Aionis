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
  /** Accessible label for the scroll region (optional). */
  label?: string;
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

  // --- iOS rubber-band damping at the scroll edges (2026-09 motion brief) --
  // When a wheel gesture pushes past an edge, the content follows the finger
  // with resistance (iOS applies ~0.33 of the delta) instead of stopping
  // dead, and springs back on release with the damped-spring easing. Skipped
  // under prefers-reduced-motion. The pin transform on <thead> keeps its
  // last native value during the pull, so the header rides the bounce too.
  const rubber = useRef(0);
  const contentRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = viewportRef.current;
    const content = contentRef.current;
    if (!el || !content) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    let releaseTimer: ReturnType<typeof setTimeout> | null = null;
    const springBack = () => {
      if (rubber.current === 0) return;
      content.style.transition = `transform 0.5s var(--ease-apple-spring, cubic-bezier(0.34, 1.24, 0.44, 1))`;
      content.style.transform = "translateY(0)";
      rubber.current = 0;
    };
    // VERIFIED iOS overscroll mapping (chpwn/originell gist; Flutter
    // BouncingScrollPhysics ports the same physics): the overscroll distance
    // is an asymptotic function of the finger distance — inherently damped,
    // no arbitrary cap needed. d = viewport dimension, c = 0.55.
    const d = el.clientHeight;
    const overscroll = (fingerPx: number) =>
      d * (1 - 1 / ((0.55 * Math.abs(fingerPx)) / d + 1));
    let finger = 0;
    const onWheel = (e: WheelEvent) => {
      const atTop = el.scrollTop <= 0;
      const atBottom = el.scrollTop >= el.scrollHeight - el.clientHeight - 1;
      const pullingUp = atTop && e.deltaY < 0;
      const pullingDown = atBottom && e.deltaY > 0;
      if (!pullingUp && !pullingDown) {
        if (rubber.current !== 0) springBack();
        return; // normal scrolling: native behavior untouched
      }
      e.preventDefault();
      wake();
      finger = Math.max(-240, Math.min(240, finger + e.deltaY));
      rubber.current = overscroll(finger) * Math.sign(finger);
      content.style.transition = "none";
      content.style.transform = `translateY(${-rubber.current}px)`;
      if (releaseTimer) clearTimeout(releaseTimer);
      releaseTimer = setTimeout(springBack, 90); // gesture pause -> spring back
    };
    el.addEventListener("wheel", onWheel, { passive: false });
    return () => {
      el.removeEventListener("wheel", onWheel);
      if (releaseTimer) clearTimeout(releaseTimer);
    };
  }, [wake]);

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
        {...(label ? { role: "region", "aria-label": label } : {})}
        onScroll={schedule}
        className="frost-scroll overflow-y-auto overscroll-contain rounded-md border border-border/60"
        style={{ maxHeight }}
      >
        <div ref={contentRef}>{children}</div>
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
          {...(label ? { "aria-label": label } : {})}
          aria-orientation="vertical"
          tabIndex={0}
          onPointerDown={onThumbPointerDown}
          onPointerMove={onThumbPointerMove}
          onPointerUp={onThumbPointerUp}
          className={`frost-thumb-pill absolute right-0.5 top-0 w-[7px] cursor-pointer rounded-full outline-none ${
            active ? "opacity-100" : "opacity-0"
          }`}
          style={{
            willChange: "transform",
            transition: `opacity 0.24s var(--ease-apple-snappy, var(--ease-apple-snappy-fb, ease-out))`,
          }}
        />
      ) : null}
    </div>
  );
}
