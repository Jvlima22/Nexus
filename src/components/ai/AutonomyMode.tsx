import { Card } from "@/components/ui/card";
import { Hand, Users, Bot } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

const modes = [
  { id: "manual", label: "Manual", desc: "Apenas sinais — você executa.", Icon: Hand },
  { id: "hibrido", label: "Híbrido", desc: "IA sugere, você confirma.", Icon: Users },
  { id: "auto", label: "Full Auto", desc: "Claude no comando total.", Icon: Bot },
] as const;

export function AutonomyMode() {
  const [active, setActive] = useState<typeof modes[number]["id"]>("hibrido");
  return (
    <Card className="p-5 bg-card border-border">
      <div className="flex items-center justify-between mb-1">
        <h3 className="text-sm font-medium">Modo de Autonomia</h3>
        <span className="text-[10px] text-muted-foreground">Claude · v2.4</span>
      </div>
      <p className="text-xs text-muted-foreground mb-4">
        Defina o grau de controle entregue ao agente.
      </p>
      <div className="grid grid-cols-3 gap-2">
        {modes.map((m) => {
          const on = active === m.id;
          return (
            <button
              key={m.id}
              onClick={() => {
                setActive(m.id);
                toast.success(`Modo ${m.label} ativado`, {
                  description: m.desc,
                });
              }}
              className={cn(
                "rounded-md border p-3 text-left transition-all",
                on
                  ? "border-primary/60 bg-primary/10 shadow-[0_0_0_1px_oklch(0.75_0.15_160_/_0.3)]"
                  : "border-border bg-background/40 hover:border-primary/30 hover:bg-background/60"
              )}
            >
              <m.Icon className={cn("h-4 w-4 mb-2", on ? "text-primary" : "text-muted-foreground")} />
              <div className={cn("text-xs font-medium", on ? "text-foreground" : "text-foreground/80")}>
                {m.label}
              </div>
              <div className="text-[10px] text-muted-foreground mt-0.5 leading-snug">
                {m.desc}
              </div>
            </button>
          );
        })}
      </div>
    </Card>
  );
}
