"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useI18n } from "@/i18n/provider";
import { aionis } from "@/data/aionis";
import { ClockIcon, ShieldCheckIcon } from "lucide-react";

export function RedditView() {
  const { t } = useI18n();
  const r = aionis.reddit;

  return (
    <div className="space-y-6 p-4 md:p-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-bold tracking-tight">{t("reddit.title")}</h1>
        <p className="text-sm text-muted-foreground">{t("reddit.window")}</p>
      </header>

      <Card className="border-amber-500/30 bg-amber-500/5">
        <CardContent className="space-y-2 p-4">
          <div className="flex items-center gap-2">
            <ClockIcon className="size-4 text-amber-600 dark:text-amber-400" />
            <Badge
              variant="outline"
              className="border-amber-500/40 bg-amber-500/10 text-amber-700 dark:text-amber-400"
            >
              {t("reddit.status.awaiting")}
            </Badge>
          </div>
          <p className="font-mono text-xs">{r.collector}</p>
          <p className="text-xs text-muted-foreground">{r.mode}</p>
        </CardContent>
      </Card>

      <p className="text-sm text-muted-foreground">{t("reddit.explain")}</p>

      <div className="flex flex-wrap gap-2">
        {r.subreddits.map((s) => (
          <Badge key={s} variant="secondary" className="font-mono">
            r/{s}
          </Badge>
        ))}
      </div>

      <Card>
        <CardHeader className="border-b">
          <CardTitle className="flex items-center gap-2 text-base">
            <ShieldCheckIcon className="size-4" /> {t("reddit.howto")}
          </CardTitle>
        </CardHeader>
        <CardContent className="p-4">
          <p className="text-xs text-muted-foreground">{t("reddit.howto.body")}</p>
        </CardContent>
      </Card>

      <Card className="border-dashed">
        <CardContent className="flex flex-col items-center justify-center gap-1 py-12 text-center">
          <p className="text-sm font-medium text-muted-foreground">
            {t("reddit.status.awaiting")}
          </p>
          <p className="text-xs text-muted-foreground/70">
            0 snapshots · {t("reddit.window")}
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
