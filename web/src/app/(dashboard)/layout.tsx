import { BackToTop } from "@/components/back-to-top";
import { TopNav } from "@/components/top-nav";

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
    <div className="flex min-h-screen flex-col">
      {/* eslint-disable-next-line react/no-danger -- static pre-paint seed, no user input */}
      <script dangerouslySetInnerHTML={{ __html: colorConvScript }} />
      <TopNav />
      {/* Aligned-site main rail: 1320px, px-5/py-8 (md:px-6). Sticky
          descendants (hot-ticker strip) stay valid — no overflow-hidden
          ancestor. */}
      <main className="mx-auto w-full max-w-[1320px] flex-1 px-5 py-8 md:px-6">
        {children}
      </main>
      <BackToTop />
    </div>
  );
}
