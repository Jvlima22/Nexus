import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabase";

export interface TradeRow {
  id: string;
  // Campos MT5
  position_id: string | null;
  symbol: string | null;
  asset: string | null;           // fallback legacy
  direction: string | null;       // BUY | SELL
  type: string | null;            // alias direction (legado)
  volume: number | null;
  entry_price: number | null;
  stop_loss: number | null;
  take_profit: number | null;
  close_price: number | null;
  pnl: number | null;
  result: number | null;          // legado — mesmo que pnl
  close_reason: string | null;    // tp | sl | manual
  status: string | null;          // open | closed | win | loss
  source: string | null;
  session: string | null;
  timeframe: string | null;
  time: string | null;
  created_at: string | null;
  closed_at: string | null;
}

const COLS = [
  "id", "position_id", "symbol", "asset", "direction", "type",
  "volume", "entry_price", "stop_loss", "take_profit",
  "close_price", "pnl", "result", "close_reason",
  "status", "source", "session", "timeframe",
  "time", "created_at", "closed_at",
].join(",");

/** Retorna o par do trade independente do campo preenchido. */
export function tradePair(t: TradeRow): string {
  return t.symbol ?? t.asset ?? "—";
}

/** Retorna a direção (BUY/SELL) independente do campo preenchido. */
export function tradeDirection(t: TradeRow): string | null {
  return t.direction ?? t.type ?? null;
}

/**
 * Operações MT5 em tempo real via Supabase Realtime.
 * Suporta tanto trades MT5 (nexus_mt5) quanto legado (nexus/manual).
 */
export function useTrades(limit = 100) {
  const [trades, setTrades] = useState<TradeRow[]>([]);

  useEffect(() => {
    let active = true;

    supabase
      .from("trades")
      .select(COLS)
      .order("created_at", { ascending: false })
      .limit(limit)
      .then(({ data }) => {
        if (active && data) setTrades(data as unknown as TradeRow[]);
      });

    const channel = supabase
      .channel("trades-rt-mt5")
      .on("postgres_changes", { event: "*", schema: "public", table: "trades" }, (payload) => {
        setTrades((prev) => {
          if (payload.eventType === "DELETE") {
            return prev.filter((t) => t.id !== (payload.old as TradeRow).id);
          }
          const row = payload.new as TradeRow;
          const i = prev.findIndex((t) => t.id === row.id);
          if (i === -1) return [row, ...prev].slice(0, limit);
          const next = [...prev];
          next[i] = row;
          return next;
        });
      })
      .subscribe();

    return () => {
      active = false;
      supabase.removeChannel(channel);
    };
  }, [limit]);

  return trades;
}
