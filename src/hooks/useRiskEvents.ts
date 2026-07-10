import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabase";

export interface RiskEvent {
  id: string;
  created_at: string;
  decision: "approved" | "rejected";
  code: string; // OK | LOW_CONFIDENCE | NEUTRAL | ALLOC_EXCEEDED | MARGIN_LEVEL_LOW | CIRCUIT_BREAKER | DAILY_LOSS_CAP | MACRO_CONFLICT | OUTSIDE_SESSION | NEWS_BLACKOUT
  asset: string;
  direction: string;
  confidence: number | null;
  amount: number;
  balance: number | null;
  reason: string;
  details: Record<string, unknown> | null;
}

const COLS = "id,created_at,decision,code,asset,direction,confidence,amount,balance,reason,details";

/**
 * Veredito do Risk Judge (risk_events) em tempo real, filtrado por conta
 * (`source`, guardado dentro de `details` — ver connector/risk.py). Alimenta
 * o feed do AITerminal e o status "operando/inativo" da Visão Geral.
 */
export function useRiskEvents(source: string, limit = 30) {
  const [events, setEvents] = useState<RiskEvent[]>([]);

  useEffect(() => {
    let active = true;
    setEvents([]);

    supabase
      .from("risk_events")
      .select(COLS)
      .eq("details->>source", source)
      .order("created_at", { ascending: false })
      .limit(limit)
      .then(({ data }) => {
        if (active && data) setEvents(data as RiskEvent[]);
      });

    const channel = supabase
      .channel(`risk-events-rt-${source}`)
      .on("postgres_changes", { event: "INSERT", schema: "public", table: "risk_events" }, (payload) => {
        const row = payload.new as RiskEvent;
        if ((row.details as { source?: string } | null)?.source !== source) return;
        setEvents((prev) => [row, ...prev].slice(0, limit));
      })
      .subscribe();

    return () => {
      active = false;
      supabase.removeChannel(channel);
    };
  }, [source, limit]);

  return events;
}
