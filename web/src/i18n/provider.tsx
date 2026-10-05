"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { zh } from "./dict-zh";
import type { DictKey, Lang } from "./dict";

type I18nContextValue = {
  lang: Lang;
  setLang: (lang: Lang) => void;
  t: (key: DictKey) => string;
};

const I18nContext = createContext<I18nContextValue | null>(null);

const STORAGE_KEY = "aionis-lang";

// Round 201: the English table is a dynamic import — the every-route chunk
// carries the (SSR-default) Chinese table only. First switch/download has a
// brief zh-rendered moment; the chunk is browser-cached afterwards.
let enPromise: Promise<typeof import("./dict-en")> | null = null;
function loadEn() {
  enPromise ??= import("./dict-en");
  return enPromise;
}

export function I18nProvider({ children }: { children: React.ReactNode }) {
  const [lang, setLangState] = useState<Lang>("zh");
  const [table, setTable] = useState<Record<DictKey, string>>(zh);

  useEffect(() => {
    // SSR-safe localStorage hydration: the prerendered HTML must stay
    // deterministic ("zh"), so the saved language can only be applied after
    // mount — the setState-in-effect here is the intended pattern.
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved === "en") {
      setLangState(saved);
      void loadEn().then((m) => {
        setTable(m.en);
      });
    } else if (saved === "zh") {
      setLangState(saved);
    }
  }, []);

  const setLang = (next: Lang) => {
    setLangState(next);
    localStorage.setItem(STORAGE_KEY, next);
    if (next === "en") {
      void loadEn().then((m) => setTable(m.en));
    } else {
      setTable(zh);
    }
  };

  const t = (key: DictKey) => table[key] ?? key;

  return (
    <I18nContext.Provider value={{ lang, setLang, t }}>
      {children}
    </I18nContext.Provider>
  );
}

export function useI18n() {
  const ctx = useContext(I18nContext);
  if (!ctx) {
    throw new Error("useI18n must be used within I18nProvider");
  }
  return ctx;
}
