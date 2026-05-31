import { createFileRoute } from "@tanstack/react-router";
import { AppLayout } from "@/components/AppLayout";
import { Card } from "@/components/ui/card";
import { insights } from "@/lib/mock-data";
import { useTrades } from "@/hooks/useTrades";
import { ArrowUpRight, ArrowDownRight, Brain } from "lucide-react";

const fmtTime = (iso: string | null) =>
  iso ? new Date(iso).toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" }) : "—";

export const Route = createFileRoute("/historico")({
  head: () => ({
    meta: [
      { title: "Nexus Trader — Histórico e Memória" },
      { name: "description", content: "Operações executadas e know-how aprendido pela IA." },
    ],
  }),
  component: HistoryPage,
});

function HistoryPage() {
  const trades = useTrades(100);
  return (
    <AppLayout title="Histórico e Memória" subtitle="Operações executadas e insights da IA (Obsidian sync)">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="lg:col-span-2 p-0 bg-card border-border overflow-hidden">
          <div className="px-5 py-4 border-b border-border flex items-center justify-between">
            <div>
              <h3 className="text-sm font-medium">Operações recentes</h3>
              <p className="text-xs text-muted-foreground">Tempo real via Supabase</p>
            </div>
            <span className="text-xs text-muted-foreground tabular-nums">{trades.length}</span>
          </div>
          <div className="overflow-x-auto max-h-[560px] overflow-y-auto">
            <table className="w-full text-sm">
              <thead className="text-[11px] uppercase tracking-wider text-muted-foreground">
                <tr className="border-b border-border">
                  <th className="text-left font-medium px-5 py-3">Ativo</th>
                  <th className="text-left font-medium px-3 py-3">Tipo</th>
                  <th className="text-right font-medium px-3 py-3">Resultado</th>
                  <th className="text-left font-medium px-3 py-3">Horário</th>
                  <th className="text-right font-medium px-5 py-3">Origem</th>
                </tr>
              </thead>
              <tbody>
                {trades.length === 0 && (
                  <tr>
                    <td colSpan={5} className="px-5 py-8 text-center text-sm text-muted-foreground">
                      Nenhuma operação ainda.
                    </td>
                  </tr>
                )}
                {trades.map((t) => {
                  const open = t.status === "open" || t.status == null;
                  const win = (t.result ?? 0) > 0;
                  return (
                    <tr key={t.id} className="border-b border-border/60 hover:bg-accent/30">
                      <td className="px-5 py-3 font-medium">{t.asset}</td>
                      <td className="px-3 py-3">
                        <span className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded ${
                          t.type === "Call" ? "bg-success/15 text-success" : "bg-danger/15 text-danger"
                        }`}>
                          {t.type === "Call" ? <ArrowUpRight className="h-3 w-3" /> : <ArrowDownRight className="h-3 w-3" />}
                          {t.type ?? "—"}
                        </span>
                      </td>
                      <td className={`px-3 py-3 text-right tabular-nums ${open ? "text-warning" : win ? "text-success" : "text-danger"}`}>
                        {open ? "aberta" : `${win ? "+" : ""}$${(t.result ?? 0).toFixed(2)}`}
                      </td>
                      <td className="px-3 py-3 text-muted-foreground tabular-nums">{fmtTime(t.time)}</td>
                      <td className="px-5 py-3 text-right">
                        <span className={`text-[10px] uppercase px-1.5 py-0.5 rounded ${
                          t.source === "nexus" ? "bg-primary/15 text-primary" : "bg-muted text-muted-foreground"
                        }`}>
                          {t.source ?? "—"}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Card>

        <Card className="p-5 bg-card border-border">
          <div className="flex items-center gap-2 mb-4">
            <Brain className="h-4 w-4 text-primary" />
            <h3 className="text-sm font-medium">Log de know-how</h3>
          </div>
          <div className="space-y-3">
            {insights.map((i, k) => (
              <div key={k} className="rounded-md border border-border bg-background/40 p-3">
                <div className="text-[10px] uppercase tracking-wider text-primary mb-1">Aprendizado</div>
                <p className="text-xs text-foreground/85 leading-relaxed">{i}</p>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </AppLayout>
  );
}
