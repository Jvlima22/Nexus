import { useState } from "react";
import { Card } from "@/components/ui/card";
import { useTrades, tradePair, tradeDirection, type TradeRow } from "@/hooks/useTrades";
import { cn } from "@/lib/utils";

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmt(v: number | null | undefined, digits = 5): string {
  if (v == null) return "—";
  return v.toFixed(digits);
}

function fmtPnl(v: number | null | undefined): string {
  if (v == null) return "—";
  return `${v >= 0 ? "+" : ""}$${v.toFixed(2)}`;
}

function elapsed(ts: string | null): string {
  if (!ts) return "—";
  const diff = Math.floor((Date.now() - new Date(ts).getTime()) / 1000);
  if (diff < 60)   return `${diff}s`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m`;
  return `${Math.floor(diff / 3600)}h`;
}

// ── Badge de status ───────────────────────────────────────────────────────────

function StatusBadge({ trade }: { trade: TradeRow }) {
  const isOpen   = trade.status === "open" || trade.status == null;
  const isClosed = trade.status === "closed";
  const pnl      = trade.pnl ?? trade.result ?? null;
  const isWin    = pnl != null && pnl > 0;

  if (isOpen) {
    return (
      <span className="inline-flex items-center gap-1 text-amber-400 text-xs">
        <span className="h-1.5 w-1.5 rounded-full bg-amber-400 animate-pulse" />
        aberta
      </span>
    );
  }
  if (isClosed || trade.status === "win" || trade.status === "loss") {
    return (
      <span className={cn("text-xs font-medium tabular-nums", isWin ? "text-emerald-400" : "text-rose-400")}>
        {fmtPnl(pnl)}
      </span>
    );
  }
  return <span className="text-xs text-zinc-500">{trade.status}</span>;
}

// ── Linha da tabela ───────────────────────────────────────────────────────────

function TradeRow({ trade, onClick }: { trade: TradeRow; onClick: () => void }) {
  const dir   = tradeDirection(trade);
  const pair  = tradePair(trade);
  const isBuy = dir === "BUY";
  const isOpen = trade.status === "open" || trade.status == null;

  return (
    <tr
      onClick={onClick}
      className="border-b border-border/40 hover:bg-accent/20 cursor-pointer transition-colors"
    >
      {/* Par */}
      <td className="px-4 py-2.5 font-medium text-sm whitespace-nowrap">{pair}</td>

      {/* Direção */}
      <td className="px-3 py-2.5">
        <span
          className={cn(
            "inline-block text-[11px] font-bold px-2 py-0.5 rounded",
            isBuy ? "bg-emerald-500/15 text-emerald-400" : "bg-rose-500/15 text-rose-400",
          )}
        >
          {dir ?? "—"}
        </span>
      </td>

      {/* Volume */}
      <td className="px-3 py-2.5 text-right tabular-nums text-sm text-zinc-300">
        {trade.volume != null ? `${trade.volume} lot` : "—"}
      </td>

      {/* Entry */}
      <td className="px-3 py-2.5 text-right tabular-nums text-sm text-zinc-300">
        {fmt(trade.entry_price)}
      </td>

      {/* SL */}
      <td className="px-3 py-2.5 text-right tabular-nums text-xs text-rose-400/80">
        {fmt(trade.stop_loss)}
      </td>

      {/* TP */}
      <td className="px-3 py-2.5 text-right tabular-nums text-xs text-emerald-400/80">
        {fmt(trade.take_profit)}
      </td>

      {/* Status / P&L */}
      <td className="px-3 py-2.5 text-right">
        <StatusBadge trade={trade} />
      </td>

      {/* Origem + tempo */}
      <td className="px-4 py-2.5 text-right text-[11px] text-zinc-500 whitespace-nowrap">
        <div className="flex flex-col items-end gap-0.5">
          <span className={cn(
            "uppercase px-1.5 py-0.5 rounded text-[10px]",
            trade.source === "nexus_mt5"
              ? "bg-violet-500/15 text-violet-400"
              : "bg-zinc-700/50 text-zinc-400",
          )}>
            {trade.source === "nexus_mt5" ? "nexus" : (trade.source ?? "—")}
          </span>
          <span>{elapsed(trade.created_at ?? trade.time)}</span>
        </div>
      </td>
    </tr>
  );
}

// ── Painel de detalhe ─────────────────────────────────────────────────────────

function DetailPanel({ trade, onClose }: { trade: TradeRow; onClose: () => void }) {
  const dir   = tradeDirection(trade);
  const pair  = tradePair(trade);
  const isBuy = dir === "BUY";
  const pnl   = trade.pnl ?? trade.result ?? null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/60 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="w-full sm:max-w-md bg-zinc-900 border border-zinc-700 rounded-t-2xl sm:rounded-2xl p-5 space-y-4"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-lg font-bold">{pair}</span>
            <span className={cn(
              "text-xs font-bold px-2 py-0.5 rounded",
              isBuy ? "bg-emerald-500/15 text-emerald-400" : "bg-rose-500/15 text-rose-400",
            )}>
              {dir}
            </span>
          </div>
          <button onClick={onClose} className="text-zinc-500 hover:text-zinc-300 text-xl leading-none">×</button>
        </div>

        {/* Grid de dados */}
        <div className="grid grid-cols-2 gap-3 text-sm">
          {[
            ["Ticket",    trade.position_id ?? "—"],
            ["Volume",    trade.volume != null ? `${trade.volume} lot` : "—"],
            ["Entry",     fmt(trade.entry_price)],
            ["Close",     fmt(trade.close_price)],
            ["Stop Loss", fmt(trade.stop_loss)],
            ["Take Profit", fmt(trade.take_profit)],
            ["Sessão",    trade.session ?? "—"],
            ["Motivo",    trade.close_reason ?? "—"],
          ].map(([label, val]) => (
            <div key={label} className="bg-zinc-800 rounded-lg p-3">
              <div className="text-[11px] text-zinc-500 uppercase tracking-wide mb-1">{label}</div>
              <div className="font-medium tabular-nums">{val}</div>
            </div>
          ))}
        </div>

        {/* P&L destacado */}
        {pnl != null && (
          <div className={cn(
            "rounded-xl p-4 text-center",
            pnl >= 0 ? "bg-emerald-500/10 border border-emerald-500/20" : "bg-rose-500/10 border border-rose-500/20",
          )}>
            <div className="text-xs text-zinc-400 mb-1">P&L</div>
            <div className={cn("text-2xl font-bold", pnl >= 0 ? "text-emerald-400" : "text-rose-400")}>
              {fmtPnl(pnl)}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Componente principal ──────────────────────────────────────────────────────

export function LiveTrades() {
  const trades   = useTrades();
  const [sel, setSel] = useState<TradeRow | null>(null);

  const abertas  = trades.filter((t) => t.status === "open" || t.status == null);
  const fechadas = trades.filter((t) => t.status !== "open" && t.status != null);
  const pnlTotal = fechadas.reduce((acc, t) => acc + (t.pnl ?? t.result ?? 0), 0);

  return (
    <Card className="p-0 bg-card border-border overflow-hidden">
      {/* Header */}
      <div className="px-5 py-3 border-b border-border flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h3 className="text-sm font-medium">Operações MT5</h3>
          <span className="text-xs bg-amber-500/10 text-amber-400 px-2 py-0.5 rounded tabular-nums">
            {abertas.length} abertas
          </span>
        </div>
        {fechadas.length > 0 && (
          <span className={cn(
            "text-xs font-medium tabular-nums",
            pnlTotal >= 0 ? "text-emerald-400" : "text-rose-400",
          )}>
            P&L: {fmtPnl(pnlTotal)}
          </span>
        )}
      </div>

      {/* Tabela */}
      <div className="overflow-x-auto max-h-96 overflow-y-auto">
        {trades.length === 0 ? (
          <p className="px-5 py-8 text-sm text-muted-foreground text-center">
            Nenhuma operação registrada ainda.<br />
            <span className="text-xs text-zinc-600 mt-1 block">
              Execute o bot ou aplique a migration Supabase para ativar o sync.
            </span>
          </p>
        ) : (
          <table className="w-full text-sm">
            <thead className="text-[10px] uppercase tracking-wider text-zinc-500 sticky top-0 bg-card">
              <tr className="border-b border-border">
                <th className="text-left font-medium px-4 py-2">Par</th>
                <th className="text-left font-medium px-3 py-2">Side</th>
                <th className="text-right font-medium px-3 py-2">Volume</th>
                <th className="text-right font-medium px-3 py-2">Entry</th>
                <th className="text-right font-medium px-3 py-2">SL</th>
                <th className="text-right font-medium px-3 py-2">TP</th>
                <th className="text-right font-medium px-3 py-2">P&L</th>
                <th className="text-right font-medium px-4 py-2">Origem</th>
              </tr>
            </thead>
            <tbody>
              {/* Abertas primeiro */}
              {abertas.map((t) => (
                <TradeRow key={t.id} trade={t} onClick={() => setSel(t)} />
              ))}
              {/* Separador se houver ambas */}
              {abertas.length > 0 && fechadas.length > 0 && (
                <tr>
                  <td colSpan={8} className="px-4 py-1.5 text-[10px] uppercase text-zinc-600 tracking-wider bg-zinc-900/40">
                    Fechadas
                  </td>
                </tr>
              )}
              {fechadas.map((t) => (
                <TradeRow key={t.id} trade={t} onClick={() => setSel(t)} />
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Detalhe */}
      {sel && <DetailPanel trade={sel} onClose={() => setSel(null)} />}
    </Card>
  );
}
