import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabase";

export interface BankrollPoint {
  balance: number;
  timestamp: string;
}

/**
 * Histórico de saldo (bankroll_history) com tempo real. Retorna a série em ordem
 * cronológica e o saldo mais recente. O Connector faz snapshots periódicos.
 */
export function useBankroll(limit = 200) {
  const [points, setPoints] = useState<BankrollPoint[]>([]);

  useEffect(() => {
    let active = true;

    supabase
      .from("bankroll_history")
      .select("balance,timestamp")
      .order("timestamp", { ascending: false })
      .limit(limit)
      .then(({ data }) => {
        if (active && data) setPoints((data as BankrollPoint[]).slice().reverse());
      });

    const channel = supabase
      .channel("bankroll-rt")
      .on("postgres_changes", { event: "INSERT", schema: "public", table: "bankroll_history" }, (payload) => {
        setPoints((prev) => [...prev, payload.new as BankrollPoint].slice(-limit));
      })
      .subscribe();

    return () => {
      active = false;
      supabase.removeChannel(channel);
    };
  }, [limit]);

  const latest = points.length ? points[points.length - 1].balance : null;
  return { points, latest };
}
