import { useState } from "react";
import { toast } from "sonner";
import { ArrowUpRight, ArrowDownRight, Loader2 } from "lucide-react";
import { placeOrder } from "@/lib/connector";

const EXPIRATIONS = [1, 5, 15];

/** Entrada de ordem sobreposta ao gráfico, estilo IQ Option (borda direita). */
export function ChartOrderPanel({ active }: { active: string }) {
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
    <div className="absolute left-3 top-1/2 -translate-y-1/2 z-10 w-40 flex flex-col gap-2 rounded-lg border border-border bg-card/80 backdrop-blur-sm p-2.5 shadow-lg">
      <label className="flex flex-col gap-1">
        <span className="text-[10px] uppercase tracking-wider text-muted-foreground">Valor ($)</span>
        <input
          type="number"
          min={1}
          step={1}
          value={amount}
          onChange={(e) => setAmount(Math.max(1, Number(e.target.value)))}
          className="w-full bg-background border border-border rounded-md px-2.5 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-primary tabular-nums"
        />
      </label>
      <label className="flex flex-col gap-1">
        <span className="text-[10px] uppercase tracking-wider text-muted-foreground">Expiração</span>
        <select
          value={expiration}
          onChange={(e) => setExpiration(Number(e.target.value))}
          className="w-full bg-background border border-border rounded-md px-2.5 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
        >
          {EXPIRATIONS.map((m) => (
            <option key={m} value={m}>
              {m}m
            </option>
          ))}
        </select>
      </label>
      <button
        onClick={() => submit("call")}
        disabled={sending !== null}
        className="inline-flex items-center justify-center gap-1.5 px-3 py-2.5 rounded-md bg-success/15 text-success text-sm font-semibold hover:bg-success/25 disabled:opacity-50 transition-colors"
      >
        {sending === "call" ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowUpRight className="h-4 w-4" />}
        CALL
      </button>
      <button
        onClick={() => submit("put")}
        disabled={sending !== null}
        className="inline-flex items-center justify-center gap-1.5 px-3 py-2.5 rounded-md bg-danger/15 text-danger text-sm font-semibold hover:bg-danger/25 disabled:opacity-50 transition-colors"
      >
        {sending === "put" ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowDownRight className="h-4 w-4" />}
        PUT
      </button>
      <span className="text-[10px] text-muted-foreground text-center leading-tight">gate de risco 2% no servidor</span>
    </div>
  );
}
