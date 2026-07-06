import { Bell, Search } from "lucide-react";

export function Topbar({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <header className="h-16 shrink-0 border-b border-border bg-background/60 backdrop-blur px-4 md:px-8 flex items-center justify-between">
      <div>
        <h1 className="text-base md:text-lg font-semibold tracking-tight">{title}</h1>
        {subtitle && <p className="text-xs text-muted-foreground mt-0.5">{subtitle}</p>}
      </div>
      <div className="flex items-center gap-2">
        <div className="hidden md:flex items-center gap-2 rounded-md border border-border bg-card/60 px-3 h-9 text-xs text-muted-foreground w-64">
          <Search className="h-3.5 w-3.5" />
          <span>Buscar operações, ativos…</span>
          <kbd className="ml-auto text-[10px] border border-border rounded px-1.5 py-0.5">⌘K</kbd>
        </div>
        <button className="h-9 w-9 grid place-items-center rounded-md border border-border bg-card/60 hover:bg-accent">
          <Bell className="h-4 w-4" />
        </button>
        <div className="h-9 w-9 rounded-full bg-gradient-to-br from-primary/60 to-chart-5/60" />
      </div>
    </header>
  );
}
