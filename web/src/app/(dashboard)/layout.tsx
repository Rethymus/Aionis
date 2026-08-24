import { AppSidebar } from "@/components/app-sidebar";
import { BackToTop } from "@/components/back-to-top";
import { ColorConvToggle } from "@/components/colorconv-toggle";
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

// Pre-paint application of the saved up/down color convention (same pattern
// next-themes uses for theme): ships inside the prerendered HTML and runs
// before hydration, so a CN-convention user never sees a green-up flash.
const colorConvScript = `try{if(localStorage.getItem("aionis-colorconv")==="cn"){document.documentElement.dataset.colorconv="cn"}}catch(e){}`;

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <SidebarProvider>
      {/* eslint-disable-next-line react/no-danger -- static pre-paint seed, no user input */}
      <script dangerouslySetInnerHTML={{ __html: colorConvScript }} />
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
            <ColorConvToggle />
            <LangToggle />
            <ThemeToggle />
          </div>
        </header>
        {/* overflow-hidden here would break position:sticky descendants (a
            hidden-overflow ancestor becomes the sticky element's scroll
            container and never scrolls) — h-overflow is prevented by
            min-w-0 on SidebarInset instead. */}
        <main className="flex min-w-0 flex-1 flex-col">
          {/* Deployed-terminal alignment: one shared 1320px content rail. */}
          <div className="mx-auto w-full max-w-[1320px] flex-1">{children}</div>
        </main>
        <BackToTop />
      </SidebarInset>
    </SidebarProvider>
  );
}
