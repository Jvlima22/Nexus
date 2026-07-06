import { useEffect, useMemo, useState } from "react";
import { supabase } from "@/lib/supabase";
import type { MacroBias, SentimentMarket } from "@/lib/connector";

const COLS = "slug,question,probability,bias,volume,updated_at";

/**
 * Sentimento macro (Polymarket) com tempo real. O Connector faz upsert em
 * `market_sentiment` por slug; aqui assinamos as mudanças de probabilidade/bias
 * e derivamos o bias macro agregado (mesma regra do Risk Judge: maioria não-neutra).
 */
export function useSentiment() {
  const [markets, setMarkets] = useState<SentimentMarket[]>([]);

  useEffect(() => {
    let active = true;

    supabase
      .from("market_sentiment")
      .select(COLS)
      .order("volume", { ascending: false })
      .then(({ data }) => {
        if (active && data) setMarkets(data as SentimentMarket[]);
      });

    const channel = supabase
      .channel("sentiment-rt")
      .on("postgres_changes", { event: "*", schema: "public", table: "market_sentiment" }, (payload) => {
        setMarkets((prev) => {
          if (payload.eventType === "DELETE") {
            return prev.filter((m) => m.slug !== (payload.old as SentimentMarket).slug);
          }
          const row = payload.new as SentimentMarket;
          const i = prev.findIndex((m) => m.slug === row.slug);
          if (i === -1) return [...prev, row];
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

  const macroBias = useMemo<MacroBias>(() => {
    const bulls = markets.filter((m) => m.bias === "bullish").length;
    const bears = markets.filter((m) => m.bias === "bearish").length;
    if (bulls > bears) return "bullish";
    if (bears > bulls) return "bearish";
    return "neutral";
  }, [markets]);

  return { markets, macroBias };
}
