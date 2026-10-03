"use client";

// Watchlist store — client-side localStorage set of ticker strings.
// Purely a display-layer convenience: zero server state, zero research-data
// contact (the tickers referenced here are already committed panel rows).
//
// Patterns follow colorconv-toggle (module store + listeners +
// localStorage + pre-hydration seed guard). The store is lazily loaded on
// first client access; the server snapshot is always empty so SSR HTML
// renders unstarred, and consumer components MUST gate the watched styling
// behind a mounted check to avoid hydration mismatch (the round-136 lesson:
// verify with a static-build probe, not just dev).

import { useCallback, useSyncExternalStore } from "react";

const STORAGE_KEY = "aionis-watchlist";
const listeners = new Set<() => void>();
let watched: Set<string> = new Set();
let loaded = false;

function load() {
  if (loaded || typeof window === "undefined") return;
  try {
    watched = new Set(JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]"));
  } catch {
    watched = new Set();
  }
  loaded = true;
}

function persist() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify([...watched]));
  } catch {
    // storage full / private mode — in-memory only, silently degrade
  }
}

function subscribe(cb: () => void) {
  listeners.add(cb);
  return () => {
    listeners.delete(cb);
  };
}

// String snapshot (sorted for referential stability across reads).
function getSnapshot(): string {
  load();
  return [...watched].sort().join(",");
}

function getServerSnapshot(): string {
  return "";
}

export function useWatchlist() {
  const snapshot = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
  const set = new Set(snapshot ? snapshot.split(",") : []);

  const toggle = useCallback((ticker: string) => {
    load();
    if (watched.has(ticker)) watched.delete(ticker);
    else watched.add(ticker);
    persist();
    for (const cb of listeners) cb();
  }, []);

  const isWatched = useCallback((ticker: string) => set.has(ticker), [set]);

  return { watched: set, toggle, isWatched, count: set.size };
}
