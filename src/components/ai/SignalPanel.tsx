import { useEffect, useState, useCallback } from "react";
import { toast } from "sonner";
import { Activity, TrendingUp, TrendingDown, Minus, RefreshCw, Check, Loader2, Gauge } from "lucide-react";
import { Card } from "@/components/ui/card";
import { fetchIndicators, placeOrder, type Signal, type Vote } from "@/lib/connector";
import { cn } from "@/lib/utils";

const VOTE_META: Record<Vote, { cls: string; Icon: typeof TrendingUp }> = {
  bullish: { cls: "text-success", Icon: TrendingUp },
  bearish: { cls: "text-danger", Icon: TrendingDown },
  neutral: { cls: "text-muted-foreground", Icon: Minus },
};

/**
 * Painel de sinal técnico (Fase 2): mostra o sinal "rules" do connector e permite
 * APROVAR — que envia a ordem com a confidence do sinal pelo Risk Judge. Aprovação
 * humana obrigatória; o servidor ainda aplica todos os gates (macro/sessão/notícia/risco).
 */
export function SignalPanel({ active, size, amount = 1, expiration = 1 }: {
  active: string;
  size: number;
  amount?: number;
  expiration?: number;
}) {
  const [signal, setSignal] = useState<Signal | null>(null);
  const [loading, setLoading] = useState(false);
  const [approving, setApproving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setSignal(await fetchIndicators(active, size));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setSignal(null);
    } finally {
      setLoading(false);
    }
  }, [active, size]);

  useEffect(() => {
    load();
  }, [load]);

  async function approve() {
    if (!signal?.direction) return;
    setApproving(true);
    try {
      const r = await placeOrder({
        active: signal.active,
        direction: signal.direction,
        amount,
        expiration,
        confidence: signal.confidence,
      });
      toast.success(`Sinal aprovado · ${signal.active} ${signal.direction.toUpperCase()}`, {
        description: `$${amount} · conf ${(signal.confidence * 100).toFixed(0)}% · banca $${r.balance.toFixed(2)}`,
      });
    } catch (e) {
      const err = e as Error & { code?: string };
      toast.error(err.code ? `Vetado pelo Risk Judge · ${err.code}` : "Ordem recusada", {
        description: err.message,
      });
    } finally {
      setApproving(false);
    }
  }

  const meta = signal ? VOTE_META[signal.bias] : VOTE_META.neutral;
  const pct = signal ? Math.round(signal.confidence * 100) : 0;

  return (
    <Card className="p-5 bg-card border-border">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Activity className="h-4 w-4 text-primary" />
          <h3 className="text-sm font-medium">Sinal Técnico · {active}</h3>
        </div>
        <button
          onClick={load}
          disabled={loading}
          className="text-muted-foreground hover:text-foreground transition-colors disabled:opacity-50"
          title="Recarregar"
        >
          <RefreshCw className={cn("h-3.5 w-3.5", loading && "animate-spin")} />
        </button>
      </div>

      {error ? (
        <p className="text-sm text-danger">{error}</p>
      ) : !signal ? (
        <p className="text-sm text-muted-foreground">Carregando análise…</p>
      ) : (
        <>
          <div className="flex items-center gap-4">
            <div className="flex-1">
              <div className={cn("inline-flex items-center gap-1.5 text-lg font-semibold", meta.cls)}>
                <meta.Icon className="h-5 w-5" />
                {signal.direction ? signal.direction.toUpperCase() : "SEM SINAL"}
                <span className="text-xs font-normal text-muted-foreground">· {signal.timeframe}</span>
              </div>
              <div className="mt-1 text-[11px] text-muted-foreground">
                confiança {pct}% · {signal.candles_used} candles
              </div>
            </div>
          </div>

          <div className="mt-2 h-1.5 rounded-full bg-muted overflow-hidden">
            <div
              className={cn("h-full transition-all", signal.bias === "bullish" ? "bg-success" : signal.bias === "bearish" ? "bg-danger" : "bg-warning")}
              style={{ width: `${pct}%` }}
            />
          </div>

          {/* Regime de mercado (prompt #4): ambiente em que o sinal foi gerado */}
          <div className={cn(
            "mt-3 rounded-md border px-3 py-2",
            signal.regime.suitable_for_trend
              ? "border-success/30 bg-success/5"
              : "border-warning/30 bg-warning/5",
          )}>
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-1.5 text-xs font-medium">
                <Gauge className={cn("h-3.5 w-3.5", signal.regime.suitable_for_trend ? "text-success" : "text-warning")} />
                Regime
              </div>
              <div className="flex flex-wrap items-center gap-1 text-[10px]">
                <span className="rounded bg-background/60 px-1.5 py-0.5">tend. {signal.regime.trend}</span>
                <span className="rounded bg-background/60 px-1.5 py-0.5">vol {signal.regime.volatility}</span>
                {signal.regime.volume !== "indisponível" && (
                  <span className="rounded bg-background/60 px-1.5 py-0.5">volume {signal.regime.volume}</span>
                )}
                {signal.regime.atr_pct != null && (
                  <span className="rounded bg-background/60 px-1.5 py-0.5">ATR {signal.regime.atr_pct}%</span>
                )}
              </div>
            </div>
            <p className="mt-1.5 text-[11px] text-muted-foreground leading-relaxed">{signal.regime.recommend}</p>
          </div>

          {/* Votos por indicador */}
          <div className="mt-4 grid grid-cols-2 sm:grid-cols-3 gap-2">
            {Object.entries(signal.features.votes).map(([name, vote]) => {
              const vm = VOTE_META[vote];
              return (
                <div key={name} className="rounded-md border border-border bg-background/40 px-2.5 py-2">
                  <div className="text-[10px] uppercase tracking-wider text-muted-foreground">{name}</div>
                  <div className={cn("inline-flex items-center gap-1 text-xs font-medium", vm.cls)}>
                    <vm.Icon className="h-3 w-3" /> {vote}
                  </div>
                </div>
              );
            })}
          </div>

          <p className="mt-3 text-[11px] text-muted-foreground leading-relaxed">{signal.rationale}</p>

          {/* Aprovação */}
          <button
            onClick={approve}
            disabled={approving || !signal.direction}
            className={cn(
              "mt-4 w-full inline-flex items-center justify-center gap-2 rounded-md px-4 py-2.5 text-sm font-medium transition-colors disabled:opacity-50",
              signal.direction === "call"
                ? "bg-success/15 text-success hover:bg-success/25"
                : signal.direction === "put"
                  ? "bg-danger/15 text-danger hover:bg-danger/25"
                  : "bg-muted text-muted-foreground cursor-not-allowed",
            )}
          >
            {approving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
            {signal.direction ? `Aprovar ${signal.direction.toUpperCase()} ($${amount})` : "Sem consenso — nada a aprovar"}
          </button>
          <p className="mt-1.5 text-[10px] text-muted-foreground text-center">
            Passa pelo Risk Judge (macro · sessão · notícia · 2% · breaker). Conta PRACTICE.
          </p>
        </>
      )}
    </Card>
  );
}
