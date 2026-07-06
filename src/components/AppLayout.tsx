import { Sidebar } from "./Sidebar";
import { MobileNav } from "./MobileNav";
import { Topbar } from "./Topbar";
import { RequireAuth } from "./RequireAuth";

export function AppLayout({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
}) {
  return (
    <RequireAuth>
      <div className="h-screen overflow-hidden flex w-full bg-background text-foreground">
        <Sidebar />
        <div className="flex-1 flex flex-col min-w-0">
          <Topbar title={title} subtitle={subtitle} />
          <main className="flex-1 min-h-0 overflow-y-auto scrollbar-modern p-4 md:p-8 pb-24 md:pb-8">{children}</main>
        </div>
        <MobileNav />
      </div>
    </RequireAuth>
  );
}
