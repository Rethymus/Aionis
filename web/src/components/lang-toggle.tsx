"use client";

import { useSyncExternalStore } from "react";
import { Button } from "@/components/ui/button";
import { useI18n } from "@/i18n/provider";

const emptySubscribe = () => () => {};
const useIsMounted = () =>
  useSyncExternalStore(emptySubscribe, () => true, () => false);

export function LangToggle() {
  const { lang, setLang } = useI18n();
  const mounted = useIsMounted();

  if (!mounted) {
    return (
      <Button variant="ghost" size="sm" className="h-8 px-2 text-xs">
        <span className="sr-only">Toggle language</span>
      </Button>
    );
  }

  const isZh = lang === "zh";

  return (
    <Button
      variant="ghost"
      size="sm"
      className="press h-8 gap-0 rounded-full px-2 text-xs font-semibold"
      onClick={() => setLang(isZh ? "en" : "zh")}
      aria-label="Toggle language"
    >
      <span className={isZh ? "text-foreground" : "text-muted-foreground"}>中</span>
      <span className="mx-0.5 text-muted-foreground">/</span>
      <span className={!isZh ? "text-foreground" : "text-muted-foreground"}>EN</span>
    </Button>
  );
}
