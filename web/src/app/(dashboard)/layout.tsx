import { AppSidebar } from "@/components/app-sidebar";
import { BackToTop } from "@/components/back-to-top";
import { CommandPalette } from "@/components/command-palette";
import { DynamicBreadcrumb } from "@/components/dynamic-breadcrumb";
import { ThemeToggle } from "@/components/theme-toggle";
import { LangToggle } from "@/components/lang-toggle";
import { Separator } from "@/components/ui/separator";
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <SidebarProvider>
      <AppSidebar />
      <SidebarInset>
        {/* Frosted-glass nav bar (Apple material): translucent, blurred,
            hairline-separated — chrome that defers to content scrolling
            beneath it. */}
        <header className="sticky top-0 z-40 flex h-16 shrink-0 items-center gap-2 border-b border-border/60 bg-background/70 backdrop-blur-xl backdrop-saturate-150">
          <div className="flex items-center gap-2 px-4">
            <SidebarTrigger className="-ml-1" />
            <Separator
              orientation="vertical"
              className="mr-2 data-vertical:h-4 data-vertical:self-auto"
            />
            <DynamicBreadcrumb />
          </div>
          <div className="ml-auto flex items-center gap-1 pr-4">
            <CommandPalette />
            <LangToggle />
            <ThemeToggle />
          </div>
        </header>
        {/* overflow-hidden here would break position:sticky descendants (a
            hidden-overflow ancestor becomes the sticky element's scroll
            container and never scrolls) — h-overflow is prevented by
            min-w-0 on SidebarInset instead. */}
        <main className="flex min-w-0 flex-1 flex-col">{children}</main>
        <BackToTop />
      </SidebarInset>
    </SidebarProvider>
  );
}
