import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabase";
import type { TradeSnapshot } from "@/lib/snapshot";

/**
 * Busca SOB DEMANDA o snapshot de uma operação (só quando o modal abre).
 * Lê `trade_snapshots` por trade_id; RLS garante que é do dono. Trades antigas
 * (anteriores à feature) não têm snapshot → retorna null sem erro.
 */
export function useTradeSnapshot(tradeId: string | null) {
  const [snapshot, setSnapshot] = useState<TradeSnapshot | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!tradeId) {
      setSnapshot(null);
      setError(null);
      return;
    }
    let active = true;
    setLoading(true);
    setError(null);

    supabase
      .from("trade_snapshots")
      .select("snapshot")
      .eq("trade_id", tradeId)
      .maybeSingle()
      .then(({ data, error }) => {
        if (!active) return;
        if (error) setError(error.message);
        setSnapshot((data?.snapshot as TradeSnapshot) ?? null);
        setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [tradeId]);

  return { snapshot, loading, error };
}
