import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabase";

export interface AssetRow {
  id: string;
  symbol: string;
  name: string | null;
  type: string;
  is_open: boolean;
  payout: number | null;
}

const COLS = "id,symbol,name,type,is_open,payout";

/**
 * Lista de ativos da IQ espelhada no Supabase, com atualização em tempo real.
 * O Connector faz o poll e grava; aqui só lemos (RLS: só os do usuário logado).
 */
export function useAssets() {
  const [assets, setAssets] = useState<AssetRow[]>([]);

  useEffect(() => {
    let active = true;

    supabase
      .from("assets")
      .select(COLS)
      .order("symbol")
      .then(({ data }) => {
        if (active && data) setAssets(data as AssetRow[]);
      });

    const channel = supabase
      .channel("assets-rt")
      .on("postgres_changes", { event: "*", schema: "public", table: "assets" }, (payload) => {
        setAssets((prev) => {
          if (payload.eventType === "DELETE") {
            return prev.filter((a) => a.id !== (payload.old as AssetRow).id);
          }
          const row = payload.new as AssetRow;
          const i = prev.findIndex((a) => a.id === row.id);
          if (i === -1) return [...prev, row].sort((a, b) => a.symbol.localeCompare(b.symbol));
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
  }, []);

  return assets;
}
