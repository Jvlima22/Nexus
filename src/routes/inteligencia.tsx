import { createFileRoute } from "@tanstack/react-router";
import { AppLayout } from "@/components/AppLayout";
import { AITerminal } from "@/components/ai/AITerminal";
import { KnowledgeBase } from "@/components/ai/KnowledgeBase";
import { IndicatorsGrid } from "@/components/ai/IndicatorsGrid";
import { AutonomyMode } from "@/components/ai/AutonomyMode";
import { RiskPanel } from "@/components/ai/RiskPanel";
import { useEffect } from "react";
import { toast } from "sonner";

export const Route = createFileRoute("/inteligencia")({
  head: () => ({
    meta: [
      { title: "Nexus Trader — Inteligência" },
      { name: "description", content: "Terminal Claude, memória Obsidian, indicadores e risco em tempo real." },
    ],
  }),
  component: IntelligencePage,
});

function IntelligencePage() {
  // Periodic "IA aprendeu algo novo" notification
  useEffect(() => {
    const events = [
      { title: "Memória atualizada no Obsidian", desc: "Nota #453 · reversao-btc-h1 salva." },
      { title: "Novo aprendizado consolidado", desc: "+2% margem em setups de alta volatilidade." },
      { title: "Padrão promovido a A+", desc: "Momentum SOL com 5 acertos consecutivos." },
    ];
    let i = 0;
    const id = setInterval(() => {
      const e = events[i % events.length];
      toast(e.title, { description: e.desc });
      i++;
    }, 14000);
    return () => clearInterval(id);
  }, []);

  return (
    <AppLayout
      title="Inteligência"
      subtitle="Pensamento, memória e gestão de risco — o coração do agente"
    >
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 space-y-4">
          <AITerminal source="nexus_mt5" />
          <IndicatorsGrid />
        </div>
        <div className="space-y-4">
          <AutonomyMode />
          <RiskPanel />
        </div>
      </div>

      <div className="mt-4">
        <KnowledgeBase />
      </div>
    </AppLayout>
  );
}
