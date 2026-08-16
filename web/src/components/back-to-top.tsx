"use client";

import { useEffect, useState } from "react";
import { ArrowUpIcon } from "lucide-react";
import { useI18n } from "@/i18n/provider";

// Back-to-top affordance for the deep hub pages (picks tab alone is ~10
// screens). Appears only after the user has scrolled 600px, so it never adds
// noise above the fold. 44px target per touch-ergonomics guidance.
export function BackToTop() {
  const { t } = useI18n();
  const [show, setShow] = useState(false);

  useEffect(() => {
    const onScroll = () => setShow(window.scrollY > 600);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  if (!show) return null;

  return (
    <button
      type="button"
      aria-label={t("common.back_to_top")}
      title={t("common.back_to_top")}
      onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
      className="fixed right-5 bottom-5 z-40 flex size-11 items-center justify-center rounded-full border bg-background/95 text-foreground shadow-md backdrop-blur transition-colors hover:bg-muted"
    >
      <ArrowUpIcon className="size-4" />
    </button>
  );
}
