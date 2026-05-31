import { useState } from "react";
import { toast } from "sonner";
import { ArrowUpRight, ArrowDownRight, Loader2 } from "lucide-react";
import { Card } from "@/components/ui/card";
import { useTrades } from "@/hooks/useTrades";
import { placeOrder } from "@/lib/connector";
import { cn } from "@/lib/utils";

const EXPIRATIONS = [1, 5, 15];

export function LiveTrades({ active }: { active: string }) {
  const trades = useTrades();
  const [amount, setAmount] = useState(1);
  const [expiration, setExpiration] = useState(1);
  const [sending, setSending] = useState<"call" | "put" | null>(null);

  async function submit(direction: "call" | "put") {
    setSending(direction);
    try {
      const r = await placeOrder({ active, direction, amount, expiration });
      toast.success(`Ordem enviada · ${active} ${direction.toUpperCase()}`, {
        description: `$${amount} · ${expiration}m · banca $${r.balance.toFixed(2)} (limite 2%: $${r.risk_limit.toFixed(2)})`,
      });
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      console.error("[NEXUS] Ordem recusada:", msg);
      toast.error("Ordem recusada", { description: msg });
    } finally {
      setSending(null);
    }
  }

  return (
    <Card className="p-0 bg-card border-border overflow-hidden">
      {/* Formulário de ordem */}
      <div className="px-5 py-4 border-b border-border">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-medium">Operar · {active}</h3>
          <span className="text-[11px] text-muted-foreground">gate de risco 2% no servidor</span>
        </div>
        <div className="flex flex-wrap items-end gap-3">
          <label className="flex flex-col gap-1">
            <span className="text-[11px] uppercase tracking-wider text-muted-foreground">Valor ($)</span>
            <input
              type="number"
              min={1}
              step={1}
              value={amount}
              onChange={(e) => setAmount(Math.max(1, Number(e.target.value)))}
              className="w-28 bg-background border border-border rounded-md px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-primary tabular-nums"
            />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-[11px] uppercase tracking-wider text-muted-foreground">Expiração</span>
            <select
              value={expiration}
              onChange={(e) => setExpiration(Number(e.target.value))}
              className="bg-background border border-border rounded-md px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
            >
              {EXPIRATIONS.map((m) => (
                <option key={m} value={m}>
                  {m}m
                </option>
              ))}
            </select>
          </label>
          <div className="flex items-center gap-2 ml-auto">
            <button
              onClick={() => submit("call")}
              disabled={sending !== null}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-md bg-success/15 text-success text-sm font-medium hover:bg-success/25 disabled:opacity-50 transition-colors"
            >
              {sending === "call" ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowUpRight className="h-4 w-4" />}
              CALL
            </button>
            <button
              onClick={() => submit("put")}
              disabled={sending !== null}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-md bg-danger/15 text-danger text-sm font-medium hover:bg-danger/25 disabled:opacity-50 transition-colors"
            >
              {sending === "put" ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowDownRight className="h-4 w-4" />}
              PUT
            </button>
          </div>
        </div>
      </div>

      {/* Operações ao vivo */}
      <div className="px-5 py-3 border-b border-border flex items-center justify-between">
        <h3 className="text-sm font-medium">Operações ao vivo</h3>
        <span className="text-xs text-muted-foreground tabular-nums">{trades.length}</span>
      </div>
      <div className="overflow-x-auto max-h-80 overflow-y-auto">
        {trades.length === 0 ? (
          <p className="px-5 py-6 text-sm text-muted-foreground text-center">
            Nenhuma operação ainda. Envie uma ordem acima — ela aparece aqui e muda para win/loss sozinha.
          </p>
        ) : (
          <table className="w-full text-sm">
            <thead className="text-[11px] uppercase tracking-wider text-muted-foreground">
              <tr className="border-b border-border">
                <th className="text-left font-medium px-5 py-2">Ativo</th>
                <th className="text-left font-medium px-3 py-2">Tipo</th>
                <th className="text-right font-medium px-3 py-2">Valor</th>
                <th className="text-right font-medium px-3 py-2">Resultado</th>
                <th className="text-left font-medium px-3 py-2">Origem</th>
              </tr>
            </thead>
            <tbody>
              {trades.map((t) => {
                const open = t.status === "open" || t.status == null;
                const win = (t.result ?? 0) > 0;
                return (
                  <tr key={t.id} className="border-b border-border/50 hover:bg-accent/30">
                    <td className="px-5 py-2 font-medium">{t.asset}</td>
                    <td className="px-3 py-2">
                      <span className={cn("text-xs", t.type === "Call" ? "text-success" : "text-danger")}>
                        {t.type}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-right tabular-nums">{t.amount != null ? `$${t.amount}` : "—"}</td>
                    <td className="px-3 py-2 text-right tabular-nums">
                      {open ? (
                        <span className="inline-flex items-center gap-1 text-warning">
                          <span className="h-1.5 w-1.5 rounded-full bg-warning pulse-ring" /> aberta
                        </span>
                      ) : t.status === "tie" ? (
                        <span className="text-muted-foreground">empate</span>
                      ) : (
                        <span className={win ? "text-success" : "text-danger"}>
                          {win ? "+" : ""}${(t.result ?? 0).toFixed(2)}
                        </span>
                      )}
                    </td>
                    <td className="px-3 py-2">
                      <span
                        className={cn(
                          "text-[10px] uppercase px-1.5 py-0.5 rounded",
                          t.source === "nexus" ? "bg-primary/15 text-primary" : "bg-muted text-muted-foreground",
                        )}
                      >
                        {t.source ?? "—"}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </Card>
  );
}
