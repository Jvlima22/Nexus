import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabase";

export interface TradeRow {
  id: string;
  asset: string;
  type: string | null; // "Call" | "Put"
  amount: number | null;
  payout: number | null;
  result: number | null; // PnL em $ (preenchido no fechamento)
  status: string | null; // open | win | loss | tie
  source: string | null; // nexus | manual
  time: string | null;
  external_id: string | null;
}

const COLS = "id,asset,type,amount,payout,result,status,source,time,external_id";

/**
 * Operações em `trades` com tempo real. Uma ordem aparece como `open` e muda
 * para win/loss sozinha quando o Connector dá UPDATE (acompanhamento do resultado).
 */
export function useTrades(limit = 50) {
  const [trades, setTrades] = useState<TradeRow[]>([]);

  useEffect(() => {
    let active = true;

    supabase
      .from("trades")
      .select(COLS)
      .order("time", { ascending: false })
      .limit(limit)
      .then(({ data }) => {
        if (active && data) setTrades(data as TradeRow[]);
      });

    const channel = supabase
      .channel("trades-rt")
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
