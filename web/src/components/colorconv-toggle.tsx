"use client";

import { useCallback, useSyncExternalStore } from "react";
import { ArrowUpIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useI18n } from "@/i18n/provider";

// Up/down color-convention toggle. The terminal is dual-region (US + CN):
// the international convention colors up green / down rose, the A-share
// convention colors up red / down green. A single global convention (not
// per-region) keeps mixed-region pages readable one way. Persisted to
// localStorage and applied pre-paint by the inline script in the dashboard
// layout; the actual swap lives in globals.css ([data-colorconv="cn"]).

const STORAGE_KEY = "aionis-colorconv";
type Conv = "intl" | "cn";

const listeners = new Set<() => void>();
let conv: Conv = "intl";

// Client module eval happens after the pre-paint inline script, so a saved
// preference is already on <html> — seed the store from it (otherwise the
// first click would toggle from the wrong side).
if (
  typeof document !== "undefined" &&
  document.documentElement.dataset.colorconv === "cn"
) {
  conv = "cn";
}

function subscribe(cb: () => void) {
  listeners.add(cb);
  return () => listeners.delete(cb);
}

function currentConv(): Conv {
  return conv;
}

function apply(next: Conv) {
  conv = next;
  if (typeof document !== "undefined") {
    if (next === "cn") {
      document.documentElement.dataset.colorconv = "cn";
    } else {
      delete document.documentElement.dataset.colorconv;
    }
  }
  localStorage.setItem(STORAGE_KEY, next);
  for (const cb of listeners) cb();
}

const emptySubscribe = () => () => {};
const useIsMounted = () =>
  useSyncExternalStore(emptySubscribe, () => true, () => false);

export function ColorConvToggle() {
  const { t } = useI18n();
  const value = useSyncExternalStore(subscribe, currentConv, () => "intl" as Conv);
  const mounted = useIsMounted();

  const onClick = useCallback(() => {
    apply(value === "cn" ? "intl" : "cn");
  }, [value]);

  const isCn = value === "cn";

  return (
    <Button
      variant="ghost"
      size="sm"
      className="press h-8 gap-1 rounded-full px-2 text-xs font-semibold"
      onClick={onClick}
      aria-label={t("colorconv.aria")}
      title={t("colorconv.hint")}
    >
      {mounted ? (
        <>
          {/* Live preview: the arrow shows the ACTIVE convention's up color. */}
          <ArrowUpIcon className="size-3 text-up" />
          <span className={isCn ? "text-foreground" : "text-muted-foreground"}>
            {t("colorconv.red")}
          </span>
          <span className="mx-0.5 text-muted-foreground">/</span>
          <span className={!isCn ? "text-foreground" : "text-muted-foreground"}>
            {t("colorconv.green")}
          </span>
        </>
      ) : (
        <span className="sr-only">{t("colorconv.aria")}</span>
      )}
    </Button>
  );
}
