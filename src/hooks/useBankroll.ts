import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabase";

export interface BankrollPoint {
  balance: number;
  equity: number | null;
  margin_level: number | null;
  timestamp: string;
}

/**
 * Histórico de saldo (bankroll_history) com tempo real, filtrado por `source`
 * (conta/corretora — ex. "nexus_mt5" ou "nexus"/"tick"). Retorna a série em
 * ordem cronológica e o snapshot mais recente.
 */
export function useBankroll(source: string, limit = 200) {
  const [points, setPoints] = useState<BankrollPoint[]>([]);

  useEffect(() => {
    let active = true;
    setPoints([]);

    supabase
      .from("bankroll_history")
      .select("balance,equity,margin_level,timestamp")
      .eq("source", source)
      .order("timestamp", { ascending: false })
      .limit(limit)
      .then(({ data }) => {
        if (active && data) setPoints((data as BankrollPoint[]).slice().reverse());
      });

    const channel = supabase
      .channel(`bankroll-rt-${source}`)
      .on("postgres_changes", { event: "INSERT", schema: "public", table: "bankroll_history" }, (payload) => {
        const row = payload.new as BankrollPoint & { source: string };
        if (row.source !== source) return;
        setPoints((prev) => [...prev, row].slice(-limit));
      })
      .subscribe();

    return () => {
      active = false;
      supabase.removeChannel(channel);
    };
  }, [source, limit]);

  const latest = points.length ? points[points.length - 1] : null;
  return { points, latest };
}
