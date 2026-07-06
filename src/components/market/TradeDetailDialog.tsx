import { Loader2, TrendingUp, TrendingDown } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { SnapshotChart } from "@/components/market/SnapshotChart";
import { useTradeSnapshot } from "@/hooks/useTradeSnapshot";
import type { TradeRow } from "@/hooks/useTrades";
import type { CandlePattern } from "@/lib/snapshot";
import { cn } from "@/lib/utils";

const BIAS_CLS: Record<CandlePattern["bias"], string> = {
  bullish: "bg-success/15 text-success",
  bearish: "bg-danger/15 text-danger",
  neutral: "bg-muted text-muted-foreground",
};

function Stat({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-[10px] uppercase tracking-wider text-muted-foreground">{label}</span>
      <span className="text-sm tabular-nums">{value ?? "—"}</span>
    </div>
  );
}

const fmt = (n: number | null | undefined, d = 5) => (n == null ? "—" : n.toFixed(d));

/**
 * Detalhe pós-trade: ao clicar numa operação, redesenha o mercado do instante da
 * ordem (gráfico + entrada + S/R), o padrão de candle identificado e os indicadores
 * usados. Trades anteriores à feature não têm snapshot (mostra aviso).
 */
export function TradeDetailDialog({ trade, onClose }: { trade: TradeRow | null; onClose: () => void }) {
  const { snapshot, loading, error } = useTradeSnapshot(trade?.id ?? null);
  const open = trade !== null;
  const call = trade?.type === "Call";

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-3xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            {trade && (
              <span className={cn(call ? "text-success" : "text-danger")}>
                {call ? <TrendingUp className="h-4 w-4" /> : <TrendingDown className="h-4 w-4" />}
              </span>
            )}
            <span>{trade?.asset}</span>
            <span className="text-xs text-muted-foreground font-normal">
              {trade?.type} · {trade?.source ?? "—"}
              {trade?.time ? ` · ${new Date(trade.time).toLocaleString()}` : ""}
            </span>
          </DialogTitle>
        </DialogHeader>

        {loading ? (
          <div className="grid place-items-center h-64 text-muted-foreground">
            <Loader2 className="h-5 w-5 animate-spin" />
          </div>
        ) : error ? (
          <p className="text-sm text-danger">{error}</p>
        ) : !snapshot ? (
          <p className="text-sm text-muted-foreground py-8 text-center">
            Sem snapshot para esta operação. Operações anteriores a esta feature não foram
            capturadas — as próximas terão o retrato completo do mercado.
          </p>
        ) : (
          <div className="space-y-4">
            <div className="h-72 rounded-md border border-border overflow-hidden">
              <SnapshotChart snapshot={snapshot} />
            </div>

            {/* Padrões identificados */}
            <div>
              <div className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1.5">
                Padrão de candle
              </div>
              {snapshot.patterns.length === 0 ? (
                <span className="text-xs text-muted-foreground">Nenhum padrão clássico no candle de entrada.</span>
              ) : (
                <div className="flex flex-wrap gap-1.5">
                  {snapshot.patterns.map((p, i) => (
                    <span key={i} className={cn("text-xs px-2 py-0.5 rounded capitalize", BIAS_CLS[p.bias])}>
                      {p.name}
                    </span>
                  ))}
                </div>
              )}
            </div>

            {/* Indicadores + S/R + risco */}
            <div className="grid grid-cols-3 sm:grid-cols-4 gap-3 border-t border-border pt-3">
              <Stat label="RSI" value={fmt(snapshot.indicators.rsi, 1)} />
              <Stat label="EMA 9" value={fmt(snapshot.indicators.ema9)} />
              <Stat label="EMA 21" value={fmt(snapshot.indicators.ema21)} />
              <Stat label="MACD hist" value={fmt(snapshot.indicators.macd?.hist, 5)} />
              <Stat label="Resistência" value={<span className="text-danger">{fmt(snapshot.support_resistance.resistance)}</span>} />
              <Stat label="Suporte" value={<span className="text-success">{fmt(snapshot.support_resistance.support)}</span>} />
              <Stat
                label="Confiança"
                value={`${(snapshot.signal.confidence * 100).toFixed(0)}%`}
              />
              <Stat label="Expiração" value={`${snapshot.expiration_min}m`} />
              {snapshot.indicators.bollinger && (
                <>
                  <Stat label="Boll. sup" value={fmt(snapshot.indicators.bollinger.upper)} />
                  <Stat label="Boll. méd" value={fmt(snapshot.indicators.bollinger.mid)} />
                  <Stat label="Boll. inf" value={fmt(snapshot.indicators.bollinger.lower)} />
                </>
              )}
              {snapshot.payout != null && <Stat label="Payout" value={`${snapshot.payout}%`} />}
            </div>

            {/* Racional do sinal */}
            <div className="border-t border-border pt-3">
              <div className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1">
                Racional do sinal ({snapshot.signal.source})
              </div>
              <p className="text-xs text-muted-foreground">{snapshot.signal.rationale}</p>
            </div>

            {snapshot.risk && (
              <p className="text-[10px] text-muted-foreground text-center border-t border-border pt-2">
                Risk Judge · banca ${fmt(snapshot.risk.balance, 2)} · limite 2% $
                {fmt(snapshot.risk.risk_limit, 2)}
                {snapshot.risk.pnl_today != null ? ` · PnL dia $${fmt(snapshot.risk.pnl_today, 2)}` : ""}
              </p>
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
