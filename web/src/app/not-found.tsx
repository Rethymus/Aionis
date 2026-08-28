import Link from "next/link"
import { Button } from "@/components/ui/button"
import { LandmarkIcon } from "lucide-react"

export default function NotFound() {
  return (
    // Semantic main landmark (a11y F-AUD4): same element classes — main is
    // block-level like div, so layout and visuals are unchanged.
    <main className="flex min-h-svh flex-col items-center justify-center gap-6 bg-background p-4 text-center">
      <div className="flex size-16 items-center justify-center rounded-2xl bg-primary text-primary-foreground">
        <LandmarkIcon className="size-8" />
      </div>
      <div className="space-y-2">
        <h1 className="text-4xl font-bold tabular-nums">404</h1>
        <p className="text-muted-foreground">This page doesn&apos;t exist.</p>
      </div>
      <Button render={<Link href="/dashboard" />}>
        Back to Dashboard
      </Button>
    </main>
  )
}
