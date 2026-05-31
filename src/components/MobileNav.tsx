import { Link, useRouterState } from "@tanstack/react-router";
import { LayoutDashboard, SlidersHorizontal, History, Plug, Brain, Library } from "lucide-react";
import { cn } from "@/lib/utils";

const nav = [
  { to: "/", label: "Visão", icon: LayoutDashboard },
  { to: "/inteligencia", label: "IA", icon: Brain },
  { to: "/knowledge", label: "Memória", icon: Library },
  { to: "/controle", label: "Controle", icon: SlidersHorizontal },
  { to: "/historico", label: "Histórico", icon: History },
];

export function MobileNav() {
  const path = useRouterState({ select: (s) => s.location.pathname });
  return (
    <nav className="md:hidden fixed bottom-0 inset-x-0 z-30 border-t border-border bg-sidebar/95 backdrop-blur">
      <div className="grid grid-cols-5">
        {nav.map((n) => {
          const active = path === n.to;
          return (
            <Link
              key={n.to}
              to={n.to}
              className={cn(
                "flex flex-col items-center gap-1 py-2.5 text-[10px]",
                active ? "text-primary" : "text-muted-foreground"
              )}
            >
              <n.icon className="h-4 w-4" />
              {n.label}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
