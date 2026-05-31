import { Link, useRouterState } from "@tanstack/react-router";
import { LayoutDashboard, SlidersHorizontal, History, Plug, Activity, Brain, Library, LogOut, CandlestickChart } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/hooks/useAuth";

const nav = [
  { to: "/", label: "Visão Geral", icon: LayoutDashboard },
  { to: "/mercado", label: "Mercado", icon: CandlestickChart },
  { to: "/inteligencia", label: "Inteligência", icon: Brain },
  { to: "/knowledge", label: "Knowledge", icon: Library },
  { to: "/controle", label: "Controle", icon: SlidersHorizontal },
  { to: "/historico", label: "Histórico", icon: History },
  { to: "/conexoes", label: "Conexões", icon: Plug },
];

export function Sidebar() {
  const path = useRouterState({ select: (s) => s.location.pathname });
  const { user, signOut } = useAuth();
  return (
    <aside className="hidden md:flex w-60 shrink-0 flex-col border-r border-sidebar-border bg-sidebar">
      <div className="flex items-center gap-2 px-5 h-16 border-b border-sidebar-border">
        <div className="relative grid place-items-center h-8 w-8 rounded-md bg-primary/15 text-primary">
          <Activity className="h-4 w-4" />
          <span className="absolute -right-0.5 -top-0.5 h-2 w-2 rounded-full bg-primary pulse-ring" />
        </div>
        <div className="leading-tight">
          <div className="text-sm font-semibold tracking-tight">Nexus Trader</div>
          <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Autonomous AI</div>
        </div>
      </div>
      <nav className="flex-1 p-3 space-y-1">
        {nav.map((n) => {
          const active = path === n.to;
          return (
            <Link
              key={n.to}
              to={n.to}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors",
                active
                  ? "bg-sidebar-accent text-sidebar-accent-foreground"
                  : "text-sidebar-foreground/70 hover:text-sidebar-foreground hover:bg-sidebar-accent/60"
              )}
            >
              <n.icon className="h-4 w-4" />
              {n.label}
            </Link>
          );
        })}
      </nav>
      <div className="p-3 border-t border-sidebar-border space-y-2">
        <div className="rounded-md bg-card/60 border border-border p-3">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <span className="h-1.5 w-1.5 rounded-full bg-success animate-thinking" />
            Agente operando
          </div>
          <div className="mt-1 text-[11px] text-muted-foreground/70">Sessão #4821 · 02:14h</div>
        </div>
        {user && (
          <button
            onClick={() => signOut()}
            className="w-full flex items-center gap-2 rounded-md px-3 py-2 text-xs text-sidebar-foreground/70 hover:text-sidebar-foreground hover:bg-sidebar-accent/60 transition-colors"
            title={user.email ?? ""}
          >
            <LogOut className="h-3.5 w-3.5" />
            <span className="truncate">{user.email}</span>
          </button>
        )}
      </div>
    </aside>
  );
}
