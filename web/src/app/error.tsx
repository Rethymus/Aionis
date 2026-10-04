"use client";

// Root error boundary (round 176): catches any UNCAUGHT client render error
// across all 1500+ pages. Without this, a runtime error shows Next's default
// crash page with no recovery path — this gives the user a graceful card
// with a reload button and a path back to the dashboard.

import Link from "next/link";
import { AlertTriangleIcon, RotateCcwIcon } from "lucide-react";

export default function Error({
  error,
}: {
  error: Error & { digest?: string };
}) {
  return (
    <main className="flex min-h-svh flex-col items-center justify-center gap-6 bg-background p-4 text-center">
      <div className="flex size-16 items-center justify-center rounded-2xl bg-rose-500/10 text-rose-500">
        <AlertTriangleIcon className="size-8" />
      </div>
      <div className="space-y-2">
        <h1 className="text-2xl font-bold">渲染出错 · Render error</h1>
        <p className="max-w-md text-sm text-muted-foreground">
          {error.message || "页面渲染时发生未知错误。"}
          {error.digest ? ` (digest: ${error.digest})` : ""}
        </p>
      </div>
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={() => window.location.reload()}
          className="inline-flex items-center gap-2 rounded-lg border border-line bg-card px-4 py-2 text-sm font-medium transition-colors hover:border-faint"
        >
          <RotateCcwIcon className="size-4" />
          重新加载 · Reload
        </button>
        <Link
          href="/dashboard"
          className="text-sm text-primary underline decoration-primary/40 underline-offset-2 hover:decoration-primary"
        >
          回到总览 · Dashboard
        </Link>
      </div>
    </main>
  );
}
